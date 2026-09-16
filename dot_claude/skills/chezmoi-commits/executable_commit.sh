#!/usr/bin/env bash
# Commit one row of the proposed table in the chezmoi source tree: stage
# the given source paths (none for a row whose hunks `git apply --cached`
# already staged) and commit them under the subject.
set -euo pipefail

if (( $# < 1 )); then
    echo 'usage: commit.sh <subject> [source-path...]' >&2
    exit 2
fi
subject=$1
shift

cd "$(chezmoi source-path)"
if (( $# > 0 )); then
    git add -- "$@"
fi
git commit -m "$subject"
