"""
In-memory alert store (no database per the project's non-goals).

Each distinct `source` ("synthetic" or "dataset") is loaded and embedded once,
then cached for the lifetime of the process -- embeddings don't change when
the frontend's alpha/beta/gamma sliders move, only the distance weighting and
clustering do, so there's no reason to ever recompute them per-request. The
synthetic batch is warmed at startup (see app/main.py) so the very first
request during a live demo doesn't pay the embedding cold-start cost.

`source=dataset` has a three-tier fallback, each stage catching only the
failure mode it can actually fix:
  1. A local real AIOps2020 dataset copy, if NUCLEUS_AIOPS_DATASET_ROOT is
     set and exists -- alerts are regenerated live via threshold rules
     (app/data/aiops_loader.py).
  2. The bundled sample_loghub.csv -- a real ~675-alert slice of that same
     rule engine's output, checked into the repo so the "real dataset" path
     works with zero setup.
  3. The synthetic generator, if even the bundled sample is somehow missing
     or corrupted -- the live demo must never break on stage.
"""
import logging

from app.config import AIOPS_RAW_DATASET_ROOT
from app.data.aiops_loader import generate_from_raw_dataset
from app.data.loghub_loader import DatasetLoadError, load_dataset
from app.data.synthetic import generate_alerts
from app.pipeline.embeddings import embed_messages, strip_service_prefix

logger = logging.getLogger("nucleus.store")

_cache = {}


def _load_source(source: str):
    if source != "dataset":
        return generate_alerts()

    if AIOPS_RAW_DATASET_ROOT:
        try:
            return generate_from_raw_dataset(AIOPS_RAW_DATASET_ROOT)
        except DatasetLoadError as exc:
            logger.warning("raw AIOps2020 dataset unavailable (%s); trying bundled sample", exc)

    try:
        return load_dataset()
    except DatasetLoadError as exc:
        logger.warning("bundled dataset sample failed to load (%s); falling back to synthetic generator", exc)
        return generate_alerts()


def get_alert_batch(source: str) -> dict:
    """Return {"alerts": [...], "embeddings": ndarray} for the given source,
    computing and caching it on first use."""
    if source in _cache:
        return _cache[source]

    alerts = _load_source(source)
    texts = [strip_service_prefix(a["message"], a["service"]) for a in alerts]
    embeddings = embed_messages(texts)

    entry = {"alerts": alerts, "embeddings": embeddings}
    _cache[source] = entry
    return entry
