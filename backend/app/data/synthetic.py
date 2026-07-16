"""
Synthetic alert generator.

This is the demo's reliability backbone: real-dataset parsing (loghub_loader.py)
is a bonus, but this generator is what actually runs on stage. It must always
produce a clean, explainable result -- a fixed number of root-cause incidents,
each spawning a burst of correlated downstream symptom alerts on neighboring
services, plus a wash of unrelated background noise that shouldn't cluster
with anything.

Ground truth (`incident_id`) is attached to every alert we generate but is
never returned by the API -- it exists only so the sanity-check script and
local debugging can measure clustering quality against a known answer key.
The dashboard and the clustering pipeline never see it.
"""
import itertools
import random
import time
from datetime import datetime, timezone

from app.data.service_graph import ALL_SERVICES, neighbors_within

SEVERITY_RANK = {"critical": 3, "warning": 2, "info": 1}

# Each entry: (kind, callable(rng, service) -> message)
ROOT_CAUSE_TEMPLATES = [
    ("db_pool_exhausted", lambda r, s: f"{s}: connection pool exhausted ({r.randint(190, 200)}/200 active connections)"),
    ("disk_io_spike", lambda r, s: f"{s}: disk I/O latency spike detected (p99 {r.randint(800, 2400)}ms)"),
    ("oom_kill", lambda r, s: f"{s}: pod OOMKilled, memory usage hit {r.randint(980, 1024)}Mi limit"),
    ("deploy_regression", lambda r, s: f"{s}: post-deploy error rate spike to {r.randint(15, 60)}% on release v{r.randint(2, 9)}.{r.randint(0, 9)}.{r.randint(0, 9)}"),
    ("network_partition", lambda r, s: f"{s}: network partition detected, {r.randint(20, 80)}% packet loss to upstream"),
    ("cert_expired", lambda r, s: f"{s}: TLS certificate expired, upstream handshake failures"),
    ("cpu_saturation", lambda r, s: f"{s}: CPU utilization sustained at {r.randint(92, 100)}% for 5m"),
]

SYMPTOM_TEMPLATES = [
    ("latency_breach", lambda r, s: f"{s}: request latency p99 breached SLO ({r.randint(520, 3000)}ms > 500ms)"),
    ("error_rate", lambda r, s: f"{s}: 5xx error rate elevated to {r.randint(5, 45)}%"),
    ("timeout", lambda r, s: f"{s}: upstream request timeout after {r.randint(1000, 5000)}ms, retrying"),
    ("queue_growth", lambda r, s: f"{s}: task queue depth growing ({r.randint(150, 5000)} pending)"),
    ("circuit_breaker", lambda r, s: f"{s}: circuit breaker OPEN for downstream dependency"),
    ("replica_lag", lambda r, s: f"{s}: replica lag increasing ({r.randint(5, 120)}s behind primary)"),
    ("health_check_fail", lambda r, s: f"{s}: readiness probe failing, {r.randint(1, 3)}/3 consecutive failures"),
    ("dependency_degraded", lambda r, s: f"{s}: degraded response from dependency, success rate {r.randint(40, 85)}%"),
]

NOISE_TEMPLATES = [
    ("scheduled_backup", lambda r, s: f"{s}: scheduled backup completed successfully"),
    ("cert_renewal", lambda r, s: f"{s}: TLS certificate renewal reminder ({r.randint(10, 30)} days remaining)"),
    ("autoscale", lambda r, s: f"{s}: autoscaler added 1 replica (target CPU {r.randint(50, 70)}%)"),
    ("config_reload", lambda r, s: f"{s}: configuration reloaded from ConfigMap"),
    ("deploy_success", lambda r, s: f"{s}: deployment v{r.randint(2, 9)}.{r.randint(0, 9)}.{r.randint(0, 9)} rolled out successfully"),
    ("cache_warm", lambda r, s: f"{s}: cache warm-up completed ({r.randint(1000, 50000)} keys loaded)"),
    ("routine_gc", lambda r, s: f"{s}: garbage collection pause {r.randint(20, 180)}ms (within budget)"),
    ("low_disk_info", lambda r, s: f"{s}: disk usage at {r.randint(30, 65)}%, within normal range")
]

# Services with a rich enough neighborhood to make an interesting incident.
_ROOT_CANDIDATES = ["payment-service", "payment-db", "checkout-service", "inventory-service",
                     "order-service", "order-db", "api-gateway", "search-service", "auth-service"]


