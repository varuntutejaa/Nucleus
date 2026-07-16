# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 13:41:15 2026

@author: DELL
"""

"""
====================================================================
ROOT CAUSE ANALYSIS ENGINE
Part 1
====================================================================
"""

import os
import sys
from collections import Counter

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config import ALERT_DIR

# ==========================================================
# CONFIGURATION
# ==========================================================

INPUT_FILE = ALERT_DIR / "correlated_alerts.csv"

ROOT_CAUSE_FILE = ALERT_DIR / "root_cause.csv"

SUPPRESSED_FILE = ALERT_DIR / "suppressed_alerts.csv"

SUMMARY_FILE = ALERT_DIR / "incident_root_summary.csv"

# ==========================================================
# METRIC PRIORITY
# Higher value = more likely to be root cause
# ==========================================================

METRIC_PRIORITY = {

    "cpu_usage": 5,
    "memory_usage": 4,
    "disk_usage": 3,
    "disk_io": 3,
    "network": 2,
    "redis": 2,
    "oracle": 2

}

# ==========================================================
# SEVERITY SCORE
# ==========================================================

SEVERITY_SCORE = {

    "Critical": 5,

    "Warning": 3,

    "Info": 1

}

# ==========================================================
# LOAD ALERTS
# ==========================================================

print("=" * 70)
print("Loading Correlated Alerts")
print("=" * 70)

df = pd.read_csv(INPUT_FILE)

df["timestamp"] = pd.to_datetime(df["timestamp"])

print(f"Loaded {len(df):,} alerts")

print()

print("Incidents :", df["incident_id"].nunique())

print("Hosts     :", df["host"].nunique())

print()

# ==========================================================
# ROOT CAUSE ANALYZER
# ==========================================================

class RootCauseAnalyzer:

    def __init__(self, dataframe):

        self.df = dataframe

        self.root_causes = []

        self.suppressed = []

        self.summary = []

    # ------------------------------------------------------
    # Root Cause Score
    # ------------------------------------------------------

    def calculate_score(self, row, incident_df):

        score = 0.0

        # ---------------------------------------------
        # 1. Severity (35%)
        # ---------------------------------------------

        severity = SEVERITY_SCORE.get(
            row["severity"],
            1
        )

        score += (severity / 5.0) * 0.35

        # ---------------------------------------------
        # 2. Earliest Alert (25%)
        # ---------------------------------------------

        earliest = incident_df["timestamp"].min()

        latest = incident_df["timestamp"].max()

        total = (
            latest - earliest
        ).total_seconds()

        if total == 0:

            score += 0.25

        else:

            position = (
                row["timestamp"] -
                earliest
            ).total_seconds()

            score += (
                1 -
                position / total
            ) * 0.25

        # ---------------------------------------------
        # 3. Metric Frequency (20%)
        # ---------------------------------------------

        metric_count = (

            incident_df["metric"]

            == row["metric"]

        ).sum()

        score += (

            metric_count /

            len(incident_df)

        ) * 0.20

        # ---------------------------------------------
        # 4. Metric Priority (20%)
        # ---------------------------------------------

        priority = METRIC_PRIORITY.get(

            row["metric"],

            1

        )

        score += (

            priority / 5.0

        ) * 0.20

        return round(score, 4)

    # ------------------------------------------------------
    # Analyze All Incidents
    # ------------------------------------------------------

    def analyze(self):

        print()

        print("=" * 70)

        print("Running Root Cause Analysis")

        print("=" * 70)

        # ------------------------------------------

        for incident_id, incident_df in (

            self.df.groupby("incident_id")

        ):

            incident_df = (

                incident_df

                .sort_values("timestamp")

                .copy()

            )

            # ----------------------------------
            # Calculate Root Score
            # ----------------------------------

            scores = []

            for _, row in incident_df.iterrows():

                scores.append(

                    self.calculate_score(

                        row,

                        incident_df

                    )

                )

            incident_df["root_score"] = scores

            # ----------------------------------
            # Root Cause
            # ----------------------------------

            root = (

                incident_df

                .sort_values(

                    "root_score",

                    ascending=False

                )

                .iloc[0]

            )

            # ----------------------------------
            # Store Root Cause
            # ----------------------------------

            self.root_causes.append({

                "incident_id":

                    incident_id,

                "alert_id":

                    root["alert_id"],

                "timestamp":

                    root["timestamp"],

                "host":

                    root["host"],

                "metric":

                    root["metric"],

                "severity":

                    root["severity"],

                "value":

                    root["value"],

                "root_score":

                    root["root_score"]

            })

            # ----------------------------------
            # Suppressed Alerts
            # ----------------------------------

            suppressed = incident_df[

                incident_df["alert_id"]

                != root["alert_id"]

            ].copy()

            suppressed["root_alert"] = root["alert_id"]

            self.suppressed.extend(

                suppressed.to_dict(

                    "records"

                )

            )

            # ----------------------------------
            # Summary
            # ----------------------------------

            self.summary.append({

                "incident_id":

                    incident_id,

                "host":

                    root["host"],

                "root_metric":

                    root["metric"],

                "severity":

                    root["severity"],

                "alerts":

                    len(incident_df),

                "suppressed":

                    len(suppressed),

                "root_score":

                    root["root_score"]

            })

        print()

        print("Incidents Processed :", len(self.summary))

        print("Root Causes Found  :", len(self.root_causes))

        print("Suppressed Alerts  :", len(self.suppressed))

    # ------------------------------------------------------
    # Save Results
    # ------------------------------------------------------

    def save(self):

        root_df = pd.DataFrame(self.root_causes)

        suppressed_df = pd.DataFrame(self.suppressed)

        summary_df = pd.DataFrame(self.summary)

        root_df.to_csv(
            ROOT_CAUSE_FILE,
            index=False
        )

        suppressed_df.to_csv(
            SUPPRESSED_FILE,
            index=False
        )

        summary_df.to_csv(
            SUMMARY_FILE,
            index=False
        )

        print()

        print("=" * 70)
        print("FILES SAVED")
        print("=" * 70)

        print()

        print("Root Causes")
        print(ROOT_CAUSE_FILE)

        print()

        print("Suppressed Alerts")
        print(SUPPRESSED_FILE)

        print()

        print("Incident Summary")
        print(SUMMARY_FILE)


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    analyzer = RootCauseAnalyzer(df)

    analyzer.analyze()

    analyzer.save()

    print()

    print("=" * 70)
    print("ROOT CAUSE ANALYSIS COMPLETE")
    print("=" * 70)

    print()

    print("Incidents          :", len(analyzer.summary))

    print("Root Causes        :", len(analyzer.root_causes))

    print("Suppressed Alerts  :", len(analyzer.suppressed))

    reduction = 100 * (
        1 -
        len(analyzer.root_causes) /
        len(df)
    )

    print()

    print(
        "Alert Reduction    :",
        f"{reduction:.2f}%"
    )

    print()

    print("=" * 70)