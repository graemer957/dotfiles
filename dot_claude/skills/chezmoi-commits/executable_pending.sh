#!/usr/bin/env bash
# Print everything pending in the chezmoi source tree: status, the diff
# against HEAD (staged and unstaged), and each untracked file in full.
set -euo pipefail

cd "$(chezmoi source-path)"

git status --short
echo
git diff HEAD

git ls-files --others --exclude-standard | while IFS= read -r file; do
    printf '\n=== untracked: %s ===\n' "$file"
    cat -- "$file"
done