def _build_alert(counter, timestamp, service, severity, message, incident_id, source):
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return {
        "id": f"alt-{next(counter):05d}",
        "timestamp": dt.isoformat(),
        "timestamp_unix": timestamp,
        "service": service,
        "severity": severity,
        "severity_rank": SEVERITY_RANK[severity],
        "message": message,
        "source": source,
        "incident_id": incident_id,  # ground truth, stripped before API responses
    }


def generate_alerts(seed: int = 42, num_incidents: int = 8, target_total: int = 800,
                     duration_hours: float = 6.0):
    """Generate a synthetic burst of alerts: `num_incidents` root-cause incidents
    each with a cluster of correlated symptoms, plus background noise, totalling
    approximately `target_total` alerts spread over `duration_hours`.
    """
    rng = random.Random(seed)
    counter = itertools.count(1)
    now = time.time()
    start_ts = now - duration_hours * 3600
    usable_span = duration_hours * 3600

    slot = usable_span / num_incidents
    incident_specs = []
    for i in range(num_incidents):
        base = start_ts + i * slot + slot * 0.1
        jitter = rng.uniform(0, slot * 0.25)
        incident_start = base + jitter
        root_service = rng.choice(_ROOT_CANDIDATES)
        symptom_count = rng.randint(70, 110)
        incident_specs.append((incident_start, root_service, symptom_count))

    reserved = sum(count + 1 for _, _, count in incident_specs)
    noise_count = max(target_total - reserved, 40)
    noise_count = min(noise_count, 150)  # cap noise density so unrelated background alerts stay temporally sparse

    alerts = []
    for idx, (incident_start, root_service, symptom_count) in enumerate(incident_specs):
        incident_id = f"incident-{idx + 1}"
        _, root_fn = rng.choice(ROOT_CAUSE_TEMPLATES)
        alerts.append(_build_alert(
            counter, incident_start, root_service, "critical",
            root_fn(rng, root_service), incident_id, "synthetic",
        ))

        neighbor_pool = neighbors_within(root_service, max_hops=1)
        if not neighbor_pool:
            neighbor_pool = [(root_service, 0)]
        # the root service itself is also a very plausible source of symptom alerts
        neighbor_pool = neighbor_pool + [(root_service, 0)] * max(1, len(neighbor_pool) // 2)

        for _ in range(symptom_count):
            svc, hops = rng.choice(neighbor_pool)
            delay = rng.uniform(3, 240) * (1 + hops * 0.35)
            ts = incident_start + delay
            _, symptom_fn = rng.choice(SYMPTOM_TEMPLATES)
            severity = rng.choices(["critical", "warning"], weights=[0.35, 0.65])[0]
            alerts.append(_build_alert(
                counter, ts, svc, severity, symptom_fn(rng, svc), incident_id, "synthetic",
            ))

    # Background noise: evenly-spaced (with jitter) timestamps, and a
    # shuffled round-robin "bag" of (service, template) pairs so the same
    # routine message never recurs on the same service within roughly one
    # full bag cycle. Without this, independent uniform draws inevitably
    # clump a handful of identical-looking noise events close together in
    # time purely by chance -- and since they're the same service AND near-
    # identical text, the clustering pipeline (correctly!) treats "close in
    # time + same service + same wording" as a correlation signal, turning
    # coincidental noise into large spurious clusters that swamp the real
    # incidents. Spacing out recurrences keeps noise genuinely uncorrelated.
    noise_times = []
    for i in range(noise_count):
        base = start_ts + (i / noise_count) * usable_span
        jitter = rng.uniform(-usable_span / noise_count * 0.4, usable_span / noise_count * 0.4)
        noise_times.append(base + jitter)
    noise_times.sort()

    pairs = [(svc, idx) for svc in ALL_SERVICES for idx in range(len(NOISE_TEMPLATES))]
    rng.shuffle(pairs)
    bag, bag_pos = pairs, 0

    for ts in noise_times:
        if bag_pos >= len(bag):
            bag = pairs[:]
            rng.shuffle(bag)
            bag_pos = 0
        svc, tmpl_idx = bag[bag_pos]
        bag_pos += 1
        _, noise_fn = NOISE_TEMPLATES[tmpl_idx]
        severity = rng.choices(["info", "warning"], weights=[0.8, 0.2])[0]
        alerts.append(_build_alert(
            counter, ts, svc, severity, noise_fn(rng, svc), None, "synthetic",
        ))

    alerts.sort(key=lambda a: a["timestamp_unix"])
    # Re-assign ids in chronological order for readable demo output.
    for i, a in enumerate(alerts, start=1):
        a["id"] = f"alt-{i:05d}"

    return alerts
