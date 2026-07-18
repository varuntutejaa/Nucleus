"""
Nucleus -- AIOps alert correlation engine (FastAPI service).

Endpoints (see API_CONTRACT.md for the full documented shape):
  GET /api/alerts/raw         -> { alerts: [...], count }
  GET /api/alerts/correlated  -> { clusters: [...], noise: [...], metrics: {...} }

Both endpoints accept `source` ("synthetic" | "dataset", default "synthetic")
and an optional `as_of` unix-timestamp cutoff used by the frontend's replay
mode to simulate alerts arriving live (poll with an advancing `as_of` instead
of opening a socket -- see project non-goals: no WebSockets).
"""
import logging
from contextlib import asynccontextmanager
from typing import List, Literal, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import DEFAULT_ALPHA, DEFAULT_BETA, DEFAULT_GAMMA
from app.data.aiops_full_loader import load_full_dataset, sample_alerts
from app.pipeline.clustering import correlate, public_alert
from app.pipeline.streaming_engine import run_engine
from app.schemas import AiopsSampleResponse, AiopsSummary, CorrelatedResponse, EngineRunResponse, RawAlertsResponse
from app.store import get_alert_batch

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_alert_batch("synthetic")  # warm the cache so the first demo request is instant
    yield


app = FastAPI(
    title="Nucleus",
    description=(
        "AIOps alert correlation engine: groups temporally and semantically "
        "related alerts, identifies the likely root cause per cluster, and "
        "suppresses derivative alerts from the primary view while keeping "
        "them inspectable."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

SourceParam = Literal["synthetic", "dataset"]


def _filter_as_of(alerts: List[dict], embeddings, as_of: Optional[float]):
    if as_of is None:
        return alerts, embeddings
    keep = [i for i, a in enumerate(alerts) if a["timestamp_unix"] <= as_of]
    return [alerts[i] for i in keep], embeddings[keep]


@app.get("/api/alerts/raw", response_model=RawAlertsResponse)
def get_raw_alerts(
    source: SourceParam = "synthetic",
    as_of: Optional[float] = Query(None, description="Unix timestamp cutoff for replay mode"),
):
    batch = get_alert_batch(source)
    alerts, _ = _filter_as_of(batch["alerts"], batch["embeddings"], as_of)
    public = [public_alert(a) for a in alerts]
    return {"alerts": public, "count": len(public)}


@app.get("/api/alerts/correlated", response_model=CorrelatedResponse)
def get_correlated_alerts(
    source: SourceParam = "synthetic",
    alpha: float = Query(DEFAULT_ALPHA, ge=0.0, le=1.0, description="Semantic distance weight"),
    beta: float = Query(DEFAULT_BETA, ge=0.0, le=1.0, description="Temporal distance weight"),
    gamma: float = Query(DEFAULT_GAMMA, ge=0.0, le=1.0, description="Service-topology penalty weight"),
    as_of: Optional[float] = Query(None, description="Unix timestamp cutoff for replay mode"),
):
    batch = get_alert_batch(source)
    alerts, embeddings = _filter_as_of(batch["alerts"], batch["embeddings"], as_of)
    clusters, noise, metrics = correlate(alerts, embeddings, alpha=alpha, beta=beta, gamma=gamma)
    return {"clusters": clusters, "noise": noise, "metrics": metrics}


@app.get("/api/aiops/summary", response_model=AiopsSummary)
def get_aiops_summary():
    """Cheap metadata about the full 132,927-row AIOps2020 dataset (row/host
    count) so the frontend can show "130k alerts loaded" without running the
    engine or shipping the whole dataset over the wire."""
    df = load_full_dataset()
    return {"raw_count": len(df), "host_count": int(df["host"].nunique())}


@app.get("/api/aiops/sample", response_model=AiopsSampleResponse)
def get_aiops_sample(limit: int = Query(250, ge=1, le=1000)):
    alerts = sample_alerts(limit)
    return {"alerts": alerts, "count": len(alerts)}


@app.post("/api/aiops/run", response_model=EngineRunResponse)
def run_aiops_engine():
    """Run the streaming correlation + root-cause engine (see
    pipeline/streaming_engine.py) over the full dataset on demand. Takes
    ~20s on the full 132,927 rows -- this is a synchronous `def` (not
    `async def`) so FastAPI runs it in a worker thread instead of blocking
    the event loop."""
    df = load_full_dataset()
    return run_engine(df)
