"""PubMedBERT loading + embedding for runtime inference.

The v1.5.2 ML path needs to embed an asset's eligibility-criteria text
through PubMedBERT (mean-pooled, 768-dim) and concatenate with the
36-dim structured feature vector. This module owns the model lifecycle:

- `get_model()` is the singleton accessor — lazy-loads the model + tokenizer
  on first call, caches them at module scope for the worker's lifetime.
- `embed_text(text)` runs the mean-pool inference and returns a numpy
  array. Validates input + matches the training-time parameters
  (max_length=512, pool='mean') so the runtime embedding distribution
  matches what the LGBM was trained on.

The model + tokenizer are pre-downloaded into the Docker image at build
time (see api/Dockerfile) — first inference doesn't pay for the network
fetch, only the model load into memory (~5-10 sec on Fly's CPU).

Memory: PubMedBERT-base is ~440 MB at fp32. Combined with FastAPI +
deps the container peaks around 700-800 MB. Fits in the 1 GB
shared-cpu-2x Fly machine declared in fly.toml.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from transformers import PreTrainedModel, PreTrainedTokenizer

log = logging.getLogger(__name__)

# Must match the training-time configuration (data_pipeline/train_gbt.py +
# the Colab notebook). Recorded redundantly in the model.joblib feature_schema
# sidecar; engine._load_model() asserts they agree.
MODEL_ID = "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"
MAX_LENGTH = 512
POOL_METHOD = "mean"
EMBEDDING_DIM = 768

# Module-level singletons + lock — lazy-init on first call.
_tokenizer: "PreTrainedTokenizer | None" = None
_model: "PreTrainedModel | None" = None
_load_lock = threading.Lock()


def _load_model_and_tokenizer():
    """Lazy singleton load. Thread-safe via double-checked locking."""
    global _tokenizer, _model

    if _model is not None and _tokenizer is not None:
        return _tokenizer, _model

    with _load_lock:
        # Re-check under the lock — another thread may have loaded already
        if _model is not None and _tokenizer is not None:
            return _tokenizer, _model

        log.info("loading PubMedBERT (%s) — first inference will be slow", MODEL_ID)
        # Deferred imports so the test environment doesn't have to install
        # torch + transformers just to import this module
        import torch  # noqa: F401  (validates the dependency exists)
        from transformers import AutoModel, AutoTokenizer

        _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        _model = AutoModel.from_pretrained(MODEL_ID).eval()
        # Stay on CPU — the Fly machine has no GPU. Each inference is fast
        # enough on CPU for the rate of UI requests Asclepius serves.

        log.info("PubMedBERT loaded; hidden_size=%d", _model.config.hidden_size)
        assert _model.config.hidden_size == EMBEDDING_DIM, (
            f"PubMedBERT hidden size {_model.config.hidden_size} != "
            f"expected {EMBEDDING_DIM} — model upstream may have changed"
        )

    return _tokenizer, _model


def _mean_pool(last_hidden_state, attention_mask):
    """Mean over non-padding token embeddings. Mirrors the training-time
    implementation byte-for-byte (data_pipeline/embed_biobert.py)."""
    mask = attention_mask.unsqueeze(-1).float()
    summed = (last_hidden_state * mask).sum(dim=1)
    counts = mask.sum(dim=1).clamp(min=1e-9)
    return summed / counts


def embed_text(text: str) -> np.ndarray:
    """Embed a single eligibility-criteria text → 768-dim float32 vector.

    Same tokenization + truncation + pooling as the training pipeline:
    wordpiece-tokenize, truncate from the back at 512 tokens, mean-pool
    over non-padding positions. Raises ValueError on empty / whitespace
    input (the training pipeline drops those rows; runtime should reject
    rather than silently produce a degenerate embedding).
    """
    if not text or not text.strip():
        raise ValueError(
            "Cannot embed empty criteria text. The v1.5.2 ML path "
            "requires non-empty eligibility-criteria text — supply via "
            "the criteria_text field or an nct_id with retrievable text."
        )

    tokenizer, model = _load_model_and_tokenizer()

    # Local import — same reason as in _load_model_and_tokenizer
    import torch

    enc = tokenizer(
        text,
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    )

    with torch.no_grad():
        out = model(**enc)
        pooled = _mean_pool(out.last_hidden_state, enc["attention_mask"])

    return pooled.squeeze(0).numpy().astype(np.float32)


def is_model_loaded() -> bool:
    """For test introspection — was the singleton ever instantiated?"""
    return _model is not None and _tokenizer is not None


def _reset_for_tests() -> None:
    """Wipe the singletons. Tests call this between cases to avoid
    cross-test state leakage."""
    global _tokenizer, _model
    _tokenizer = None
    _model = None
