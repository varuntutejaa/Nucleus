import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from pathlib import Path
import uuid

import pandas as pd

from config import DATASET_ROOT, ALERT_DIR
from rules import ALERT_RULES
from utils import evaluate


METRIC_FILES = {
    "os_linux.csv",
    "db_oracle_11g.csv",
    "mw_redis.csv",
    "dcos_docker.csv",
    "dcos_container.csv"
}


class AlertGenerator:

    def __init__(self):

        self.alerts = []

    # --------------------------------------------------

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

            except:

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

                    "source": csv_file.name

                })

    # --------------------------------------------------

    def run(self):

        for csv_file in DATASET_ROOT.rglob("*.csv"):

            if csv_file.name not in METRIC_FILES:
                continue

            self.process_file(csv_file)

    # --------------------------------------------------

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