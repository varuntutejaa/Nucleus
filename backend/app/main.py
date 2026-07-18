"""
Nucleus -- streaming AIOps alert correlation engine (FastAPI service).

Runs the correlation + root-cause engine (see app/pipeline/streaming_engine.py,
ported from logic/src/correlation_engine.py + root_cause.py) over the full
132,927-alert real AIOps2020 dataset bundled at app/data/aiops_full_alerts.csv.

Endpoints:
  GET  /api/aiops/summary        -> { raw_count, host_count }
  GET  /api/aiops/sample         -> { alerts: [...], count } (demo stream sample)
  POST /api/aiops/run            -> { incidents: [...], metrics: {...} }
"""
import logging

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app.data.aiops_full_loader import load_full_dataset, sample_alerts
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
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/aiops/summary", response_model=AiopsSummary)
def get_aiops_summary():
    """Cheap metadata about the full dataset (row/host count) so the
    frontend can show "130k alerts loaded" without running the engine or
    shipping the whole dataset over the wire."""
    df = load_full_dataset()
    return {"raw_count": len(df), "host_count": int(df["host"].nunique())}


@app.get("/api/aiops/sample", response_model=AiopsSampleResponse)
def get_aiops_sample(limit: int = Query(250, ge=1, le=1000)):
    alerts = sample_alerts(limit)
    return {"alerts": alerts, "count": len(alerts)}


@app.post("/api/aiops/run", response_model=EngineRunResponse)
def run_aiops_engine():
    """Run the streaming correlation + root-cause engine over the full
    dataset on demand. Takes ~20s on the full 132,927 rows -- this is a
    synchronous `def` (not `async def`) so FastAPI runs it in a worker
    thread instead of blocking the event loop."""
    df = load_full_dataset()
    return run_engine(df)
