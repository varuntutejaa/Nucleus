"""
Ground-truth accuracy validation for streaming_engine.py.

The real AIOps2020 dataset has no true incident labels -- nobody knows the
"correct" grouping for real telemetry, so streaming_engine.py's output on it
can only be checked for internal *coherence* (same host/metric/severity
purity -- see the checks used throughout this project's tuning work), never
actual accuracy against a known answer.

This generates a SYNTHETIC alert set with a KNOWN correct answer instead --
adapted from the pre-deletion synthetic.py (git history, commit 848d63a^,
which did the same root-cause + symptom-burst + background-noise structure
for the old, since-removed HDBSCAN pipeline) -- rewritten to emit alerts in
the CURRENT schema (alert_id, timestamp[ms], host, metric, value, severity,
message, source), using your REAL host IDs (pulled live from the bundled
dataset) and REAL threshold rules (mirrors data_pipeline/generate_alerts.py
::ALERT_RULES), so it exercises the exact schema and code path production
alerts do -- not a parallel toy format the old version used (fake
microservice names, a hand-authored dependency graph).

Ground truth (`true_incident_id`) is attached to every generated alert but is
stripped before being handed to streaming_engine.py -- the engine never sees
it, same "answer key the engine can't cheat off of" guarantee the old
synthetic.py had. Scoring uses sklearn's adjusted_rand_score (permutation-
invariant -- true and predicted incident IDs use unrelated numbering, ARI
doesn't care) plus human-readable fragmentation/merge counts.

Run: cd backend && python scripts/validate_correlation.py
"""
import random
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from sklearn.metrics import adjusted_rand_score

from app.aiops_full_loader import load_full_dataset
from app.streaming_engine import run_engine

# Mirrors data_pipeline/generate_alerts.py::ALERT_RULES -- duplicated (not
# imported) since that module lives outside the backend/ package and this
# script only needs the severity/message/threshold shape, not the generator
# itself.
ALERT_RULES = {
    "CPU_util_pct": {"threshold": 0.90, "severity": "Critical", "message": "High CPU Utilization"},
    "Processor_load_5_min": {"threshold": 0.80, "severity": "Warning", "message": "High Processor Load"},
    "MEM_real_util": {"threshold": 0.90, "severity": "Critical", "message": "High Memory Utilization"},
    "Sent_errors_packets": {"threshold": 0, "severity": "Critical", "message": "Network Packet Errors"},
    "Receive_errors_packets": {"threshold": 0, "severity": "Critical", "message": "Incoming Packet Errors"},
    "Sess_Connect": {"threshold": 500, "severity": "Warning", "message": "Too Many Database Sessions"},
    "DbTime": {"threshold": 1000, "severity": "Critical", "message": "Database Response Time High"},
}
OS_METRICS = ["CPU_util_pct", "Processor_load_5_min", "MEM_real_util", "Sent_errors_packets", "Receive_errors_packets"]
DB_METRICS = ["Sess_Connect", "DbTime"]


def _value_for(metric, rng):
    rule = ALERT_RULES[metric]
    if metric in ("CPU_util_pct", "Processor_load_5_min", "MEM_real_util"):
        # Threshold is a 0-1 fraction but real readings are a 0-100 scale
        # (the same documented miscalibration as the real dataset) -- use a
        # realistic-looking value that still trivially clears `> threshold`.
        return round(rng.uniform(5, 35), 2)
    if metric in ("Sent_errors_packets", "Receive_errors_packets"):
        return rng.randint(1, 20)
    threshold = int(rule["threshold"])
    return rng.randint(threshold + 1, threshold * 3)


