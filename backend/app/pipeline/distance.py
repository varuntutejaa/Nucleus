"""
Composite distance metric.

    distance = alpha * semantic_distance + beta * temporal_distance + gamma * service_penalty

Each component is independently normalized to [0, 1] before weighting so that
alpha/beta/gamma are directly comparable "how much does this factor matter"
knobs -- doubling alpha always has the same relative effect regardless of how
beta/gamma are set, because the three weights are re-normalized to sum to 1
before being applied. This is what lets the frontend sliders "visibly reshape
the clusters" instead of producing cosmetic jitter: at alpha=1,beta=0,gamma=0
you get pure semantic clustering, at beta=1 you get pure time-proximity
clustering, and so on continuously in between.
"""
import numpy as np

from app.config import TEMPORAL_NORMALIZER_SECONDS
from app.data.service_graph import service_penalty as _service_penalty_lookup


def _semantic_distance_matrix(sub_embeddings: np.ndarray) -> np.ndarray:
    """1 - cosine_similarity, rescaled from [0,2] to [0,1]. Embeddings are
    assumed L2-normalized so the dot product IS the cosine similarity."""
    cos_sim = sub_embeddings @ sub_embeddings.T
    cos_sim = np.clip(cos_sim, -1.0, 1.0)
    return (1.0 - cos_sim) / 2.0


def _temporal_distance_matrix(sub_timestamps: np.ndarray) -> np.ndarray:
    """Absolute time difference normalized by a fixed timescale (not the
    observed span of this batch -- see TEMPORAL_NORMALIZER_SECONDS docstring
    in app/config.py for why that has to be a fixed constant)."""
    diffs = np.abs(sub_timestamps[:, None] - sub_timestamps[None, :])
    return np.clip(diffs / TEMPORAL_NORMALIZER_SECONDS, 0.0, 1.0)


def _service_penalty_matrix(sub_services) -> np.ndarray:
    n = len(sub_services)
    matrix = np.zeros((n, n), dtype=np.float32)
    # Cache pairwise lookups per unique service pair -- there are far fewer
    # distinct services than alerts, so this collapses an O(n^2) Python loop
    # down to O(u^2) for u unique services in the window.
    unique_services = sorted(set(sub_services))
    pair_cache = {}
    for a in unique_services:
        for b in unique_services:
            pair_cache[(a, b)] = _service_penalty_lookup(a, b)
    for i in range(n):
        for j in range(n):
            matrix[i, j] = pair_cache[(sub_services[i], sub_services[j])]
    return matrix


def composite_distance_matrix(sub_embeddings: np.ndarray, sub_timestamps: np.ndarray,
                               sub_services, alpha: float, beta: float, gamma: float):
    """Compute the (n, n) composite distance matrix for one window/batch of alerts.

    Returns (distance_matrix, components) where components is a dict with the
    raw un-weighted semantic/temporal/service matrices, useful for debugging
    or explaining a clustering decision.
    """
    semantic = _semantic_distance_matrix(sub_embeddings)
    temporal = _temporal_distance_matrix(sub_timestamps)
    service = _service_penalty_matrix(sub_services)

    total_weight = alpha + beta + gamma
    if total_weight <= 0:
        alpha, beta, gamma = 1.0, 1.0, 1.0
        total_weight = 3.0
    a, b, g = alpha / total_weight, beta / total_weight, gamma / total_weight

    distance = a * semantic + b * temporal + g * service
    np.fill_diagonal(distance, 0.0)
    distance = np.clip(distance, 0.0, 1.0)

    return distance.astype(np.float64), {
        "semantic": semantic, "temporal": temporal, "service": service,
        "weights": {"alpha": a, "beta": b, "gamma": g},
    }
