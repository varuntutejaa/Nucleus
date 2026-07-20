"""
Nucleus -- streaming AIOps alert correlation engine (FastAPI service).

Runs the correlation + root-cause engine (see app/streaming_engine.py --
originally prototyped separately, then rewritten here as pure functions) over
the full 132,927-alert real AIOps2020 dataset bundled at
app/data/aiops_full_alerts.csv, or over one of four fixed, graduated demo
slices for a faster/traceable demo.

Endpoints:
  GET  /api/aiops/summary            -> { raw_count, host_count, hosts }
  GET  /api/aiops/sample?size=100    -> { alerts: [...], count } (fixed demo slice, size in DEMO_SIZES)
  POST /api/aiops/run-sample?size=100-> { incidents: [...], metrics: {...} } (correlates that same slice)
  POST /api/aiops/run                -> { incidents: [...], metrics: {...} } (correlates the full 132,927 dataset)

Both run endpoints above also accept enable_ai_scoring (default false; see
app/streaming_engine.py ENABLE_AI_SCORING) to optionally blend AI-similarity
into correlation scoring -- off by default, byte-identical output to before
that feature existed. See docs/ARCHITECTURE.md "Future compatibility".

Pre-clustering preprocessing pipeline (embeddings + composite distance, no
clustering yet -- see app/preprocessing.py, app/embeddings.py, app/distance.py):
  POST /api/aiops/preprocess?size=100                    -> summary + preprocessing_id
  GET  /api/aiops/preprocess/{id}                        -> re-fetch that summary
  GET  /api/aiops/preprocess/{id}/matrices                -> full embeddings + distance matrices (n<=200 only)
  GET  /api/aiops/preprocess/{id}/similar/{alert_id}      -> top-k most similar alerts by composite distance
"""
import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.aiops_full_loader import DEMO_SIZES, load_demo_sample, load_full_dataset, sample_alerts
from app.distance import DEFAULT_ALPHA, DEFAULT_BETA, DEFAULT_GAMMA
from app.preprocessing import full_matrices, get_full_result, most_similar, run_preprocessing, summarize
from app.schemas import (
    AiopsSampleResponse, AiopsSummary, CopilotRequest, CopilotResponse, EngineRunResponse,
    PreprocessMatricesOut, PreprocessSummaryOut, SimilarAlertsResponse,
)
from app.streaming_engine import AI_SCORE_WEIGHT_AI, AI_SCORE_WEIGHT_EXISTING, run_engine

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


# Composite distance is O(n^2); only the two smallest demo slices are viable
# for /preprocess. 10,000/100,000 are refused outright (a 100,000x100,000
# matrix is 10 billion cells) -- see app/preprocessing.py MAX_ALERTS_FOR_PREPROCESS.
PREPROCESS_SIZES = [100, 1000]


