# Asclepius API — production container for Fly.io.
#
# Python 3.11 slim base. v1.5.2 Day 4 adds the heavy ML inference stack:
# torch (CPU-only wheel), transformers, and lightgbm. The container also
# pre-downloads PubMedBERT-base (~440 MB) at build time so the first
# request after deploy doesn't pay for the model fetch — only the
# in-memory load (~5-10 sec on shared-cpu-2x).
#
# Container size: ~1.4 GB (was ~150 MB pre-v1.5.2). The Fly machine size
# in fly.toml is shared-cpu-2x (1 GB RAM) to fit PubMedBERT + FastAPI
# headroom.

FROM python:3.11-slim

# Set unbuffered stdout so log lines flush immediately on uvicorn output
ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    # HuggingFace cache lives here in the image so the pre-download below
    # sticks across container restarts (Fly machines are immutable; this
    # is more about predictability than persistence).
    HF_HOME=/app/.hf_cache \
    TRANSFORMERS_OFFLINE=0 \
    # PyTorch + LightGBM both link against OpenMP runtimes. When loaded into
    # the same process they can segfault silently (observed on macOS Day 4
    # cache-gen; defensive on Linux because the same risk exists). Pinning
    # OMP_NUM_THREADS=1 avoids the conflict by serializing OpenMP work to a
    # single thread, and KMP_DUPLICATE_LIB_OK=TRUE explicitly permits
    # multiple OMP runtimes to coexist if the previous setting isn't enough.
    OMP_NUM_THREADS=1 \
    KMP_DUPLICATE_LIB_OK=TRUE

WORKDIR /app

# v1.5.2.3: install libgomp (OpenMP runtime). LightGBM's manylinux wheel
# dlopens `libgomp.so.1` at first `import lightgbm`; python:3.11-slim
# strips system libs by default, so without this the engine crashes at
# load with `libgomp.so.1: cannot open shared object file`. Cost: ~150 KB.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# v1.5.2.3: install the CPU-only torch wheel explicitly to avoid pulling the
# default wheel (which includes NVIDIA CUDA runtime libraries ~2 GB).
# This must happen before `pip install .` reads pyproject.toml, otherwise
# pip resolves the GPU wheel.
#
# Torch must be >= 2.6 because transformers >= 4.46 enforces CVE-2025-32434
# (`torch.load` vulnerability — `check_torch_load_is_safe()` raises on any
# .bin checkpoint with torch < 2.6, even with `weights_only=True`).
# PubMedBERT's HF repo only ships `pytorch_model.bin` (no safetensors
# variant), so the CVE check trips on every cold load unless torch is
# new enough.
RUN pip install --no-cache-dir torch==2.6.0+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Install project deps (pyproject.toml lists transformers + lightgbm in
# the base [project.dependencies]; the CPU torch above satisfies the
# `torch>=2.2` constraint without re-resolving).
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

# Pre-download PubMedBERT into the image. Saves the user's first ML PoS
# Prior request from waiting on a 440 MB network fetch. The model files
# land in $HF_HOME and are loaded by transformers' `from_pretrained` at
# inference time directly from disk.
RUN python -c "from transformers import AutoModel, AutoTokenizer; \
    mid = 'microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext'; \
    AutoTokenizer.from_pretrained(mid); \
    AutoModel.from_pretrained(mid); \
    print('PubMedBERT pre-downloaded.')"

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
