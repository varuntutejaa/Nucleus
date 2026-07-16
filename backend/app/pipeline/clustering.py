"""
Correlation pipeline: sliding windows -> per-window composite-distance HDBSCAN
-> cross-window union-find merge -> root-cause selection -> metrics.

Why union-find across windows: each sliding window is clustered independently
(HDBSCAN needs a bounded batch, not the whole stream), so the same incident
can produce a separate local cluster in window K and window K+1 wherever they
overlap. We treat "these two alerts were ever placed in the same local
cluster" as "these two alerts belong together" and union them; the connected
components of that union-find at the end are the final global clusters. This
is also exactly what stitches a boundary-straddling incident back together.
"""
import logging
from collections import defaultdict

import hdbscan
import numpy as np

from app.config import (
    CLUSTER_SELECTION_EPSILON, MAX_INCIDENT_SPAN_SECONDS, MIN_CLUSTER_SIZE, MIN_SAMPLES,
    STEP_SECONDS, WINDOW_SECONDS,
)
from app.pipeline.distance import composite_distance_matrix
from app.pipeline.embeddings import get_backend_name
from app.pipeline.windows import sliding_windows

logger = logging.getLogger("nucleus.clustering")


class _DisjointSet:
    """Union-find with a time-span guard: a union is refused if it would
    stretch the resulting group's [min_ts, max_ts] beyond `max_span`. See
    MAX_INCIDENT_SPAN_SECONDS in app/config.py for why that's necessary."""

    def __init__(self, timestamps, max_span):
        n = len(timestamps)
        self.parent = list(range(n))
        self.min_ts = list(timestamps)
        self.max_ts = list(timestamps)
        self.max_span = max_span

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        merged_min = min(self.min_ts[ra], self.min_ts[rb])
        merged_max = max(self.max_ts[ra], self.max_ts[rb])
        if merged_max - merged_min > self.max_span:
            return  # would over-stretch a single incident's blast radius -- refuse
        self.parent[ra] = rb
        self.min_ts[rb] = merged_min
        self.max_ts[rb] = merged_max


_INTERNAL_ONLY_FIELDS = ("incident_id",)


def public_alert(alert: dict) -> dict:
    return {k: v for k, v in alert.items() if k not in _INTERNAL_ONLY_FIELDS}


def correlate(alerts: list, embeddings: np.ndarray, alpha: float, beta: float, gamma: float,
              window_seconds: float = WINDOW_SECONDS, step_seconds: float = STEP_SECONDS,
              min_cluster_size: int = MIN_CLUSTER_SIZE, min_samples: int = MIN_SAMPLES,
              cluster_selection_epsilon: float = CLUSTER_SELECTION_EPSILON,
              max_incident_span_seconds: float = MAX_INCIDENT_SPAN_SECONDS):
    """Run the full correlation pipeline over an alert batch.

    `alerts` must be sorted ascending by timestamp_unix, and `embeddings`
    must be the corresponding (n, d) matrix in the same order (row i is the
    embedding of alerts[i]).

    Returns (clusters, noise, metrics) matching the API contract.
    """
    n = len(alerts)
    if n == 0:
        return [], [], _build_metrics(0, 0, 0, 0)

    timestamps = np.array([a["timestamp_unix"] for a in alerts], dtype=np.float64)
    services = [a["service"] for a in alerts]

    dsu = _DisjointSet(timestamps, max_incident_span_seconds)
    windows = sliding_windows(timestamps, window_seconds, step_seconds)

    for window_indices in windows:
        if len(window_indices) < min_cluster_size:
            continue  # too small a batch to ever form a valid HDBSCAN cluster

        sub_emb = embeddings[window_indices]
        sub_ts = timestamps[window_indices]
        sub_services = [services[i] for i in window_indices]

        dist_matrix, _components = composite_distance_matrix(sub_emb, sub_ts, sub_services, alpha, beta, gamma)

        clusterer = hdbscan.HDBSCAN(
            metric="precomputed", min_cluster_size=min_cluster_size, min_samples=min_samples,
            cluster_selection_epsilon=cluster_selection_epsilon,
        )
        labels = clusterer.fit_predict(dist_matrix)

        label_groups = defaultdict(list)
        for local_idx, label in enumerate(labels):
            if label == -1:
                continue
            label_groups[int(label)].append(window_indices[local_idx])

        for group in label_groups.values():
            anchor = group[0]
            for other in group[1:]:
                dsu.union(anchor, other)

    global_groups = defaultdict(list)
    for i in range(n):
        global_groups[dsu.find(i)].append(i)

    clusters = []
    noise = []
    for members in global_groups.values():
        if len(members) < 2:
            noise.append(public_alert(alerts[members[0]]))
            continue

        member_alerts = [alerts[i] for i in members]
        # Root cause: earliest timestamp; severity (critical > warning > info) breaks ties.
        ordered = sorted(member_alerts, key=lambda a: (a["timestamp_unix"], -a["severity_rank"]))
        root_cause = ordered[0]
        suppressed = sorted(ordered[1:], key=lambda a: a["timestamp_unix"])

        span = max(a["timestamp_unix"] for a in member_alerts) - min(a["timestamp_unix"] for a in member_alerts)
        clusters.append({
            "cluster_id": None,  # assigned after chronological sort below
            "root_cause": public_alert(root_cause),
            "suppressed": [public_alert(a) for a in suppressed],
            "size": len(member_alerts),
            "time_span_seconds": round(span, 1),
            "explanation": (
                f"Earliest alert in cluster ({root_cause['severity']} severity) "
                f"among {len(member_alerts)} correlated alerts on {len(set(a['service'] for a in member_alerts))} service(s)."
            ),
            "_sort_ts": root_cause["timestamp_unix"],
        })

    clusters.sort(key=lambda c: c["_sort_ts"])
    for i, c in enumerate(clusters, start=1):
        c["cluster_id"] = f"cluster-{i}"
        del c["_sort_ts"]

    noise.sort(key=lambda a: a["timestamp_unix"])

    metrics = _build_metrics(
        raw_count=n,
        cluster_count=len(clusters),
        noise_count=len(noise),
        suppressed_count=sum(c["size"] for c in clusters) - len(clusters),
    )
    metrics["weights_used"] = {"alpha": alpha, "beta": beta, "gamma": gamma}

    return clusters, noise, metrics


def _build_metrics(raw_count, cluster_count, noise_count, suppressed_count):
    visible_count = cluster_count + noise_count
    reduction_pct = round((1 - visible_count / raw_count) * 100, 1) if raw_count else 0.0
    return {
        "raw_count": raw_count,
        "cluster_count": cluster_count,
        "noise_count": noise_count,
        "suppressed_count": suppressed_count,
        "reduction_pct": reduction_pct,
        "embedding_backend": get_backend_name(),
    }
