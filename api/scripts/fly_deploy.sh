#!/usr/bin/env bash
# Deploy the Asclepius API to Fly.io, staging the methodology/ folder into the
# Docker build context first.
#
# The methodology files live at the repo root in methodology/ but the
# fly.toml build context is api/ — so methodology files would be invisible
# to Docker COPY. This script copies them into api/app/methodology/ (which
# is gitignored), then runs flyctl deploy.
#
# Run from anywhere; uses the script's location to resolve paths.

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
API_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
REPO_DIR="$( cd "$API_DIR/.." && pwd )"

METHODOLOGY_SRC="$REPO_DIR/methodology"
METHODOLOGY_STAGE="$API_DIR/app/methodology"

if [ ! -d "$METHODOLOGY_SRC" ]; then
    echo "error: methodology source not found at $METHODOLOGY_SRC" >&2
    exit 1
fi

echo "staging methodology/ → api/app/methodology/ for Docker build context…"
rm -rf "$METHODOLOGY_STAGE"
mkdir -p "$METHODOLOGY_STAGE"
cp "$METHODOLOGY_SRC"/*.md "$METHODOLOGY_STAGE/"
echo "  $(ls "$METHODOLOGY_STAGE" | wc -l | tr -d ' ') files staged"

cd "$API_DIR"
echo "running flyctl deploy from $API_DIR…"
flyctl deploy "$@"

echo "cleaning up staging dir…"
rm -rf "$METHODOLOGY_STAGE"
echo "done."
