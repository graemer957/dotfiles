#!/usr/bin/env bash
# Print everything pending in the chezmoi source tree: status, the diff
# against HEAD (staged and unstaged) with each file's hunks numbered as
# `git diff HEAD -- <file>` counts them, and each untracked file in full.
# Records HEAD as the run's base, so `stage-hunks.sh` keeps these numbers
# after earlier rows commit.
set -euo pipefail

src=$(chezmoi source-path)
cd "$src"
git rev-parse HEAD >"$(git rev-parse --git-path chezmoi-commits-base)"

git status --short
echo
git diff HEAD | awk '/^diff --git/ { n = 0 } /^@@/ { n++; printf "[hunk %d] ", n } { print }'

git ls-files --others --exclude-standard | while IFS= read -r file; do
    printf '\n=== untracked: %s ===\n' "$file"
    cat -- "$file"
done
