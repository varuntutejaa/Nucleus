"""
Text embedding for alert messages.

Primary path: sentence-transformers/all-MiniLM-L6-v2, a small (~80MB) model
that embeds a sentence into a 384-dim vector in a few milliseconds on CPU.
It's loaded once (lazy singleton) and reused for the lifetime of the process.

Fallback path: if the model can't be loaded (no internet on first run, so the
weights can't be downloaded and cached), we fall back to a TF-IDF vectorizer
fit on the alert corpus. This keeps the "must never break on stage" guarantee
-- clustering still works, just with a cruder notion of semantic similarity.
The active backend is surfaced in API metrics (`embedding_backend`) so the
demo is transparent about which path is live.

Embeddings are computed once per ingested alert batch (see app/main.py) and
cached; the composite-distance/clustering pipeline only ever slices rows out
of this precomputed matrix, so moving the alpha/beta/gamma sliders never
triggers re-embedding -- only re-weighting of an already-computed matrix.
"""
import logging
from typing import List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize as sk_normalize

logger = logging.getLogger("nucleus.embeddings")

MODEL_NAME = "all-MiniLM-L6-v2"

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


def strip_service_prefix(message: str, service: str) -> str:
    """Alert messages are formatted as "{service}: {description}" for display.
    Service identity is already carried by the `service_penalty` distance
    component, so embedding it a second time inside the text would let two
    unrelated alerts on the same service (or two related ones on different
    services) skew semantic_distance for a reason that has nothing to do
    with actual message content. Strip it before embedding so semantic
    similarity reflects the description only.
    """
    prefix = f"{service}: "
    if message.startswith(prefix):
        return message[len(prefix):]
    return message


def _tfidf_embed(messages: List[str]) -> np.ndarray:
    vectorizer = TfidfVectorizer(max_features=2048, stop_words="english")
    matrix = vectorizer.fit_transform(messages)
    dense = matrix.toarray().astype(np.float32)
    return sk_normalize(dense)


def embed_messages(messages: List[str]) -> np.ndarray:
    """Embed a batch of alert messages into L2-normalized vectors, shape (n, d)."""
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
