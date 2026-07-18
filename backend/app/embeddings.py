"""
Text embedding for alert messages.

Recovered from git history (commit 848d63a^, backend/app/pipeline/embeddings.py
before it was deleted as unreachable dead code) -- the embedding logic itself
is unchanged from that version.

Primary path: sentence-transformers/all-MiniLM-L6-v2, a small (~80MB) model
that embeds a sentence into a 384-dim vector in a few milliseconds on CPU.
It's loaded once (lazy singleton) and reused for the lifetime of the process.

Fallback path: if the model can't be loaded (no internet on first run, so the
weights can't be downloaded and cached), we fall back to a TF-IDF vectorizer
fit on the alert corpus. This keeps the "must never break on stage" guarantee
-- preprocessing still works, just with a cruder notion of semantic similarity.
The active backend is surfaced via get_backend_name() so callers can report
which path is live.

alert_to_text() is new here (the original alert shape had no equivalent):
this dataset's `message` field is one of only 7 fixed strings (see
data_pipeline/generate_alerts.py::ALERT_RULES), so embedding it alone would give
every alert of the same type an identical vector. Building one natural-
language sentence per alert from all its fields gives the model something
to actually differentiate on.

load/save_cached_embeddings() are also new: embedding is O(n) but not free
-- measured at ~290s for the full 100,000-alert demo slice on this machine
(the model itself is a lazy in-process singleton, so that cost is otherwise
paid every time the process restarts, e.g. Render spinning down on the free
tier). Cached to disk per dataset identity (`cache_key`, e.g. "demo_100000")
so it's paid once ever, not once per process lifetime.
"""
import logging
from pathlib import Path
from typing import List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize as sk_normalize

logger = logging.getLogger("nucleus.embeddings")

MODEL_NAME = "all-MiniLM-L6-v2"

EMBEDDINGS_CACHE_DIR = Path(__file__).parent / "data" / "embeddings_cache"

_model = None
_backend_name = None


def _load_model():
    global _model, _backend_name
    if _backend_name is not None:
        return
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
        _backend_name = f"sentence-transformers/{MODEL_NAME}"
        logger.info("embedding backend: %s", _backend_name)
    except Exception as exc:
        logger.warning(
            "sentence-transformers model unavailable (%s); falling back to TF-IDF embeddings", exc,
        )
        _model = None
        _backend_name = "tfidf-fallback"


def get_backend_name() -> str:
    _load_model()
    return _backend_name


def _host_type_label(host: str) -> str:
    if host.startswith("os_"):
        return "Linux"
    if host.startswith("db_"):
        return "Oracle Database"
    return "unknown-type"


def alert_to_text(host: str, metric: str, severity: str, value: float, message: str) -> str:
    """One natural-language sentence per alert, built from every field, so
    two alerts that trigger the same fixed rule message still get distinct
    embeddings (differentiated by host, host type, metric, and value)."""
    host_type = _host_type_label(host)
    return f"{severity} alert on {host_type} host {host}: {message} ({metric} = {value})."


def _cache_path(cache_key: str) -> Path:
    # cache_key is always one of a handful of caller-controlled strings
    # ("demo_100", "full_dataset", ...), never raw user input.
    return EMBEDDINGS_CACHE_DIR / f"{cache_key}.npy"


def load_cached_embeddings(cache_key: str) -> Optional[np.ndarray]:
    """Load a previously-saved (n, d) embeddings array from disk, or None
    if nothing's cached for this key yet."""
    path = _cache_path(cache_key)
    if not path.exists():
        return None
    try:
        return np.load(path)
    except Exception as exc:
        logger.warning("failed to load cached embeddings from %s (%s); will recompute", path, exc)
        return None


def save_cached_embeddings(cache_key: str, embeddings: np.ndarray) -> None:
    EMBEDDINGS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.save(_cache_path(cache_key), embeddings)


def _tfidf_embed(messages: List[str]) -> np.ndarray:
    vectorizer = TfidfVectorizer(max_features=2048, stop_words="english")
    matrix = vectorizer.fit_transform(messages)
    dense = matrix.toarray().astype(np.float32)
    return sk_normalize(dense)


def embed_messages(messages: List[str]) -> np.ndarray:
    """Embed a batch of alert texts into L2-normalized vectors, shape (n, d)."""
    _load_model()
    if _model is not None:
        try:
            vectors = _model.encode(
                messages, normalize_embeddings=True, show_progress_bar=False, batch_size=64,
            )
            return np.asarray(vectors, dtype=np.float32)
        except Exception as exc:
            logger.warning("sentence-transformers encode() failed (%s); falling back to TF-IDF", exc)
            global _backend_name
            _backend_name = "tfidf-fallback"
    return _tfidf_embed(messages)
