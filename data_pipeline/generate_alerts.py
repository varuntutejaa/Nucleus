"""
Generates the real alert dataset (app/data/aiops_full_alerts.csv, bundled
with the backend) by applying threshold rules to the raw AIOps2020
Challenge platform-metric CSVs (os_linux.csv, db_oracle_11g.csv,
mw_redis.csv, dcos_docker.csv, dcos_container.csv).

This is the offline data pipeline (see docs/ARCHITECTURE.md) -- a one-time,
run-by-hand script, not something the running app calls. See
backend/app/aiops_full_loader.py for how the already-generated output is
consumed at runtime. Set DATASET_ROOT below to wherever you've extracted the
raw AIOps2020 challenge dataset before running.

(This used to live at logic/, alongside the original correlation-engine and
root-cause prototypes; both were fully ported into
backend/app/streaming_engine.py and removed once superseded. Moved to
data_pipeline/ to make the offline/runtime split explicit at the folder
level -- see docs/ARCHITECTURE.md.)
"""
import operator
import uuid
from pathlib import Path

import pandas as pd

DATASET_ROOT = Path("./aiops2020_dataset")  # point this at the extracted raw dataset
ALERT_DIR = Path(__file__).parent / "data" / "alerts"
ALERT_DIR.mkdir(parents=True, exist_ok=True)

METRIC_FILES = {
    "os_linux.csv",
    "db_oracle_11g.csv",
    "mw_redis.csv",
    "dcos_docker.csv",
    "dcos_container.csv",
}

ALERT_RULES = {
    # ================= OS ==================
    "CPU_util_pct": {
        "operator": ">",
        "threshold": 0.90,
        "severity": "Critical",
        "message": "High CPU Utilization",
    },
    "Processor_load_5_min": {
        "operator": ">",
        "threshold": 0.80,
        "severity": "Warning",
        "message": "High Processor Load",
    },
    "MEM_real_util": {
        "operator": ">",
        "threshold": 0.90,
        "severity": "Critical",
        "message": "High Memory Utilization",
    },
    "Sent_errors_packets": {
        "operator": ">",
        "threshold": 0,
        "severity": "Critical",
        "message": "Network Packet Errors",
    },
    "Receive_errors_packets": {
        "operator": ">",
        "threshold": 0,
        "severity": "Critical",
        "message": "Incoming Packet Errors",
    },
    # ================= Oracle ==================
    "Sess_Connect": {
        "operator": ">",
        "threshold": 500,
        "severity": "Warning",
        "message": "Too Many Database Sessions",
    },
    "DbTime": {
        "operator": ">",
        "threshold": 1000,
        "severity": "Critical",
        "message": "Database Response Time High",
    },
}

_OPS = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
}


def evaluate(value, rule):
    return _OPS[rule["operator"]](float(value), rule["threshold"])


class AlertGenerator:
    def __init__(self):
        self.alerts = []

    def process_file(self, csv_file):
        print(f"Processing {csv_file.name}")
        df = pd.read_csv(csv_file)
        for _, row in df.iterrows():
            metric = row["name"]
            if metric not in ALERT_RULES:
                continue
            rule = ALERT_RULES[metric]
            try:
                value = float(row["value"])
            except ValueError:
                continue
            if evaluate(value, rule):
                self.alerts.append({
                    "alert_id": str(uuid.uuid4()),
                    "timestamp": row["timestamp"],
                    "host": row["cmdb_id"],
                    "metric": metric,
                    "value": value,
                    "severity": rule["severity"],
                    "message": rule["message"],
                    "source": csv_file.name,
                })

    def run(self):
        for csv_file in DATASET_ROOT.rglob("*.csv"):
            if csv_file.name not in METRIC_FILES:
                continue
            self.process_file(csv_file)

    def save(self):
        df = pd.DataFrame(self.alerts)
        output = ALERT_DIR / "alerts.csv"
        df.to_csv(output, index=False)
        print()
        print("=" * 70)
        print("Finished")
        print("=" * 70)
        print()
        print("Total Alerts :", len(df))
        print("Saved to")
        print(output)


if __name__ == "__main__":
    generator = AlertGenerator()
    generator.run()
    generator.save()
