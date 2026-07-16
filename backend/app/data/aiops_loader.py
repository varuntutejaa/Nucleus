"""
Alert generation from raw AIOps2020 challenge-dataset metrics.

Ported from a companion rule-based prototype that ran directly against a
local copy of the real AIOps2020 dataset (multi-gigabyte trace/metric/log
bundles under `2020_MM_DD/.../<Platform Metrics>/*.csv`, keyed by `cmdb_id`).
That dataset is too large to bundle in this repo, so this loader is exercised
by pointing `dataset_root` at a local copy -- see README.md "Bringing your
own dataset". The bundled demo instead ships a real ~800-alert slice of this
loader's own output (`sample_loghub.csv`), so the "real dataset" path is
genuinely real data end to end, just not regenerated live.

Each raw metric CSV has (at least) columns: name, value, timestamp, cmdb_id.
A row becomes an alert when its metric name is in ALERT_RULES and its value
crosses that rule's threshold (see app/data/metric_rules.py).
"""
import itertools
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.data.metric_rules import ALERT_RULES, evaluate
from app.data.loghub_loader import DatasetLoadError

# The subset of AIOps2020 metric files our threshold rules cover.
METRIC_FILES = {
    "os_linux.csv",
    "db_oracle_11g.csv",
    "mw_redis.csv",
    "dcos_docker.csv",
    "dcos_container.csv",
}

_SEVERITY_RANK = {"critical": 3, "warning": 2, "info": 1}


def _process_file(csv_file: Path, counter) -> list:
    df = pd.read_csv(csv_file)
    alerts = []
    for row in df.itertuples(index=False):
        metric = getattr(row, "name", None)
        rule = ALERT_RULES.get(metric)
        if rule is None:
            continue
        try:
            value = float(row.value)
        except (TypeError, ValueError):
            continue
        if not evaluate(value, rule):
            continue

        ts_ms = float(row.timestamp)
        dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
        severity = rule["severity"]
        alerts.append({
            "id": f"alt-{next(counter):05d}",
            "timestamp": dt.isoformat(),
            "timestamp_unix": ts_ms / 1000.0,
            "service": str(row.cmdb_id),
            "severity": severity,
            "severity_rank": _SEVERITY_RANK[severity],
            "message": f"{str(row.cmdb_id)}: {rule['message']} ({metric}={value:g})",
            "source": "dataset",
            "incident_id": None,
        })
    return alerts


def generate_from_raw_dataset(dataset_root: Path) -> list:
    """Scan a local AIOps2020 dataset copy and generate alerts via threshold
    rules. Raises DatasetLoadError if the root doesn't exist or no metric
    files are found -- callers should fall back to the bundled sample."""
    dataset_root = Path(dataset_root)
    if not dataset_root.exists():
        raise DatasetLoadError(f"AIOps2020 dataset root not found: {dataset_root}")

    counter = itertools.count(1)
    alerts = []
    found_any_file = False
    for csv_file in dataset_root.rglob("*.csv"):
        if csv_file.name not in METRIC_FILES:
            continue
        found_any_file = True
        try:
            alerts.extend(_process_file(csv_file, counter))
        except Exception as exc:
            raise DatasetLoadError(f"failed to parse {csv_file}: {exc}") from exc

    if not found_any_file:
        raise DatasetLoadError(f"no recognized metric files under {dataset_root}")
    if not alerts:
        raise DatasetLoadError(f"{dataset_root} produced zero alerts (no rule crossed threshold)")

    alerts.sort(key=lambda a: a["timestamp_unix"])
    for i, a in enumerate(alerts, start=1):
        a["id"] = f"alt-{i:05d}"
    return alerts
