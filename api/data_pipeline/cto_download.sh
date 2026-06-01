#!/usr/bin/env bash
# Download the CT Open (CTO) benchmark CSVs from HuggingFace.
#
# Source: Gao et al. 2024 / Nature Health 2026
#   https://huggingface.co/datasets/chufangao/CTO
#   https://arxiv.org/abs/2406.10292
#
# Total download size: ~19 MB across 4 CSV files. The dataset is not
# vendored in the repo (api/data/cto/ is in .gitignore); run this once
# after clone to populate the directory.
#
# Usage:
#   bash api/data_pipeline/cto_download.sh

set -euo pipefail

# Locate the repo root regardless of where this script is invoked
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CTO_DIR="$REPO_ROOT/api/data/cto"

mkdir -p "$CTO_DIR"
cd "$CTO_DIR"

# Files to fetch + their HuggingFace URLs.
declare -a FILES=(
  "human_labels_2020_2024.csv|https://huggingface.co/datasets/chufangao/CTO/resolve/main/human_labels_2020_2024/human_labels_2020_2024.csv"
  "phase1_CTO_rf.csv|https://huggingface.co/datasets/chufangao/CTO/raw/main/phase1_CTO_rf.csv"
  "phase2_CTO_rf.csv|https://huggingface.co/datasets/chufangao/CTO/raw/main/phase2_CTO_rf.csv"
  "phase3_CTO_rf.csv|https://huggingface.co/datasets/chufangao/CTO/raw/main/phase3_CTO_rf.csv"
)

echo "Downloading CTO benchmark data into $CTO_DIR ..."
for entry in "${FILES[@]}"; do
  filename="${entry%%|*}"
  url="${entry##*|}"
  if [ -f "$filename" ]; then
    size_kb=$(du -k "$filename" | awk '{print $1}')
    if [ "$size_kb" -gt 100 ]; then
      echo "  $filename (already present, ${size_kb} KB) — skipping"
      continue
    fi
  fi
  echo "  fetching $filename ..."
  curl -sSL "$url" -o "$filename"
  size_kb=$(du -k "$filename" | awk '{print $1}')
  echo "    done — ${size_kb} KB"
done

echo ""
echo "CTO benchmark data ready. Run the pipeline with:"
echo "  cd api && python data_pipeline/cto_acquire.py"
