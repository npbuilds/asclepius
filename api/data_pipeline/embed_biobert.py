"""v1.5.2 Day 2 — BioBERT embeddings of criteria text.

Reads the parquet produced by build_training_dataset.py, runs each row's
`criteria_text` through `dmis-lab/biobert-v1.1`, and saves a numpy array
of mean-pooled 768-dim embeddings aligned by NCT ID.

Two execution paths:
  - Local CPU: ~3-5 sec/trial × 11.5K ≈ 10-15 hour background job
  - Colab GPU: ~5-15 min on T4 (see notebooks/biobert_embed_colab.ipynb)

Output:
  api/data/training/embeddings.npy     (shape: [N, 768], dtype float32)
  api/data/training/embeddings_nctid.txt  (one NCT ID per line, ordered same as rows)

Two files (rather than one parquet with embedding + nctid columns) because:
  - npy + plain text are deployment-trivial — no pyarrow dependency at
    training-load time, and the embeddings.npy file is what ships via Git
    LFS into the runtime container for the nearest-neighbor inference path.
  - The text file is the row-index → nctid map for joining back to the
    main parquet during training.

Design choices documented in the module:
  - Mean-pool over token embeddings (NOT CLS token). BioBERT inherits BERT's
    weak CLS for non-NSP tasks; mean-pool is the practitioner standard for
    BERT-family models used as feature extractors.
  - Wordpiece-truncate from the BACK (max_length=512). Inclusion criteria
    + the first half of exclusion typically carries the diligence-relevant
    signal. Trials with very long criteria lose the tail.
  - Batched inference (default batch_size=16 for CPU, 64 for GPU).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)

API_DIR = Path(__file__).resolve().parent.parent
TRAINING_DIR = API_DIR / "data" / "training"
PARQUET_IN = TRAINING_DIR / "training_dataset.parquet"
EMBEDDINGS_OUT = TRAINING_DIR / "embeddings.npy"
NCTID_INDEX_OUT = TRAINING_DIR / "embeddings_nctid.txt"

BIOBERT_MODEL_ID = "dmis-lab/biobert-v1.1"
MAX_LENGTH = 512  # BioBERT's max wordpiece-token sequence


def _resolve_device(preferred: str | None) -> str:
    """Pick the best available device. 'auto' → cuda if available else cpu."""
    import torch

    if preferred and preferred != "auto":
        return preferred
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():  # Apple Silicon
        return "mps"
    return "cpu"


def _mean_pool(last_hidden_state, attention_mask):
    """Mean over token embeddings, masking padding tokens out of the sum.

    last_hidden_state: [B, T, H]
    attention_mask:    [B, T]  (1 for real tokens, 0 for padding)
    returns:           [B, H]  (mean over non-padding tokens)
    """
    mask = attention_mask.unsqueeze(-1).float()
    summed = (last_hidden_state * mask).sum(dim=1)
    counts = mask.sum(dim=1).clamp(min=1e-9)
    return summed / counts


def embed_criteria(
    *,
    parquet_path: Path = PARQUET_IN,
    output_path: Path = EMBEDDINGS_OUT,
    nctid_index_path: Path = NCTID_INDEX_OUT,
    batch_size: int = 16,
    device: str | None = None,
    limit: int | None = None,
) -> dict:
    """Main entrypoint. Returns a stats dict for logging."""
    # Deferred imports so the module can be type-checked without these deps
    import pandas as pd
    import torch
    from transformers import AutoModel, AutoTokenizer

    if not parquet_path.exists():
        raise FileNotFoundError(
            f"Training parquet not found at {parquet_path}. "
            f"Run `python -m data_pipeline.build_training_dataset` first."
        )

    df = pd.read_parquet(parquet_path)
    if limit is not None:
        df = df.head(limit)
    log.info("loaded %d trials from %s", len(df), parquet_path)

    device = _resolve_device(device)
    log.info("using device: %s", device)

    log.info("loading BioBERT model + tokenizer from %s", BIOBERT_MODEL_ID)
    tokenizer = AutoTokenizer.from_pretrained(BIOBERT_MODEL_ID)
    model = AutoModel.from_pretrained(BIOBERT_MODEL_ID).to(device).eval()

    embeddings = np.zeros((len(df), 768), dtype=np.float32)
    nctids: list[str] = []

    criteria_texts = df["criteria_text"].tolist()
    df_nctids = df["nctid"].tolist()
    n = len(criteria_texts)

    with torch.no_grad():
        for start in range(0, n, batch_size):
            end = min(start + batch_size, n)
            batch_texts = criteria_texts[start:end]
            batch_nctids = df_nctids[start:end]

            enc = tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=MAX_LENGTH,
                return_tensors="pt",
            ).to(device)

            out = model(**enc)
            pooled = _mean_pool(out.last_hidden_state, enc["attention_mask"])
            embeddings[start:end] = pooled.cpu().numpy().astype(np.float32)
            nctids.extend(batch_nctids)

            if (start // batch_size) % 25 == 0:
                log.info(
                    "  %d/%d trials embedded (%.1f%%)",
                    end, n, end / n * 100.0,
                )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, embeddings)
    nctid_index_path.write_text("\n".join(nctids) + "\n")

    return {
        "n_trials": int(n),
        "embedding_dim": int(embeddings.shape[1]),
        "device": device,
        "output_path": str(output_path),
        "output_size_mb": round(output_path.stat().st_size / 1024 / 1024, 2),
        "nctid_index_path": str(nctid_index_path),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Batch size for inference. Default 16 (CPU-friendly). Use 64+ on GPU.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="auto|cpu|cuda|mps. Default: auto (cuda > mps > cpu).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap rows for a smoke test (e.g. 50). Default: full parquet.",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    stats = embed_criteria(
        batch_size=args.batch_size,
        device=args.device,
        limit=args.limit,
    )

    print("\nEMBEDDING COMPLETE")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
