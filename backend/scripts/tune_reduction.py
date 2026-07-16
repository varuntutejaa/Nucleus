#!/usr/bin/env python3
"""
Grid-search the clustering knobs (app/config.py) to maximize reduction_pct
*safely* on both data sources at once:

  - synthetic: validated against its ground-truth incident labels. Rejects
    any combination that merges two different incidents together, or that
    fabricates a "cluster" out of alerts that are all background noise
    (both are correctness bugs a higher reduction% would otherwise hide).
  - bundled real AIOps2020 slice: validated structurally, since it has no
    ground truth -- rejects any cluster that spans more than one real host
    (`service`), since this dataset's incidents are independent per-host
    conditions with no real cross-host cascade.

Prints every new best combination found (by min(synthetic_reduction,
real_reduction)) and the final winner. Takes a few minutes to run.
"""
import collections

import hdbscan
import numpy as np

from app.data.loghub_loader import load_dataset
from app.data.synthetic import generate_alerts
from app.pipeline.clustering import _DisjointSet
from app.pipeline.distance import composite_distance_matrix
from app.pipeline.embeddings import embed_messages, strip_service_prefix
from app.pipeline.windows import sliding_windows


def _run(alerts, embeddings, timestamps, services, alpha, beta, gamma,
         window, step, mcs, ms, eps, max_span):
    n = len(alerts)
    dsu = _DisjointSet(timestamps, max_span)
    for widx in sliding_windows(timestamps, window, step):
        if len(widx) < mcs:
            continue
        sub_emb = embeddings[widx]
        sub_ts = timestamps[widx]
        sub_svc = [services[i] for i in widx]
        dist, _ = composite_distance_matrix(sub_emb, sub_ts, sub_svc, alpha, beta, gamma)
        clusterer = hdbscan.HDBSCAN(
            metric="precomputed", min_cluster_size=mcs, min_samples=ms,
            cluster_selection_epsilon=eps,
        )
        labels = clusterer.fit_predict(dist)
        groups = collections.defaultdict(list)
        for local_idx, label in enumerate(labels):
            if label == -1:
                continue
            groups[int(label)].append(widx[local_idx])
        for group in groups.values():
            anchor = group[0]
            for other in group[1:]:
                dsu.union(anchor, other)

    global_groups = collections.defaultdict(list)
    for i in range(n):
        global_groups[dsu.find(i)].append(i)
    clusters, noise = [], []
    for members in global_groups.values():
        (noise if len(members) < 2 else clusters).append(members if len(members) >= 2 else members[0])
    return clusters, noise


def eval_synthetic(alerts, embeddings, timestamps, services, params):
    clusters, noise = _run(alerts, embeddings, timestamps, services, **params)
    n = len(alerts)
    multi_incident_merges = 0
    pure_noise_clusters = 0
    for members in clusters:
        ground_truth = [alerts[i]["incident_id"] for i in members]
        real_incidents = set(ground_truth) - {None}
        if len(real_incidents) > 1:
            multi_incident_merges += 1
        if all(x is None for x in ground_truth):
            pure_noise_clusters += 1
    visible = len(clusters) + len(noise)
    reduction_pct = round((1 - visible / n) * 100, 1)
    safe = multi_incident_merges == 0 and pure_noise_clusters == 0
    return safe, reduction_pct, len(clusters), len(noise)


def eval_real(alerts, embeddings, timestamps, services, params):
    clusters, noise = _run(alerts, embeddings, timestamps, services, **params)
    n = len(alerts)
    cross_host_merges = sum(
        1 for members in clusters if len(set(alerts[i]["service"] for i in members)) > 1
    )
    visible = len(clusters) + len(noise)
    reduction_pct = round((1 - visible / n) * 100, 1)
    return cross_host_merges == 0, reduction_pct, len(clusters), len(noise)


def main():
    print("Loading and embedding both data sources...")
    syn_alerts = generate_alerts()
    syn_texts = [strip_service_prefix(a["message"], a["service"]) for a in syn_alerts]
    syn_emb = embed_messages(syn_texts)
    syn_ts = np.array([a["timestamp_unix"] for a in syn_alerts])
    syn_svc = [a["service"] for a in syn_alerts]

    real_alerts = load_dataset()
    real_texts = [strip_service_prefix(a["message"], a["service"]) for a in real_alerts]
    real_emb = embed_messages(real_texts)
    real_ts = np.array([a["timestamp_unix"] for a in real_alerts])
    real_svc = [a["service"] for a in real_alerts]

    best = None
    for mcs in (3, 4, 5):
        for ms in (1, 2):
            for window, step in ((1200, 600), (1800, 900), (2400, 1200), (3600, 1800)):
                for max_span in (1800, 3600):
                    for eps in (0.2, 0.3, 0.4, 0.5, 0.6):
                        for alpha, beta, gamma in ((0.25, 0.45, 0.3), (0.2, 0.5, 0.3),
                                                    (0.15, 0.55, 0.3), (0.3, 0.4, 0.3)):
                            params = dict(alpha=alpha, beta=beta, gamma=gamma, window=window,
                                          step=step, mcs=mcs, ms=ms, eps=eps, max_span=max_span)
                            syn_safe, syn_red, syn_nc, syn_noise = eval_synthetic(
                                syn_alerts, syn_emb, syn_ts, syn_svc, params)
                            if not syn_safe:
                                continue
                            real_safe, real_red, real_nc, real_noise = eval_real(
                                real_alerts, real_emb, real_ts, real_svc, params)
                            if not real_safe:
                                continue
                            combined = min(syn_red, real_red)
                            if best is None or combined > best[0]:
                                best = (combined, params, syn_red, real_red, syn_nc, real_nc)
                                print(f"NEW BEST: {params} -> synthetic={syn_red}% "
                                      f"({syn_nc} clusters) real={real_red}% ({real_nc} clusters)")

    print()
    print("FINAL BEST (safe on both sources):", best)


if __name__ == "__main__":
    main()
