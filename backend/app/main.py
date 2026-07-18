"""
Nucleus -- streaming AIOps alert correlation engine (FastAPI service).

Runs the correlation + root-cause engine (see app/pipeline/streaming_engine.py,
ported from logic/src/correlation_engine.py + root_cause.py) over the full
132,927-alert real AIOps2020 dataset bundled at app/data/aiops_full_alerts.csv,
or over one of four fixed, graduated demo slices for a faster/traceable demo.

Endpoints:
  GET  /api/aiops/summary            -> { raw_count, host_count, hosts }
  GET  /api/aiops/sample?size=100    -> { alerts: [...], count } (fixed demo slice, size in DEMO_SIZES)
  POST /api/aiops/run-sample?size=100-> { incidents: [...], metrics: {...} } (correlates that same slice)
  POST /api/aiops/run                -> { incidents: [...], metrics: {...} } (correlates the full 132,927 dataset)
"""
import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.data.aiops_full_loader import DEMO_SIZES, load_demo_sample, load_full_dataset, sample_alerts
from app.pipeline.streaming_engine import run_engine
from app.schemas import AiopsSampleResponse, AiopsSummary, EngineRunResponse

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Nucleus",
    description=(
        "Streaming AIOps alert correlation engine: groups a real 132,927-alert "
        "dataset into incidents by host/metric/time proximity and identifies "
        "the likely root-cause alert per incident."
    ),
    version="0.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _validate_size(size: int) -> int:
    if size not in DEMO_SIZES:
        raise HTTPException(400, f"size must be one of {DEMO_SIZES}, got {size}")
    return size


@app.get("/api/aiops/summary", response_model=AiopsSummary)
def get_aiops_summary():
    """Cheap metadata about the full dataset (row/host count + the real
    host IDs) so the frontend can render a live host-status grid without
    running the engine or shipping the whole dataset over the wire."""
    df = load_full_dataset()
    return {
        "raw_count": len(df),
        "host_count": int(df["host"].nunique()),
        "hosts": sorted(df["host"].unique().tolist()),
    }


@app.get("/api/aiops/sample", response_model=AiopsSampleResponse)
def get_aiops_sample(limit: int = Query(100, ge=1, le=100), size: int = Query(100)):
    """Serves from a fixed demo slice (see aiops_full_loader.sample_alerts)
    -- the same alerts every call, not a fresh random draw, and the same
    alerts that /run-sample below correlates for that size. Only size=100
    is used by the frontend's "Simulate" flood; the larger sizes are for
    the scale-comparison view, which calls /run-sample directly without
    needing the raw alert list."""
    _validate_size(size)
    alerts = sample_alerts(limit, size)
    return {"alerts": alerts, "count": len(alerts)}


@app.post("/api/aiops/run-sample", response_model=EngineRunResponse)
def run_aiops_sample_engine(size: int = Query(100), include_members: bool = Query(False)):
    """Run the engine on one of the fixed demo slices (100/1,000/10,000/
    100,000 real contiguous alerts) instead of the full dataset. size=100
    is what the frontend's "Run Nucleus" button calls after the flood
    (<1s); the larger sizes power the "Compare scale" benchmark view and
    take proportionally longer -- ~46s measured locally for 100,000, since
    a contiguous slice is denser in time than the full spread-out dataset.
    include_members=true (used by the size=100 drill-down view) attaches
    each incident's raw member alerts; left off for the larger benchmark
    sizes to keep those responses small."""
    _validate_size(size)
    df = load_demo_sample(size)
    return run_engine(df, include_members=include_members)


@app.post("/api/aiops/run", response_model=EngineRunResponse)
def run_aiops_engine(include_members: bool = Query(False)):
    """Run the streaming correlation + root-cause engine over the full
    dataset on demand. Takes ~60-70s on the full 132,927 rows (measured
    locally; the root-cause scoring pass is the dominant cost, not the
    correlation pass itself) -- this is a synchronous `def` (not `async def`)
    so FastAPI runs it in a worker thread instead of blocking the event loop."""
    df = load_full_dataset()
    return run_engine(df, include_members=include_members)