def _validate_preprocess_size(size: int) -> int:
    if size not in PREPROCESS_SIZES:
        raise HTTPException(400, f"size must be one of {PREPROCESS_SIZES} for /preprocess, got {size}")
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
def run_aiops_sample_engine(
    size: int = Query(100), include_members: bool = Query(False),
    enable_ai_scoring: bool = Query(False, description="blend AI-similarity into correlation scoring (see docs/ARCHITECTURE.md); off leaves the engine byte-identical to before this existed"),
    ai_weight_existing: float = Query(AI_SCORE_WEIGHT_EXISTING, ge=0.0),
    ai_weight_ai: float = Query(AI_SCORE_WEIGHT_AI, ge=0.0),
):
    """Run the engine on one of the fixed demo slices (100/1,000/10,000/
    100,000 real contiguous alerts) instead of the full dataset. size=100
    is what the frontend's "Run Nucleus" button calls after the flood
    (<1s); the larger sizes power the "Compare scale" benchmark view and
    take proportionally longer -- ~46s measured locally for 100,000, since
    a contiguous slice is denser in time than the full spread-out dataset.
    include_members=true (used by the size=100 drill-down view) attaches
    each incident's raw member alerts; left off for the larger benchmark
    sizes to keep those responses small.

    enable_ai_scoring=true is refused above 10,000 alerts (see
    preprocessing.MAX_ALERTS_FOR_AI_SCORING) -- embedding is O(n), and at
    132,927 alerts that's minutes of work, not viable to trigger live."""
    _validate_size(size)
    df = load_demo_sample(size)
    try:
        return run_engine(
            df, include_members=include_members, enable_ai_scoring=enable_ai_scoring,
            ai_weight_existing=ai_weight_existing, ai_weight_ai=ai_weight_ai,
            ai_disk_cache_key=f"demo_{size}",
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.post("/api/aiops/run", response_model=EngineRunResponse)
def run_aiops_engine(
    include_members: bool = Query(False),
    enable_ai_scoring: bool = Query(False, description="blend AI-similarity into correlation scoring; always refused here -- see docstring"),
    ai_weight_existing: float = Query(AI_SCORE_WEIGHT_EXISTING, ge=0.0),
    ai_weight_ai: float = Query(AI_SCORE_WEIGHT_AI, ge=0.0),
):
    """Run the streaming correlation + root-cause engine over the full
    dataset on demand. Takes ~60-70s on the full 132,927 rows (measured
    locally; the root-cause scoring pass is the dominant cost, not the
    correlation pass itself) -- this is a synchronous `def` (not `async def`)
    so FastAPI runs it in a worker thread instead of blocking the event loop.

    enable_ai_scoring=true will always fail here with a clear 400: the full
    dataset is far above MAX_ALERTS_FOR_AI_SCORING (10,000) -- embedding all
    132,927 alerts is ~4-5 minutes of work on top of this endpoint's own
    ~60-70s, not something to let happen live. Use /run-sample with size up
    to 10,000 for AI-assisted scoring instead."""
    df = load_full_dataset()
    try:
        return run_engine(
            df, include_members=include_members, enable_ai_scoring=enable_ai_scoring,
            ai_weight_existing=ai_weight_existing, ai_weight_ai=ai_weight_ai,
            ai_disk_cache_key="full_dataset",
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.post("/api/aiops/preprocess", response_model=PreprocessSummaryOut)
def run_preprocess(
    size: int = Query(100),
    alpha: float = Query(DEFAULT_ALPHA, ge=0.0, description="semantic distance weight"),
    beta: float = Query(DEFAULT_BETA, ge=0.0, description="temporal distance weight"),
    gamma: float = Query(DEFAULT_GAMMA, ge=0.0, description="host distance weight"),
):
    """Run the pre-clustering pipeline (embeddings -> semantic/temporal/host
    distance -> composite distance) over one of the two smallest demo slices.
    Does NOT cluster anything -- stops at the composite distance matrix, held
    in-memory and returned only as a summary + id. Fetch the full matrices via
    GET .../matrices or a single alert's neighbors via GET .../similar/{id}."""
    _validate_preprocess_size(size)
    df = load_demo_sample(size)
    return run_preprocessing(df, alpha=alpha, beta=beta, gamma=gamma, disk_cache_key=f"demo_{size}")


@app.get("/api/aiops/preprocess/{preprocessing_id}", response_model=PreprocessSummaryOut)
def get_preprocess_summary(preprocessing_id: str):
    """Re-fetch a previous /preprocess run's summary by id. Results are
    in-memory only (no database) and evicted after the 10 most recent runs,
    same lifetime as the rest of this app's caches."""
    result = get_full_result(preprocessing_id)
    if result is None:
        raise HTTPException(404, f"no preprocessing result for id {preprocessing_id!r} (expired or never existed)")
    return summarize(result)


@app.get("/api/aiops/preprocess/{preprocessing_id}/matrices", response_model=PreprocessMatricesOut)
def get_preprocess_matrices(preprocessing_id: str):
    """Full embeddings + all four distance matrices for a previous
    /preprocess run. Refused above 200 alerts regardless of what size was
    allowed at preprocess time -- this is for inspection/debugging on small
    batches, not a bulk data-export endpoint."""
    result = get_full_result(preprocessing_id)
    if result is None:
        raise HTTPException(404, f"no preprocessing result for id {preprocessing_id!r} (expired or never existed)")
    n = result["composite_distance"].shape[0]
    if n > 200:
        raise HTTPException(400, f"alert_count {n} exceeds the 200-alert cap for full-matrix responses")
    return full_matrices(result)


@app.get("/api/aiops/preprocess/{preprocessing_id}/similar/{alert_id}", response_model=SimilarAlertsResponse)
def get_similar_alerts(preprocessing_id: str, alert_id: str, top_k: int = Query(5, ge=1, le=50)):
    """The top_k alerts closest to `alert_id` by composite distance, with
    each component (semantic/temporal/host) reframed as a 0-1 similarity
    score. This is exactly the signal a future HDBSCAN step would cluster
    on -- surfaced here so it's inspectable before any clustering exists."""
    result = get_full_result(preprocessing_id)
    if result is None:
        raise HTTPException(404, f"no preprocessing result for id {preprocessing_id!r} (expired or never existed)")
    preview = most_similar(result, alert_id, top_k=top_k)
    if preview is None:
        raise HTTPException(404, f"alert_id {alert_id!r} not found in preprocessing result {preprocessing_id!r}")
    return preview


@app.post("/api/aiops/copilot", response_model=CopilotResponse)
def ask_incident_copilot(request: CopilotRequest):
    """Generate a Groq explanation grounded in one correlated incident.
    GROQ_API_KEY is read server-side and is never exposed to the frontend."""
    from app.llm_copilot import generate_copilot_response
    try:
        return generate_copilot_response(request)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    except Exception:
        logging.exception("incident copilot request failed")
        raise HTTPException(502, "Incident Copilot could not reach the configured LLM")
