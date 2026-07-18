"""
Composite distance metric.

    distance = alpha * semantic_distance + beta * temporal_distance + gamma * host_distance

Each component is independently normalized to [0, 1] before weighting so that
alpha/beta/gamma are directly comparable "how much does this factor matter"
knobs -- doubling alpha always has the same relative effect regardless of how
beta/gamma are set, because the three weights are re-normalized to sum to 1
before being applied.

Recovered from git history (commit 848d63a^, backend/app/pipeline/distance.py)
with two adaptations for this dataset:

- No config.py: the two tunable constants below (TEMPORAL_NORMALIZER_SECONDS,
  DEFAULT_ALPHA/BETA/GAMMA) live here at module level instead, matching how
  streaming_engine.py already keeps its own constants rather than a shared
  config file.
- No service_graph.py: the original service_penalty() did a BFS hop-distance
  over a hand-authored 16-node microservice graph that doesn't correspond to
  anything in this dataset (real host IDs, no known dependency topology).
  Replaced with host_distance() below, graded by host-ID prefix -- the one
  real signal this dataset actually has. It's a single-function seam
  (host_a, host_b) -> float so a real dependency graph can replace the body
  later without anything above it changing.

This module is pure numpy -- no FastAPI, no I/O -- so it's usable standalone
and, later, directly by a clustering step (e.g. HDBSCAN with metric="precomputed"
against composite_distance_matrix()'s output) with no changes required here.
"""
import numpy as np

# Alerts more than this many seconds apart are treated as maximally distant in
# time (distance 1.0), regardless of how large the batch is -- a fixed
# constant rather than "max gap observed in this batch" so the same absolute
# gap always scores the same distance no matter what else is in the batch.
TEMPORAL_NORMALIZER_SECONDS = 900.0  # 15 minutes

# Default composite-distance weights, used when the caller omits them.
# Carried over from the pre-deletion implementation (grid-searched against a
# different, synthetic dataset) -- a reasonable starting point, not validated
# against AIOps2020's actual structure.
DEFAULT_ALPHA = 0.15  # semantic
DEFAULT_BETA = 0.55   # temporal
DEFAULT_GAMMA = 0.3   # host

# Graded host-distance tiers. Same host is 0; same infrastructure *type*
# (two Oracle DB hosts, or two Linux hosts) is closer than two hosts of
# different types. Oracle hosts are graded closer to each other than Linux
# hosts are, on the assumption that a DB tier (e.g. RAC-style clustering,
# shared storage) is more inherently coupled than a set of independent,
# load-balanced app hosts -- a modeling assumption, not measured fact, and
# the first thing to revisit if a real dependency graph becomes available.
SAME_HOST_DISTANCE = 0.0
SAME_ORACLE_CLUSTER_DISTANCE = 0.2
SAME_LINUX_CLUSTER_DISTANCE = 0.5
CROSS_TYPE_DISTANCE = 0.9
UNKNOWN_HOST_DISTANCE = 1.0


def _host_type(host: str) -> str:
    if host.startswith("os_"):
        return "linux"
    if host.startswith("db_"):
        return "oracle"
    return "unknown"


def host_distance(host_a: str, host_b: str) -> float:
    """Graded 0-1 distance between two host IDs. This is the seam a real
    service/host dependency graph would replace -- same signature, same
    range, nothing else in this module needs to change."""
    if host_a == host_b:
        return SAME_HOST_DISTANCE
    type_a, type_b = _host_type(host_a), _host_type(host_b)
    if type_a == "unknown" or type_b == "unknown":
        return UNKNOWN_HOST_DISTANCE
    if type_a != type_b:
        return CROSS_TYPE_DISTANCE
    return SAME_ORACLE_CLUSTER_DISTANCE if type_a == "oracle" else SAME_LINUX_CLUSTER_DISTANCE


def _semantic_distance_matrix(sub_embeddings: np.ndarray) -> np.ndarray:
    """1 - cosine_similarity, rescaled from [0,2] to [0,1]. Embeddings are
    assumed L2-normalized so the dot product IS the cosine similarity."""
    cos_sim = sub_embeddings @ sub_embeddings.T
    cos_sim = np.clip(cos_sim, -1.0, 1.0)
    return (1.0 - cos_sim) / 2.0


