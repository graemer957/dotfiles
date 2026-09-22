#!/usr/bin/env bash
# Stage the numbered hunks of one file's diff against HEAD in the chezmoi
# source tree, for a table row that takes part of a file. Hunks count from 1
# in `git diff HEAD -- <file>` order; a hunk that serves two rows is still
# split by hand.
set -euo pipefail

if (( $# < 2 )); then
    echo 'usage: stage-hunks.sh <source-path> <hunk-number>...' >&2
    exit 2
fi
file=$1
shift

src=$(chezmoi source-path)
cd "$src"
diff=$(mktemp)
trap 'rm -f "$diff"' EXIT
git diff HEAD -- "$file" >"$diff"
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
