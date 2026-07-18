"""Loaders for the AIOps2020-derived alert data used by the streaming
engine and the demo UI.

- `aiops_full_alerts.csv` (132,927 rows) is the real dataset `POST
  /api/aiops/run` operates on by default. Bundled as a CSV since the raw
  AIOps2020 challenge data itself is multi-gigabyte and never shipped --
  this file is that raw data's already-materialized alert stream (see
  logic/src/alert_generator.py for how it was produced).
- `demo_sample_{100,1000,10000,100000}.csv` are a graduated series of
  fixed, reproducible *contiguous* slices of the same dataset -- used by
  the frontend's "Simulate incoming alerts" flood (always size=100, so
  it's small enough to watch alert-by-alert) and the "Compare scale"
  benchmark view (all four sizes, run independently). Contiguous rather
  than random on purpose: a random sample scattered across the dataset's
  ~50-day span has nothing temporally close enough to correlate (verified
  -- a random 1,000-alert draw only reduces ~3%, see
  `example_random_1000.csv`), while a contiguous slice is dense enough in
  time for the engine's correlation window to actually do something.
  Verified reduction at each scale (see DEMO_SIZES below):

      100     ->    20 incidents (80.00%),  ~0.1s to correlate
      1,000   ->    29 incidents (97.10%),  ~0.5s
      10,000  ->   118 incidents (98.82%),  ~4.5s
      100,000 ->   748 incidents (99.25%), ~46s (denser in time than the
                full dataset, so slower per-row despite being 75% of it)

Each cached in-process after first read, since none of these files change
at runtime.

`example_random_1000.csv` is a reference artifact from the exploration
that led to using contiguous (not random) slices above -- a random
1,000-row draw, included as the "doesn't work" counterexample. Not read
by any endpoint."""
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

CSV_PATH = Path(__file__).parent / "aiops_full_alerts.csv"
DEMO_SIZES = [100, 1000, 10000, 100000]
DEMO_PATHS = {n: Path(__file__).parent / f"demo_sample_{n}.csv" for n in DEMO_SIZES}

_cache: Optional[pd.DataFrame] = None
_demo_caches: Dict[int, pd.DataFrame] = {}


def load_full_dataset() -> pd.DataFrame:
    global _cache
    if _cache is None:
        _cache = pd.read_csv(CSV_PATH)
    return _cache


def load_demo_sample(size: int = 100) -> pd.DataFrame:
    """One of the fixed demo slices (100/1,000/10,000/100,000 rows) as a
    raw DataFrame (ms-epoch timestamp column intact) -- feed this straight
    into streaming_engine.run_engine(). Raises KeyError for any other
    size; callers (main.py) validate against DEMO_SIZES first."""
    if size not in _demo_caches:
        _demo_caches[size] = pd.read_csv(DEMO_PATHS[size]).sort_values("timestamp").reset_index(drop=True)
    return _demo_caches[size]


def sample_alerts(limit: int, size: int = 100) -> list:
    """The size=100 demo slice, JSON-ready, capped at `limit`. Powers the
    frontend's "simulate incoming alerts" flood animation -- the same 100
    alerts every time, not a fresh draw."""
    sample = load_demo_sample(size).head(limit)
    return [
        {
            "alert_id": row.alert_id,
            "timestamp": pd.to_datetime(row.timestamp, unit="ms").isoformat(),
            "host": row.host,
            "metric": row.metric,
            "value": float(row.value),
            "severity": row.severity,
            "message": row.message,
        }
        for row in sample.itertuples(index=False)
    ]
