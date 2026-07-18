"""
Preprocessing pipeline orchestration: alert batch -> embeddings -> composite
distance matrix, stored in-process and exposed through small summary/preview
responses instead of raw n x n matrices.

This is new code (not recovered) -- the pre-deletion implementation went
straight from distance matrix into sliding-window HDBSCAN + union-find
(pipeline/clustering.py), which this project explicitly isn't doing yet.
This module stops right after the composite distance matrix, on purpose.

No database, same as the rest of this app: results are held in a bounded
in-memory dict keyed by a generated preprocessing_id, evicted oldest-first
once MAX_STORED_RESULTS is exceeded, and lost on process restart -- same
lifetime as aiops_full_loader.py's demo-slice cache.
"""
import time
import uuid
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from app.distance import DEFAULT_ALPHA, DEFAULT_BETA, DEFAULT_GAMMA, composite_distance_matrix, composite_distance_pair
from app.embeddings import alert_to_text, embed_messages, get_backend_name, load_cached_embeddings, save_cached_embeddings

MAX_STORED_RESULTS = 10
MAX_ALERTS_FOR_PREPROCESS = 1000  # composite distance is O(n^2); see distance.py

# AI-scoring (streaming_engine.py's optional path) only ever needs O(n)
# embeddings, not the O(n^2) matrix above -- but O(n) is still real work:
# embedding throughput measured at ~500 alerts/sec once the model is warm, so
# the full 132,927-alert dataset would cost ~4-5 minutes on top of the
# correlation engine's own ~60-90s. That's not viable for a live demo, so
# this is capped well below the full dataset -- enabling AI scoring on the
# full run is refused outright (see build_ai_similarity_lookup) rather than
# left as a slow trap someone could hit live.
MAX_ALERTS_FOR_AI_SCORING = 10000
MAX_AI_SIMILARITY_CACHE_ENTRIES = 5

_store: "Dict[str, dict]" = {}
_insertion_order: "List[str]" = []

_ai_similarity_cache: "Dict[tuple, Callable[[str, str], float]]" = {}
_ai_similarity_cache_order: "List[tuple]" = []


def _evict_if_needed():
    while len(_insertion_order) > MAX_STORED_RESULTS:
        oldest = _insertion_order.pop(0)
        _store.pop(oldest, None)


def _get_or_compute_embeddings(df: pd.DataFrame, alerts: list, disk_cache_key: Optional[str]) -> np.ndarray:
    """Disk-cache-aware embedding step, shared by build_ai_similarity_lookup
    and run_preprocessing. If disk_cache_key is given (e.g. "demo_100000")
    and a cached array exists with the right row count, load it (a few
    hundred ms) instead of re-embedding (measured ~290s for 100,000 alerts).
    Newly-computed embeddings are saved back under that key for next time --
    this survives process restarts, unlike the in-memory caches below."""
    if disk_cache_key:
        cached = load_cached_embeddings(disk_cache_key)
        if cached is not None and len(cached) == len(df):
            return cached

    texts = [alert_to_text(a["host"], a["metric"], a["severity"], a["value"], a["message"]) for a in alerts]
    embeddings = embed_messages(texts)

    if disk_cache_key:
        save_cached_embeddings(disk_cache_key, embeddings)

    return embeddings


def build_ai_similarity_lookup(df: pd.DataFrame, alpha: float = DEFAULT_ALPHA,
                                beta: float = DEFAULT_BETA, gamma: float = DEFAULT_GAMMA,
                                disk_cache_key: Optional[str] = None
                                ) -> "Callable[[str, str], float]":
    """Embed every alert in `df` once (O(n) -- not the O(n^2) distance matrix
    run_preprocessing() builds) and return a similarity(alert_id_a, alert_id_b)
    closure. This is the only thing streaming_engine.py's optional AI-scoring
    path ever calls; it has no knowledge of embeddings, models, or distance
    formulas -- those all stay in this module and distance.py/embeddings.py.

    Raises ValueError above MAX_ALERTS_FOR_AI_SCORING -- embedding is O(n),
    but n=132,927 is still ~4-5 minutes of real work, not viable to trigger
    live during a demo. Results are cached per exact alert-id set (bounded,
    LRU-evicted, in-memory only) so repeat calls in the same process are
    instant; pass disk_cache_key (e.g. "demo_10000") to also persist the
    embeddings themselves to disk, surviving process restarts."""
    n = len(df)
    if n > MAX_ALERTS_FOR_AI_SCORING:
        raise ValueError(
            f"alert_count {n} exceeds MAX_ALERTS_FOR_AI_SCORING={MAX_ALERTS_FOR_AI_SCORING} -- "
            "AI scoring isn't available for batches this large (see preprocessing.py docstring)."
        )

    cache_key = (frozenset(df["alert_id"]), round(alpha, 6), round(beta, 6), round(gamma, 6))
    if cache_key in _ai_similarity_cache:
        return _ai_similarity_cache[cache_key]

    alerts = df.to_dict(orient="records")
    embeddings = _get_or_compute_embeddings(df, alerts, disk_cache_key)
    timestamps = (df["timestamp"].to_numpy(dtype=np.float64)) / 1000.0  # ms -> seconds
    hosts = df["host"].tolist()
    index_by_alert_id = {a["alert_id"]: i for i, a in enumerate(alerts)}

    def similarity(alert_id_a: str, alert_id_b: str) -> float:
        i, j = index_by_alert_id[alert_id_a], index_by_alert_id[alert_id_b]
        distance = composite_distance_pair(
            embeddings[i], embeddings[j], timestamps[i], timestamps[j], hosts[i], hosts[j],
            alpha, beta, gamma,
        )
        return 1.0 - distance

    _ai_similarity_cache[cache_key] = similarity
    _ai_similarity_cache_order.append(cache_key)
    while len(_ai_similarity_cache_order) > MAX_AI_SIMILARITY_CACHE_ENTRIES:
        oldest = _ai_similarity_cache_order.pop(0)
        _ai_similarity_cache.pop(oldest, None)

    return similarity


