"""
Streaming correlation + root-cause engine.

This is a straight port of logic/src/correlation_engine.py and
logic/src/root_cause.py -- the engine already validated against the full
132,927-row AIOps2020 alert dataset (99.24% reduction). Unlike the
HDBSCAN/embedding pipeline in pipeline/clustering.py (windowed, semantic
similarity, built for the small synthetic/sample batches), this engine
scales to the full real dataset because it's a single pass over
chronologically-sorted alerts with a per-(host, source) active-incident
window -- no O(n^2) distance matrix.

Ported as pure functions (input DataFrame -> output dict, no file I/O, no
module-level execution) so it's safe to call from a request handler instead
of running as a standalone script.
"""
from collections import defaultdict
from dataclasses import dataclass, field

import pandas as pd

TIME_WINDOW_SECONDS = 300
INCIDENT_TIMEOUT_SECONDS = 600
CORRELATION_THRESHOLD = 0.60

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

    def add_alert(self, row):
        self.metrics.add(row.metric)
        self.severities.add(row.severity)
        self.values.append(row.value)
        self.end_time = row.timestamp
        self.count += 1

    @property
    def last_value(self):
        return self.values[-1] if self.values else 0


class _CorrelationEngine:
    def __init__(self):
        self.next_incident = 0
        self.active = defaultdict(list)
        self.correlated = []

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


def _root_cause_score(row, incident_df: pd.DataFrame) -> float:
    score = (SEVERITY_SCORE.get(row["severity"], 1) / 5.0) * 0.35

    earliest, latest = incident_df["timestamp"].min(), incident_df["timestamp"].max()
    total = (latest - earliest).total_seconds()
    if total == 0:
        score += 0.25
    else:
        position = (row["timestamp"] - earliest).total_seconds()
        score += (1 - position / total) * 0.25

    metric_count = (incident_df["metric"] == row["metric"]).sum()
    score += (metric_count / len(incident_df)) * 0.20
    score += (METRIC_PRIORITY.get(row["metric"], 1) / 5.0) * 0.20
    return round(score, 4)


def run_engine(alerts_df: pd.DataFrame) -> dict:
    """Run the full streaming correlation + root-cause pipeline over
    `alerts_df` (columns: alert_id, timestamp[ms epoch], host, metric,
    value, severity, source). No file I/O -- returns incident summaries and
    reduction metrics directly."""
    df = alerts_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.sort_values("timestamp").reset_index(drop=True)

    correlated_df = _CorrelationEngine().correlate(df)

    incidents = []
    for incident_id, incident_df in correlated_df.groupby("incident_id"):
        incident_df = incident_df.sort_values("timestamp").copy()
        incident_df["root_score"] = [
            _root_cause_score(row, incident_df) for _, row in incident_df.iterrows()
        ]
        root = incident_df.sort_values("root_score", ascending=False).iloc[0]
        incidents.append({
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
        })

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
        },
    }
