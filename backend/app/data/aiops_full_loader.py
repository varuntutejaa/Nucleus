"""Loader for the full AIOps2020-derived alert dataset (132,927 rows) used
by the streaming engine. Bundled as a CSV since the raw AIOps2020 challenge
data itself is multi-gigabyte and never shipped -- this file is that raw
data's already-materialized alert stream (see logic/src/alert_generator.py
for how it was produced). Cached in-process after first read, same pattern
as app/store.py, since the file never changes at runtime."""
from pathlib import Path
from typing import Optional

import pandas as pd

CSV_PATH = Path(__file__).parent / "aiops_full_alerts.csv"

_cache: Optional[pd.DataFrame] = None


def load_full_dataset() -> pd.DataFrame:
    global _cache
    if _cache is None:
        _cache = pd.read_csv(CSV_PATH)
    return _cache


def sample_alerts(limit: int) -> list:
    """A random sample of individual raw alerts, chronologically ordered --
    for the frontend's "simulate incoming alerts" demo animation, which only
    needs to look like a live flood, not be exhaustive."""
    df = load_full_dataset()
    sample = df.sample(n=min(limit, len(df))).sort_values("timestamp")
    return [
        {
            "alert_id": row.alert_id,
            "timestamp": pd.to_datetime(row.timestamp, unit="ms").isoformat(),
            "host": row.host,
            "metric": row.metric,
            "severity": row.severity,
            "message": row.message,
        }
        for row in sample.itertuples(index=False)
    ]
