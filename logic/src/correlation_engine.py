"""
==========================================================
STREAMING ALERT CORRELATION ENGINE
==========================================================
"""

import os
import sys
from dataclasses import dataclass, field
from collections import defaultdict

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config import ALERT_DIR

# ==========================================================
# CONFIG
# ==========================================================

INPUT_FILE = ALERT_DIR / "alerts.csv"

CORRELATED_FILE = ALERT_DIR / "correlated_alerts.csv"

SUMMARY_FILE = ALERT_DIR / "incident_summary.csv"

STAT_FILE = ALERT_DIR / "incident_statistics.csv"

TIME_WINDOW = 300          # seconds

INCIDENT_TIMEOUT = 600     # seconds

CORRELATION_THRESHOLD = 0.60

# ==========================================================
# LOAD ALERTS
# ==========================================================

print("=" * 70)
print("Loading Alerts")
print("=" * 70)

df = pd.read_csv(INPUT_FILE)

print(f"Loaded {len(df):,} alerts")

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    unit="ms"
)

df = df.sort_values("timestamp").reset_index(drop=True)

print()
print("Hosts   :", df["host"].nunique())
print("Sources :", df["source"].nunique())
print("Metrics :", df["metric"].nunique())

# ==========================================================
# INCIDENT OBJECT
# ==========================================================

@dataclass
class Incident:

    incident_id: int

    host: str

    source: str

    start_time: pd.Timestamp

    end_time: pd.Timestamp

    alerts: list = field(default_factory=list)

    metrics: set = field(default_factory=set)

    severities: set = field(default_factory=set)

    values: list = field(default_factory=list)

    confidence: float = 0.0

    active: bool = True

    # -----------------------------------------

    def add_alert(self, row):

        self.alerts.append(row)

        self.metrics.add(row.metric)

        self.severities.add(row.severity)

        self.values.append(row.value)

        self.end_time = row.timestamp

    # -----------------------------------------

    @property
    def duration(self):

        return (
            self.end_time -
            self.start_time
        ).total_seconds()

    # -----------------------------------------

    @property
    def alert_count(self):

        return len(self.alerts)

    # -----------------------------------------

    @property
    def last_value(self):

        if self.values:
            return self.values[-1]

        return 0

# ==========================================================
# ENGINE
# ==========================================================