def _temporal_distance_matrix(sub_timestamps: np.ndarray) -> np.ndarray:
    """Absolute time difference (seconds) normalized by a fixed timescale."""
    diffs = np.abs(sub_timestamps[:, None] - sub_timestamps[None, :])
    return np.clip(diffs / TEMPORAL_NORMALIZER_SECONDS, 0.0, 1.0)


def _host_distance_matrix(sub_hosts) -> np.ndarray:
    n = len(sub_hosts)
    matrix = np.zeros((n, n), dtype=np.float32)
    # Cache pairwise lookups per unique host pair -- there are far fewer
    # distinct hosts than alerts, so this collapses an O(n^2) Python loop
    # down to O(u^2) for u unique hosts in the batch.
    unique_hosts = sorted(set(sub_hosts))
    pair_cache = {(a, b): host_distance(a, b) for a in unique_hosts for b in unique_hosts}
    for i in range(n):
        for j in range(n):
            matrix[i, j] = pair_cache[(sub_hosts[i], sub_hosts[j])]
    return matrix


def composite_distance_matrix(sub_embeddings: np.ndarray, sub_timestamps: np.ndarray,
                               sub_hosts, alpha: float, beta: float, gamma: float):
    """Compute the (n, n) composite distance matrix for one batch of alerts.

    Returns (distance_matrix, components) where components is a dict with the
    raw un-weighted semantic/temporal/host matrices, useful for debugging
    or explaining a distance value.
    """
    semantic = _semantic_distance_matrix(sub_embeddings)
    temporal = _temporal_distance_matrix(sub_timestamps)
    host = _host_distance_matrix(sub_hosts)

    total_weight = alpha + beta + gamma
    if total_weight <= 0:
        alpha, beta, gamma = 1.0, 1.0, 1.0
        total_weight = 3.0
    a, b, g = alpha / total_weight, beta / total_weight, gamma / total_weight

    distance = a * semantic + b * temporal + g * host
    np.fill_diagonal(distance, 0.0)
    distance = np.clip(distance, 0.0, 1.0)

    return distance.astype(np.float64), {
        "semantic": semantic, "temporal": temporal, "host": host,
        "weights": {"alpha": a, "beta": b, "gamma": g},
    }


# --- Scalar (single-pair) counterparts -------------------------------------
#
# Same formulas as the matrix versions above, evaluated for one pair instead
# of a whole batch. These exist for streaming_engine.py's optional AI-scoring
# path (see preprocessing.build_ai_similarity_lookup): the streaming engine
# compares one candidate alert against one incident's last alert at a time,
# never the full n x n set, so computing (and holding in memory) the full
# matrix for a 132,927-row run isn't viable -- these make the same math
# available per-pair, at O(1) cost instead of O(n^2) memory.

def semantic_distance_pair(embedding_a: np.ndarray, embedding_b: np.ndarray) -> float:
    """1 - cosine_similarity for one pair of L2-normalized embeddings."""
    cos_sim = float(np.clip(np.dot(embedding_a, embedding_b), -1.0, 1.0))
    return (1.0 - cos_sim) / 2.0


def temporal_distance_pair(timestamp_a: float, timestamp_b: float) -> float:
    """Same normalization as _temporal_distance_matrix, one pair."""
    return float(np.clip(abs(timestamp_a - timestamp_b) / TEMPORAL_NORMALIZER_SECONDS, 0.0, 1.0))


def composite_distance_pair(embedding_a: np.ndarray, embedding_b: np.ndarray,
                             timestamp_a: float, timestamp_b: float,
                             host_a: str, host_b: str,
                             alpha: float, beta: float, gamma: float) -> float:
    """Same weighting/normalization as composite_distance_matrix, one pair."""
    semantic = semantic_distance_pair(embedding_a, embedding_b)
    temporal = temporal_distance_pair(timestamp_a, timestamp_b)
    host = host_distance(host_a, host_b)

    total_weight = alpha + beta + gamma
    if total_weight <= 0:
        alpha, beta, gamma = 1.0, 1.0, 1.0
        total_weight = 3.0
    a, b, g = alpha / total_weight, beta / total_weight, gamma / total_weight

    return float(np.clip(a * semantic + b * temporal + g * host, 0.0, 1.0))
