# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 11:25:54 2026

@author: DELL
"""

from pathlib import Path
import pandas as pd

# =====================================================
# CHANGE THIS PATH
# =====================================================

DATASET_ROOT = Path(r"D:\AIOps挑战赛数据")

# =====================================================

OUTPUT_DIR = Path("D:\AIOps挑战赛数据\AlertCorrelationEngine\outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

metric_records = []

print("=" * 70)
print("Scanning metric files...")
print("=" * 70)

# Search every CSV in the dataset
for csv_file in DATASET_ROOT.rglob("*.csv"):

    # Ignore trace files
    if "trace" in csv_file.name.lower():
        continue

    try:

        df = pd.read_csv(csv_file, usecols=["name"])

        unique_metrics = sorted(df["name"].dropna().unique())

        for metric in unique_metrics:

            metric_records.append({

                "file": csv_file.name,
                "metric_name": metric,
                "path": str(csv_file)

            })

        print(f"✓ {csv_file.name:25} -> {len(unique_metrics)} metrics")

    except Exception:

        # Some files (like business metrics) don't have "name"
        continue

metrics_df = pd.DataFrame(metric_records)

metrics_df = metrics_df.drop_duplicates(
    subset=["file", "metric_name"]
)
print(f"Total Unique Metrics : {len(metrics_df)}")
metrics_df = metrics_df.sort_values(["file", "metric_name"])

output_file = OUTPUT_DIR / "all_metrics.csv"

metrics_df.to_csv(output_file, index=False)

print("\n")
print("=" * 70)
print("Finished")
print("=" * 70)

print(f"Total Unique Metrics : {len(metrics_df)}")

print(f"\nSaved to:\n{output_file.resolve()}")