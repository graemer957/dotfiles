#!/usr/bin/env bash
# Stage the numbered hunks of one file's diff in the chezmoi source tree, for
# a table row that takes part of a file. Hunks count from 1 in `git diff
# <base> -- <file>` order, where <base> is the HEAD `pending.sh` recorded, so
# the numbers it printed hold after earlier rows commit.
set -euo pipefail

if (( $# < 2 )); then
    echo 'usage: stage-hunks.sh <source-path> <hunk-number>...' >&2
    exit 2
fi
file=$1
shift

src=$(chezmoi source-path)
cd "$src"
base_file=$(git rev-parse --git-path chezmoi-commits-base)
if [[ ! -s $base_file ]]; then
    echo 'stage-hunks.sh: no base recorded; run pending.sh first' >&2
    exit 2
fi
base=$(<"$base_file")
if ! git merge-base --is-ancestor "$base" HEAD; then
    echo "stage-hunks.sh: base $base is not an ancestor of HEAD; run pending.sh again" >&2
    exit 2
fi
diff=$(mktemp)
trap 'rm -f "$diff"' EXIT
git diff "$base" -- "$file" >"$diff"
total=$(grep -c '^@@' "$diff" || true)
for n in "$@"; do
    if ! [[ $n =~ ^[1-9][0-9]*$ && $n -le $total ]]; then
        echo "stage-hunks.sh: $file has $total hunks; no hunk $n" >&2
        exit 2
    fi
done
awk -v want=" $* " '
    n == 0 && !/^@@/ { print; next }
    /^@@/ { n++; keep = index(want, " " n " ") > 0 }
    keep
' "$diff" | git apply --cached
