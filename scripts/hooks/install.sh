#!/usr/bin/env bash
# Install the project's git hooks. Re-run after a fresh clone (git doesn't
# version .git/hooks/, so each working copy needs to wire its own).
#
# Why symlink instead of copy: an edit to scripts/hooks/pre-commit then
# propagates to every active checkout without re-running this installer.
# With a copy, every developer would silently drift onto an old hook.

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

hook_src="scripts/hooks/pre-commit"
hook_dst=".git/hooks/pre-commit"

if [[ ! -f "$hook_src" ]]; then
  echo "install-hooks: ERROR — $hook_src not found. Are you in the repo?" >&2
  exit 1
fi

chmod +x "$hook_src"

# Use relative path from .git/hooks/ so the symlink survives if the repo
# moves on disk. .git/hooks/pre-commit → ../../scripts/hooks/pre-commit
ln -sf "../../$hook_src" "$hook_dst"

echo "install-hooks: installed $hook_dst -> $hook_src"
echo "install-hooks: test with: \`touch methodology/*.md && git add methodology && git commit -m test\`"
echo "install-hooks: bypass once with: \`git commit --no-verify\`"