def generate_synthetic_alerts(real_hosts, seed=42, num_incidents=15, symptoms_per_incident=(3, 8),
                               noise_count=200, duration_hours=6.0):
    """Root-cause + correlated symptom bursts (known true_incident_id, all on
    one real host per burst -- streaming_engine.py can only ever group within
    a single host anyway) plus scattered background noise (each its own
    singleton true incident)."""
    rng = random.Random(seed)
    os_hosts = [h for h in real_hosts if h.startswith("os_")]
    db_hosts = [h for h in real_hosts if h.startswith("db_")]

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=duration_hours)
    span_seconds = duration_hours * 3600

    alerts = []
    incident_counter = 0

    def add(ts, host, metric, true_incident_id):
        rule = ALERT_RULES[metric]
        source = "os_linux.csv" if host.startswith("os_") else "db_oracle_11g.csv"
        alerts.append({
            "alert_id": str(uuid.uuid4()),
            "timestamp": int(ts.timestamp() * 1000),
            "host": host,
            "metric": metric,
            "value": _value_for(metric, rng),
            "severity": rule["severity"],
            "message": rule["message"],
            "source": source,
            "true_incident_id": true_incident_id,
        })

    slot = span_seconds / num_incidents
    for i in range(num_incidents):
        base = start + timedelta(seconds=i * slot + rng.uniform(0, slot * 0.3))
        host = rng.choice(os_hosts if rng.random() < 0.6 else db_hosts)
        metrics_pool = OS_METRICS if host.startswith("os_") else DB_METRICS
        true_id = f"true-burst-{incident_counter}"
        incident_counter += 1

        # Single-metric recurrence, not a multi-metric cascade: this matches
        # what streaming_engine.py is actually designed to detect (metric
        # match is worth +0.30 of the score, and it's structurally required
        # to clear CORRELATION_THRESHOLD beyond the tight 60-180s buckets --
        # see docs/ARCHITECTURE.md), and matches what the real dataset's
        # incidents actually look like (100% single-metric, confirmed
        # separately). A small fraction of bursts are deliberately
        # multi-metric to confirm the engine still correctly keeps those
        # apart rather than inventing false cross-metric correlation.
        is_cascade = rng.random() < 0.15
        metric = rng.choice(metrics_pool)
        add(base, host, metric, true_id)
        for _ in range(rng.randint(*symptoms_per_incident)):
            delay = rng.uniform(5, 8 * 60)  # 5s to 8min after root -- spans both tight and edge-of-window cases
            symptom_metric = rng.choice(metrics_pool) if is_cascade else metric
            add(base + timedelta(seconds=delay), host, symptom_metric, true_id)

    # Background noise: shuffled round-robin (host, metric) pairs, cycling
    # without repeats until exhausted (then reshuffled) -- same technique the
    # pre-deletion synthetic.py used, and for the same reason: independent
    # uniform draws inevitably put a few identical (host, metric) pairs close
    # together in time purely by chance, and the engine (correctly!) treats
    # "same host + same metric + close in time" as a real correlation signal.
    # Without spacing them out, coincidental noise proximity gets scored as a
    # "false merge" against ground truth when the engine's merge was actually
    # the more sensible read of that coincidence.
    pairs = [(h, m) for h in real_hosts for m in (OS_METRICS if h.startswith("os_") else DB_METRICS)]
    rng.shuffle(pairs)
    bag, bag_pos = pairs, 0
    noise_times = sorted(start + timedelta(seconds=rng.uniform(0, span_seconds)) for _ in range(noise_count))
    for ts in noise_times:
        if bag_pos >= len(bag):
            bag = pairs[:]
            rng.shuffle(bag)
            bag_pos = 0
        host, metric = bag[bag_pos]
        bag_pos += 1
        add(ts, host, metric, f"true-noise-{incident_counter}")
        incident_counter += 1

    return pd.DataFrame(alerts).sort_values("timestamp").reset_index(drop=True)


def score_against_ground_truth(df_with_truth: pd.DataFrame) -> dict:
    df_for_engine = df_with_truth.drop(columns=["true_incident_id"])
    result = run_engine(df_for_engine, include_members=True)

    predicted_by_alert = {
        m["alert_id"]: inc["incident_id"]
        for inc in result["incidents"] for m in inc["members"]
    }

    true_seq = df_with_truth["true_incident_id"].tolist()
    pred_seq = [predicted_by_alert[a] for a in df_with_truth["alert_id"]]
    ari = adjusted_rand_score(true_seq, pred_seq)

    true_sizes = df_with_truth.groupby("true_incident_id").size().to_dict()
    burst_ids = [t for t, s in true_sizes.items() if s > 1]

    true_to_pred = defaultdict(set)
    pred_to_true = defaultdict(set)
    for t, p in zip(true_seq, pred_seq):
        true_to_pred[t].add(p)
        pred_to_true[p].add(t)

    perfectly_recovered = sum(1 for t in burst_ids if len(true_to_pred[t]) == 1)
    fragmented = sum(1 for t in burst_ids if len(true_to_pred[t]) > 1)
    falsely_merged = sum(1 for ts in pred_to_true.values() if len(ts) > 1)

    return {
        "adjusted_rand_score": round(ari, 4),
        "true_burst_incidents": len(burst_ids),
        "true_noise_alerts": len(true_sizes) - len(burst_ids),
        "perfectly_recovered_bursts": perfectly_recovered,
        "fragmented_bursts": fragmented,
        "predicted_incidents_merging_different_true_incidents": falsely_merged,
        "predicted_incident_count": result["metrics"]["incident_count"],
    }


if __name__ == "__main__":
    import app.streaming_engine as se

    real_hosts = sorted(load_full_dataset()["host"].unique().tolist())
    df = generate_synthetic_alerts(real_hosts)
    print(f"generated {len(df)} synthetic alerts ({df['true_incident_id'].nunique()} true incidents) across {len(real_hosts)} real hosts\n")

    for window in [300, 600]:
        se.TIME_WINDOW_SECONDS = window
        stats = score_against_ground_truth(df)
        label = "OLD (300s)" if window == 300 else "NEW (600s)"
        print(f"--- {label} ---")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        print()
