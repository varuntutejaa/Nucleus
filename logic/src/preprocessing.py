# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 11:18:06 2026

@author: DELL
"""

from pathlib import Path
import pandas as pd

# ==========================================================
# CONFIGURATION
# ==========================================================

# CHANGE THIS PATH IF YOUR DATASET IS SOMEWHERE ELSE
DATASET_ROOT = Path(r"D:\AIOps挑战赛数据")

# ==========================================================
# Folder names in Chinese
# ==========================================================

FOLDER_MAP = {
    "平台指标": "Platform Metrics",
    "业务指标": "Business Metrics",
    "调用链指标": "Trace Data"
}

# ==========================================================
# Scan Dataset
# ==========================================================

def scan_dataset(root_path):
    """
    Automatically scans every day folder
    and collects information about every CSV.
    """

    csv_info = []

    for day_folder in sorted(root_path.glob("2020_*")):

        inner = day_folder / day_folder.name

        if not inner.exists():
            continue

        for chinese_folder, english_name in FOLDER_MAP.items():

            metric_folder = inner / chinese_folder

            if not metric_folder.exists():
                continue

            for csv_file in metric_folder.glob("*.csv"):

                try:

                    df = pd.read_csv(csv_file, nrows=5)

                    csv_info.append({

                        "Day": day_folder.name,
                        "Category": english_name,
                        "File": csv_file.name,
                        "Rows(sample)": len(df),
                        "Columns": ", ".join(df.columns),
                        "Path": str(csv_file)

                    })

                except Exception as e:

                    csv_info.append({

                        "Day": day_folder.name,
                        "Category": english_name,
                        "File": csv_file.name,
                        "Rows(sample)": "ERROR",
                        "Columns": str(e),
                        "Path": str(csv_file)

                    })

    return pd.DataFrame(csv_info)

# ==========================================================
# Main
# ==========================================================

if __name__ == "__main__":

    print("=" * 70)
    print("Scanning Dataset...")
    print("=" * 70)

    summary = scan_dataset(DATASET_ROOT)

    print(summary)

    output_dir = Path("D:\AIOps挑战赛数据\AlertCorrelationEngine\outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "dataset_summary.csv"

    summary.to_csv(output_file, index=False)

    print("\nDataset summary saved to:")
    print(output_file.resolve())