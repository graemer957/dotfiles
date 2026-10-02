#!/usr/bin/env bash
# Commit one row of the proposed table in the chezmoi source tree: stage
# the given source paths (none for a row whose hunks `stage-hunks.sh`
# already staged), parse-check every staged file as the commit will hold
# it, and commit them under the subject.
set -euo pipefail

# parses <source-path> <file>: 0 when <file> parses as <source-path>'s type,
# or the type has no checker here. A template is checked as the type it
# renders to, and rendered only when that type has a checker, so a template
# feeding an unchecked type never triggers its 1Password lookups.
parses() {
    local file=$2 render=0
    if [[ $1 == *.tmpl ]]; then render=1; fi
    case ${1%.tmpl} in
        *.fish)      check fish -n ;;
        *.sh|*.bash) check bash -n ;;
        *.py)        check python3 -c 'import ast, sys; ast.parse(open(sys.argv[1]).read())' ;;
        *.json)      check jq empty ;;
        *.toml)      check python3 -c 'import sys, tomllib; tomllib.load(open(sys.argv[1], "rb"))' ;;
        *tmux.conf)  check tmux -L commit_sh -f /dev/null start-server \; source-file -n ;;
        *)           local shebang
                     shebang=$(head -n1 "$file")
                     if [[ $shebang == '#!'*bash* ]]; then check bash -n; fi ;;
    esac
}

# check <command...>: run <command...> on the file `parses` is checking,
# rendered first when it is a template.
check() {
    if (( render )); then
        chezmoi execute-template <"$file" >"$rendered" || return
        "$@" "$rendered"
    else
        "$@" "$file"
    fi
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
rendered=$(mktemp)
trap 'rm -f "$staged" "$paths" "$rendered"' EXIT
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
