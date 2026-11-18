#!/usr/bin/env bash
# Self-tests for pending.sh, run against throwaway git repositories and a
# `chezmoi` shim; the real chezmoi source tree is never touched.
# Run: ./pending.test.sh
# shellcheck disable=SC2312 # a substitution that fails yields a wrong value, which is a FAIL line, so nothing is masked
set -uo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$DIR/pending.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0
FAIL=0

# Unsigned commits, no host configuration leaking in.
cat >"$TMP/gitconfig" <<'CFG'
[user]
	name = Test
	email = test@example.invalid
[init]
	defaultBranch = main
CFG
export GIT_CONFIG_GLOBAL="$TMP/gitconfig" GIT_CONFIG_SYSTEM=/dev/null

# chezmoi shim: `source-path` prints the case repo.
mkdir "$TMP/bin"
cat >"$TMP/bin/chezmoi" <<'SHIM'
#!/usr/bin/env bash
case $1 in
    source-path) printf '%s\n' "$CASE_REPO" ;;
    *) exit 64 ;;
esac
SHIM
chmod +x "$TMP/bin/chezmoi"
export PATH="$TMP/bin:$PATH"

check() {
  local name="$1" expected="$2" actual="$3"
  if [[ "$actual" == "$expected" ]]; then
    echo "OK   $name"; PASS=$((PASS+1))
  else
    echo "FAIL $name"; FAIL=$((FAIL+1))
    printf '  expected: %s\n  actual:   %s\n' "$expected" "$actual"
  fi
}

# new_case: fresh repo with one commit; sets CASE_REPO.
new_case() {
  CASE_REPO=$(mktemp -d -p "$TMP")
  export CASE_REPO
  git init -q "$CASE_REPO"
  echo base >"$CASE_REPO/base.txt"
  git -C "$CASE_REPO" add base.txt
  git -C "$CASE_REPO" commit -q -m 'Base'
}

# section <output> <file>: the lines under <file>'s untracked header.
section() {
  awk -v head="=== untracked: $2 ===" '
    $0 == head { on = 1; next }
    /^=== untracked: / { on = 0 }
    on && NF
  ' <<<"$1"
}

new_case
printf 'one\ntwo\n' >"$CASE_REPO/notes.txt"
out=$("$SCRIPT")
check "a text file prints in full" $'one\ntwo' "$(section "$out" notes.txt)"

new_case
printf 'GIF89a\0\0\1\2binary' >"$CASE_REPO/img.bin"
out=$("$SCRIPT")
check "a binary file prints its size" "(binary, 16 bytes)" "$(section "$out" img.bin)"
check "a binary file's bytes stay out" "" "$(grep -a 'GIF89a' <<<"$out")"

new_case
: >"$CASE_REPO/empty.txt"
out=$("$SCRIPT")
check "an empty file prints nothing" "" "$(section "$out" empty.txt)"
check "an empty file still gets its header" "1" "$(grep -c 'untracked: empty.txt' <<<"$out")"

echo
echo "$PASS passed, $FAIL failed"
(( FAIL == 0 ))
