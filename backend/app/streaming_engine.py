"""
Streaming correlation + root-cause engine.

This is a rewrite of an original prototype (correlation engine + root-cause
scoring, developed and validated separately before being consolidated here
as pure functions) -- validated against the full 132,927-row AIOps2020 alert
dataset (99.24% reduction). An earlier iteration of this project also had a
second correlation approach (HDBSCAN + semantic embeddings, windowed,
built for small synthetic/sample batches); it was cut entirely since it
never ran against the real dataset and wasn't reachable from the UI. This
engine scales to the full real dataset because it's a single pass over
chronologically-sorted alerts with a per-(host, source) active-incident
window -- no O(n^2) distance matrix.

Written as pure functions (input DataFrame -> output dict, no file I/O, no
module-level execution) so it's safe to call from a request handler instead
of running as a standalone script.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Optional

import pandas as pd

TIME_WINDOW_SECONDS = 600  # was 300 (5 min); widened after an empirical sweep
# against the full 132,927-alert dataset showed 10 min cuts incident count from
# 1,012 to 820 (~19%, zero extra cost) with no loss of coherence -- every
# incident, at both settings, stayed single-metric/single-severity/single-host
# (0% mixed in either case). INCIDENT_TIMEOUT_SECONDS and CORRELATION_THRESHOLD
# were tested too; timeout had zero effect on this dataset (alert gaps don't
# land in the 10-30 min range it would affect), and lowering the threshold
# was riskier for a similar-sized win, so left alone.
INCIDENT_TIMEOUT_SECONDS = 600
CORRELATION_THRESHOLD = 0.60

# Optional AI-scoring blend (see docs/ARCHITECTURE.md "Future compatibility").
# Off by default: when disabled, _score() never touches these, never calls
# into preprocessing.py, and returns exactly what it always has -- this is
# not just numerically equivalent, it's the same code path unchanged.
ENABLE_AI_SCORING = False
AI_SCORE_WEIGHT_EXISTING = 0.75
AI_SCORE_WEIGHT_AI = 0.25

METRIC_PRIORITY = {
    "cpu_usage": 5, "memory_usage": 4, "disk_usage": 3, "disk_io": 3,
    "network": 2, "redis": 2, "oracle": 2,
}
SEVERITY_SCORE = {"Critical": 5, "Warning": 3, "Info": 1}


@dataclass
class _Incident:
    incident_id: int
    host: str
    source: str
    start_time: pd.Timestamp
    end_time: pd.Timestamp
    metrics: set = field(default_factory=set)
    severities: set = field(default_factory=set)
    values: list = field(default_factory=list)
    count: int = 0
    last_alert_id: Optional[str] = None  # only read when AI scoring is enabled

    def add_alert(self, row):
        self.metrics.add(row.metric)
        self.severities.add(row.severity)
        self.values.append(row.value)
        self.end_time = row.timestamp
        self.last_alert_id = row.alert_id
        self.count += 1

    @property
    def last_value(self):
        return self.values[-1] if self.values else 0


class _CorrelationEngine:
    def __init__(self, ai_similarity: Optional[Callable[[str, str], float]] = None,
                 ai_weight_existing: float = AI_SCORE_WEIGHT_EXISTING, ai_weight_ai: float = AI_SCORE_WEIGHT_AI):
        self.next_incident = 0
        self.active = defaultdict(list)
        self.correlated = []
        self.ai_similarity = ai_similarity
        self.ai_weight_existing = ai_weight_existing
        self.ai_weight_ai = ai_weight_ai

    def _create_incident(self, row):
        incident = _Incident(self.next_incident, row.host, row.source, row.timestamp, row.timestamp)
        incident.add_alert(row)
        self.active[(row.host, row.source)].append(incident)
        self.next_incident += 1
        return incident

    def _score(self, incident, row):
        gap = (row.timestamp - incident.end_time).total_seconds()
        if gap < 0:
            return 0.0
        if gap <= 60:
            score = 0.35
        elif gap <= 180:
            score = 0.25
        elif gap <= TIME_WINDOW_SECONDS:
            score = 0.15
        else:
            return 0.0
        if row.metric in incident.metrics:
            score += 0.30
        if row.severity in incident.severities:
            score += 0.20
        if incident.values:
            diff = abs(row.value - incident.last_value)
            if diff <= 5:
                score += 0.15
            elif diff <= 10:
                score += 0.08

        # Optional AI-scoring blend -- only reached once the alert has already
        # passed the hard time-window gate above (gap < 0 or gap > TIME_WINDOW_SECONDS
        # both return 0.0 before this point, and the AI similarity below has no
        # ability to reverse that). self.ai_similarity is None unless the caller
        # explicitly opted in, so this is a no-op on the default path.
        if self.ai_similarity is not None and incident.last_alert_id is not None:
            ai_score = self.ai_similarity(row.alert_id, incident.last_alert_id)
            score = self.ai_weight_existing * score + self.ai_weight_ai * ai_score

        return score

    def _expire(self, current_time):
        for key in list(self.active.keys()):
            self.active[key] = [
                inc for inc in self.active[key]
                if (current_time - inc.end_time).total_seconds() <= INCIDENT_TIMEOUT_SECONDS
            ]

    def _find_best(self, row):
        key = (row.host, row.source)
        if key not in self.active:
            return None
        best_incident, best_score = None, 0.0
        for incident in self.active[key]:
            score = self._score(incident, row)
            if score > best_score:
                best_score, best_incident = score, incident
        return best_incident if best_score >= CORRELATION_THRESHOLD else None

    def correlate(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        for row in dataframe.itertuples(index=False):
            self._expire(row.timestamp)
            incident = self._find_best(row)
            if incident is None:
                incident = self._create_incident(row)
            else:
                incident.add_alert(row)
            self.correlated.append({
                "alert_id": row.alert_id, "incident_id": incident.incident_id, "timestamp": row.timestamp,
                "host": row.host, "metric": row.metric, "severity": row.severity, "value": row.value,
                "source": row.source,
            })
        return pd.DataFrame(self.correlated)


def _root_cause_scores(incident_df: pd.DataFrame) -> pd.Series:
    """Score all incident members together, avoiding a full scan per alert."""
    severity = (
        incident_df["severity"].map(SEVERITY_SCORE).fillna(1).astype(float) / 5.0 * 0.35
    )

    timestamps = incident_df["timestamp"]
    earliest, latest = timestamps.min(), timestamps.max()
    total = (latest - earliest).total_seconds()
    if total == 0:
        temporal = pd.Series(0.25, index=incident_df.index)
    else:
        positions = (timestamps - earliest).dt.total_seconds()
        temporal = (1 - positions / total) * 0.25

    metric_counts = incident_df["metric"].value_counts()
    frequency = incident_df["metric"].map(metric_counts) / len(incident_df) * 0.20
    priority = (
        incident_df["metric"].map(METRIC_PRIORITY).fillna(1).astype(float) / 5.0 * 0.20
    )
    return (severity + temporal + frequency + priority).round(4)


def run_engine(alerts_df: pd.DataFrame, include_members: bool = False,
                enable_ai_scoring: Optional[bool] = None,
                ai_weight_existing: Optional[float] = None,
                ai_weight_ai: Optional[float] = None,
                ai_disk_cache_key: Optional[str] = None) -> dict:
    """Run the full streaming correlation + root-cause pipeline over
    `alerts_df` (columns: alert_id, timestamp[ms epoch], host, metric,
    value, severity, source). No file I/O -- returns incident summaries and
    reduction metrics directly.

    include_members=True attaches every raw alert folded into each incident
    (not just the aggregate counts) so a UI can show "what's in this
    cluster" on click -- opt-in since it multiplies response size by
    roughly raw_count for large runs (the 100k-alert benchmark doesn't need it).

    enable_ai_scoring=True blends an AI-similarity score (sentence-transformer
    embeddings + semantic/temporal/host distance, via app.preprocessing) into
    the correlation score -- see docs/ARCHITECTURE.md "Future compatibility".
    None (default) falls back to the module-level ENABLE_AI_SCORING constant
    (False). When it resolves False, app.preprocessing is never imported and
    _score()'s behavior is unchanged -- not just numerically equivalent, the
    same code path. ai_weight_existing/ai_weight_ai similarly fall back to
    AI_SCORE_WEIGHT_EXISTING/AI_SCORE_WEIGHT_AI when omitted.

    ai_disk_cache_key (e.g. "demo_10000"), when given, persists the embedding
    step to disk so it's paid once ever for that dataset, not once per process
    -- see app.embeddings.load_cached_embeddings."""
    use_ai = ENABLE_AI_SCORING if enable_ai_scoring is None else enable_ai_scoring
    w_existing = AI_SCORE_WEIGHT_EXISTING if ai_weight_existing is None else ai_weight_existing
    w_ai = AI_SCORE_WEIGHT_AI if ai_weight_ai is None else ai_weight_ai

    ai_similarity = None
    if use_ai:
        # Deferred import: sentence-transformers/torch only get pulled in on
        # this path, never when AI scoring is off (the default).
        from app.preprocessing import build_ai_similarity_lookup
        ai_similarity = build_ai_similarity_lookup(alerts_df, disk_cache_key=ai_disk_cache_key)

    df = alerts_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.sort_values("timestamp").reset_index(drop=True)

    engine = _CorrelationEngine(ai_similarity=ai_similarity, ai_weight_existing=w_existing, ai_weight_ai=w_ai)
    correlated_df = engine.correlate(df)

    incidents = []
    for incident_id, incident_df in correlated_df.groupby("incident_id"):
        incident_df = incident_df.sort_values("timestamp").copy()
        incident_df["root_score"] = _root_cause_scores(incident_df)
        root = incident_df.sort_values("root_score", ascending=False).iloc[0]
        incident = {
            "incident_id": int(incident_id),
            "host": str(root["host"]),
            "root_metric": str(root["metric"]),
            "severity": str(root["severity"]),
            "root_alert_id": str(root["alert_id"]),
            "root_timestamp": root["timestamp"].isoformat(),
            "root_value": float(root["value"]),
            "root_score": float(root["root_score"]),
            "alert_count": int(len(incident_df)),
            "suppressed_count": int(len(incident_df) - 1),
            "members": [],
        }
        if include_members:
            # incident_df is already timestamp-sorted above; itertuples() instead
            # of iterrows() avoids a per-row Series allocation, which matters a
            # lot once this runs over the full 132,927-row dataset.
            incident["members"] = [
                {
                    "alert_id": str(member.alert_id),
                    "timestamp": member.timestamp.isoformat(),
                    "host": str(member.host),
                    "metric": str(member.metric),
                    "severity": str(member.severity),
                    "value": float(member.value),
                    "root_score": float(member.root_score),
                    "is_root": str(member.alert_id) == str(root["alert_id"]),
                }
                for member in incident_df.itertuples(index=False)
            ]
        incidents.append(incident)

    incidents.sort(key=lambda i: i["root_timestamp"])

    raw_count = len(df)
    incident_count = len(incidents)
    suppressed_count = raw_count - incident_count
    reduction_pct = round(100 * (1 - incident_count / raw_count), 2) if raw_count else 0.0

    return {
        "incidents": incidents,
        "metrics": {
            "raw_count": raw_count,
            "incident_count": incident_count,
            "suppressed_count": suppressed_count,
            "reduction_pct": reduction_pct,
            "host_count": int(df["host"].nunique()),
            "ai_scoring_enabled": use_ai,
        },
    }
