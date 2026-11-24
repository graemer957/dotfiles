#!/usr/bin/env bash
# Print everything pending in the chezmoi source tree: status, the diff
# against HEAD (staged and unstaged) with each file's hunks numbered as
# `git diff HEAD -- <file>` counts them, and each untracked file in full,
# or its size when it is binary.
# Source paths given as arguments narrow the listing to those files.
# Records HEAD as the run's base, so `stage-hunks.sh` keeps these numbers
# after earlier rows commit.
set -euo pipefail

src=$(chezmoi source-path)
cd "$src"

# `commit.sh` commits the whole index, so a file staged before the run
# would land in whichever row commits first.
staged=$(git diff --cached --name-only)
if [[ -n $staged ]]; then
    printf "refusing: already staged, so the first row would commit it:\n%s\nthe staging may be another run's rows awaiting commit, so hand this back to the user\n" \
        "$staged" >&2
    exit 1
fi

# A named path outside the source tree, a directory or a path that names
# nothing there fails loudly, since an empty listing reads as nothing pending.
root=$(pwd -P)
for path in "$@"; do
    full=$(realpath -m -- "$path")
    if [[ $full != "$root"/* || -d $full ]]; then
        printf 'not a file in the source tree: %s\n' "$path" >&2
        exit 2
    fi
    tracked=$(git ls-files -- "$full")
    if [[ ! -e $full && -z $tracked ]]; then
        printf 'not a file in the source tree: %s\n' "$path" >&2
        exit 2
    fi
    pending=$(git status --porcelain -- "$full")
    if [[ -z $pending ]]; then
        printf 'nothing pending: %s\n' "$path" >&2
    fi
done

git rev-parse HEAD >"$(git rev-parse --git-path chezmoi-commits-base)"

git status --short -- "$@"
echo
git diff HEAD -- "$@" | awk '/^diff --git/ { n = 0 } /^@@/ { n++; printf "[hunk %d] ", n } { print }'

git ls-files --others --exclude-standard -- "$@" | while IFS= read -r file; do
    printf '\n=== untracked: %s ===\n' "$file"
    if [[ -s $file ]] && ! grep -qI '' -- "$file"; then
        size=$(stat -c %s -- "$file")
        printf '(binary, %s bytes)\n' "$size"
    else
        cat -- "$file"
    fi
done