class CorrelationEngine:

    def __init__(self):

        self.next_incident = 0

        self.incidents = []

        self.active = defaultdict(list)

        self.correlated = []

        self.summary_df = None

        self.statistics_df = None

    # --------------------------------------------------

    def create_incident(self, row):

        incident = Incident(

            incident_id=self.next_incident,

            host=row.host,

            source=row.source,

            start_time=row.timestamp,

            end_time=row.timestamp

        )

        incident.add_alert(row)

        self.incidents.append(incident)

        self.active[(row.host, row.source)].append(incident)

        self.next_incident += 1

        return incident

    # --------------------------------------------------
    # Correlation Score
    # --------------------------------------------------

    def correlation_score(self, incident, row):

        score = 0.0

        # -------------------------------
        # Time Similarity
        # -------------------------------

        gap = (
            row.timestamp -
            incident.end_time
        ).total_seconds()

        if gap < 0:
            return 0

        if gap <= 60:
            score += 0.35
        elif gap <= 180:
            score += 0.25
        elif gap <= TIME_WINDOW:
            score += 0.15
        else:
            return 0

        # -------------------------------
        # Metric Similarity
        # -------------------------------

        if row.metric in incident.metrics:
            score += 0.30

        # -------------------------------
        # Severity Similarity
        # -------------------------------

        if row.severity in incident.severities:
            score += 0.20

        # -------------------------------
        # Value Similarity
        # -------------------------------

        if incident.values:

            diff = abs(
                row.value -
                incident.last_value
            )

            if diff <= 5:
                score += 0.15

            elif diff <= 10:
                score += 0.08

        return score

    # --------------------------------------------------
    # Remove Expired Incidents
    # --------------------------------------------------

    def expire_incidents(self, current_time):

        for key in list(self.active.keys()):

            active_list = []

            for incident in self.active[key]:

                idle = (
                    current_time -
                    incident.end_time
                ).total_seconds()

                if idle <= INCIDENT_TIMEOUT:

                    active_list.append(incident)

            self.active[key] = active_list

    # --------------------------------------------------
    # Find Best Matching Incident
    # --------------------------------------------------

    def find_best_incident(self, row):

        key = (row.host, row.source)

        if key not in self.active:

            return None

        best_incident = None

        best_score = 0.0

        for incident in self.active[key]:

            score = self.correlation_score(
                incident,
                row
            )

            if score > best_score:

                best_score = score

                best_incident = incident

        if best_score >= CORRELATION_THRESHOLD:

            return best_incident

        return None

    # --------------------------------------------------
    # Correlate Alerts
    # --------------------------------------------------

    def correlate(self, dataframe):

        print()
        print("=" * 70)
        print("Running Streaming Correlation")
        print("=" * 70)

        for row in dataframe.itertuples(index=False):

            # Remove inactive incidents
            self.expire_incidents(row.timestamp)

            incident = self.find_best_incident(row)

            # ------------------------------------

            if incident is None:

                incident = self.create_incident(row)

            else:

                incident.add_alert(row)

            self.correlated.append({

                "alert_id": row.alert_id,

                "incident_id": incident.incident_id,

                "timestamp": row.timestamp,

                "host": row.host,

                "metric": row.metric,

                "severity": row.severity,

                "value": row.value,

                "source": row.source

            })

        print()

        print("=" * 70)
        print("Correlation Complete")
        print("=" * 70)

        print()

        print("Incidents Created :", len(self.incidents))

        print("Alerts Correlated :", len(self.correlated))

    # --------------------------------------------------
    # Compute Incident Confidence
    # --------------------------------------------------

    def compute_confidence(self, incident):

        score = 0.0

        # More alerts = higher confidence
        score += min(
            incident.alert_count / 20,
            1.0
        ) * 0.30

        # More metric diversity
        score += min(
            len(incident.metrics) / 4,
            1.0
        ) * 0.20

        # Longer incident duration
        score += min(
            incident.duration / 300,
            1.0
        ) * 0.20

        # Severity contribution
        if "Critical" in incident.severities:
            score += 0.20
        elif "Warning" in incident.severities:
            score += 0.10

        # Multi-alert bonus
        if incident.alert_count >= 5:
            score += 0.10

        return round(min(score, 1.0), 3)

    # --------------------------------------------------
    # Build Incident Summary
    # --------------------------------------------------

    def build_summary(self):

        rows = []

        for incident in self.incidents:

            confidence = self.compute_confidence(
                incident
            )

            incident.confidence = confidence

            if "Critical" in incident.severities:
                severity = "Critical"

            elif "Warning" in incident.severities:
                severity = "Warning"

            else:
                severity = "Info"

            rows.append({

                "incident_id":
                    incident.incident_id,

                "host":
                    incident.host,

                "source":
                    incident.source,

                "start_time":
                    incident.start_time,

                "end_time":
                    incident.end_time,

                "duration_sec":
                    incident.duration,

                "alert_count":
                    incident.alert_count,

                "metric_count":
                    len(incident.metrics),

                "severity":
                    severity,

                "confidence":
                    confidence

            })

        self.summary_df = pd.DataFrame(rows)

    # --------------------------------------------------
    # Build Statistics
    # --------------------------------------------------

    def build_statistics(self):

        self.statistics_df = (

            self.summary_df

            .groupby("host")

            .agg(

                incidents=(
                    "incident_id",
                    "count"
                ),

                alerts=(
                    "alert_count",
                    "sum"
                ),

                avg_alerts=(
                    "alert_count",
                    "mean"
                ),

                avg_duration=(
                    "duration_sec",
                    "mean"
                ),

                avg_confidence=(
                    "confidence",
                    "mean"
                )

            )

            .reset_index()

        )

        print()

        print("=" * 70)

        print("Statistics")

        print("=" * 70)

        print()

        print(self.statistics_df.head())


# ==========================================================
# SAVE RESULTS
# ==========================================================

def save(engine):

    correlated_df = pd.DataFrame(
        engine.correlated
    )

    correlated_df.to_csv(
        CORRELATED_FILE,
        index=False
    )

    engine.summary_df.to_csv(
        SUMMARY_FILE,
        index=False
    )

    engine.statistics_df.to_csv(
        STAT_FILE,
        index=False
    )

    print()

    print("=" * 70)

    print("FILES SAVED")

    print("=" * 70)

    print()

    print(CORRELATED_FILE)

    print(SUMMARY_FILE)

    print(STAT_FILE)


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    engine = CorrelationEngine()

    engine.correlate(df)

    engine.build_summary()

    engine.build_statistics()

    save(engine)

    print()

    print("=" * 70)

    print("FINAL SUMMARY")

    print("=" * 70)

    print()

    print("Alerts :", len(engine.correlated))

    print("Incidents :", len(engine.incidents))

    print(
        "Average Alerts / Incident :",
        round(
            len(engine.correlated) /
            max(len(engine.incidents), 1),
            2
        )
    )

    print(
        "Average Confidence :",
        round(
            engine.summary_df[
                "confidence"
            ].mean(),
            3
        )
    )

    print()