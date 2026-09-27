#!/usr/bin/env bash
# Commit one row of the proposed table in the chezmoi source tree: stage
# the given source paths (none for a row whose hunks `stage-hunks.sh`
# already staged), parse-check every staged file as the commit will hold
# it, and commit them under the subject.
set -euo pipefail

# parses <source-path> <file>: 0 when <file> parses as <source-path>'s type,
# or the type has no checker here.
parses() {
    case $1 in
        *.tmpl)      return 0 ;;   # parses only once chezmoi renders it
        *.fish)      fish -n "$2" ;;
        *.sh|*.bash) bash -n "$2" ;;
        *.py)        python3 -c 'import ast, sys; ast.parse(open(sys.argv[1]).read())' "$2" ;;
        *.json)      jq empty "$2" ;;
        *.toml)      python3 -c 'import sys, tomllib; tomllib.load(open(sys.argv[1], "rb"))' "$2" ;;
        *)           local shebang
                     shebang=$(head -n1 "$2")
                     if [[ $shebang == '#!'*bash* ]]; then bash -n "$2"; fi ;;
    esac
}

if (( $# < 1 )); then
    echo 'usage: commit.sh <subject> [source-path...]' >&2
    exit 2
fi
subject=$1
shift

src=$(chezmoi source-path)
cd "$src"
if (( $# > 0 )); then
    git add -- "$@"
fi

staged=$(mktemp)
paths=$(mktemp)
trap 'rm -f "$staged" "$paths"' EXIT
git diff --cached --name-only --diff-filter=d -z >"$paths"
broken=()
while IFS= read -r -d '' path; do
    git show ":$path" >"$staged"
    # shellcheck disable=SC2310  # a parse failure is collected, not fatal
    parses "$path" "$staged" || broken+=("$path")
done <"$paths"
if (( ${#broken[@]} )); then
    printf 'commit.sh: staged version does not parse: %s\n' "${broken[@]}" >&2
    echo 'commit.sh: nothing committed; the row is still staged' >&2
    exit 1
fi

git commit -m "$subject"
