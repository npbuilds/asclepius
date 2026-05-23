#!/usr/bin/env bash
# Fetch the HINT clinical-trial-outcome-prediction corpus to api/data/hint/.
# This is the v1.5.2 training data — labeled trial outcomes (success / failure)
# across Phase I/II/III with eligibility criteria text suitable for BioBERT
# embedding.
#
# The corpus is ~11K unique trials × ~50KB criteria text = ~500MB raw. It's
# gitignored (see .gitignore) — committed to disk only on the training
# machine. The trained model artifact + embeddings file land in the repo via
# Git LFS as separate artifacts.
#
# Source: futianfan/clinical-trial-outcome-prediction
# Paper:  HINT (Fu et al., 2022). MIT license per the upstream repo.

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
API_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
HINT_DIR="$API_DIR/data/hint"

if [ -d "$HINT_DIR/data" ] && [ -f "$HINT_DIR/data/raw_data.csv" ]; then
    echo "HINT corpus already present at $HINT_DIR. Skipping clone."
    echo "  (delete the directory if you want to re-fetch)"
    exit 0
fi

mkdir -p "$(dirname "$HINT_DIR")"
echo "cloning HINT corpus to $HINT_DIR…"
git clone --depth 1 \
    https://github.com/futianfan/clinical-trial-outcome-prediction.git \
    "$HINT_DIR"

# Drop the .git history — we just want the data files
rm -rf "$HINT_DIR/.git"

echo
echo "downloaded:"
ls -lh "$HINT_DIR/data/"*.csv | head -10
echo "done."