def run_preprocessing(df: pd.DataFrame, alpha: float = DEFAULT_ALPHA,
                       beta: float = DEFAULT_BETA, gamma: float = DEFAULT_GAMMA,
                       disk_cache_key: Optional[str] = None) -> dict:
    """Run the full pre-clustering pipeline over `df` (same shape
    streaming_engine.run_engine() takes: alert_id, timestamp[ms epoch], host,
    metric, value, severity, message, source). Stores the full result
    in-memory and returns a lightweight summary + the id to fetch it by.
    disk_cache_key optionally persists the embeddings step to disk (see
    build_ai_similarity_lookup's docstring)."""
    n = len(df)
    if n > MAX_ALERTS_FOR_PREPROCESS:
        raise ValueError(f"alert_count {n} exceeds MAX_ALERTS_FOR_PREPROCESS={MAX_ALERTS_FOR_PREPROCESS}")

    alerts = df.to_dict(orient="records")
    embeddings = _get_or_compute_embeddings(df, alerts, disk_cache_key)
    timestamps = (df["timestamp"].to_numpy(dtype=np.float64)) / 1000.0  # ms -> seconds
    hosts = df["host"].tolist()

    distance, components = composite_distance_matrix(embeddings, timestamps, hosts, alpha, beta, gamma)

    preprocessing_id = str(uuid.uuid4())
    result = {
        "id": preprocessing_id,
        "created_at": time.time(),
        "alerts": alerts,
        "embeddings": embeddings,
        "semantic_distance": components["semantic"],
        "temporal_distance": components["temporal"],
        "host_distance": components["host"],
        "composite_distance": distance,
        "weights": components["weights"],
        "embedding_backend": get_backend_name(),
    }
    _store[preprocessing_id] = result
    _insertion_order.append(preprocessing_id)
    _evict_if_needed()

    return summarize(result)


def get_full_result(preprocessing_id: str) -> Optional[dict]:
    return _store.get(preprocessing_id)


def summarize(result: dict) -> dict:
    composite = result["composite_distance"]
    n = composite.shape[0]
    off_diag = composite[~np.eye(n, dtype=bool)] if n > 1 else np.array([])
    return {
        "preprocessing_id": result["id"],
        "alert_count": n,
        "embedding_backend": result["embedding_backend"],
        "embedding_dimensions": int(result["embeddings"].shape[1]) if n else 0,
        "weights": result["weights"],
        "composite_distance_stats": {
            "min": float(off_diag.min()) if off_diag.size else 0.0,
            "max": float(off_diag.max()) if off_diag.size else 0.0,
            "mean": float(off_diag.mean()) if off_diag.size else 0.0,
        },
    }


def full_matrices(result: dict) -> dict:
    return {
        "preprocessing_id": result["id"],
        "alert_count": result["composite_distance"].shape[0],
        "embeddings": result["embeddings"].tolist(),
        "semantic_distance": result["semantic_distance"].tolist(),
        "temporal_distance": result["temporal_distance"].tolist(),
        "host_distance": result["host_distance"].tolist(),
        "composite_distance": result["composite_distance"].tolist(),
        "weights": result["weights"],
    }


def most_similar(result: dict, alert_id: str, top_k: int = 5) -> Optional[dict]:
    """Top-k most similar alerts to `alert_id` by composite distance
    (ascending -- lowest distance first), with each distance component
    reframed as a 0-1 similarity score (1 - distance) for readability.
    This is exactly the distance HDBSCAN would consume later, surfaced here
    so it's inspectable before any clustering exists."""
    alerts = result["alerts"]
    index_by_id = {a["alert_id"]: i for i, a in enumerate(alerts)}
    if alert_id not in index_by_id:
        return None
    i = index_by_id[alert_id]

    composite = result["composite_distance"][i]
    order = np.argsort(composite)
    order = [j for j in order if j != i][:top_k]

    semantic, temporal, host = result["semantic_distance"][i], result["temporal_distance"][i], result["host_distance"][i]

    return {
        "alert": alerts[i],
        "most_similar": [
            {
                "alert": alerts[j],
                "semantic_similarity": round(1.0 - float(semantic[j]), 4),
                "temporal_score": round(1.0 - float(temporal[j]), 4),
                "host_score": round(1.0 - float(host[j]), 4),
                "composite_score": round(1.0 - float(composite[j]), 4),
            }
            for j in order
        ],
    }
