#!/usr/bin/env bash
# Self-tests for stage-hunks.sh, run against throwaway git repositories and a
# `chezmoi` shim; the real chezmoi source tree is never touched.
# Run: ./stage-hunks.test.sh
# shellcheck disable=SC2312 # a substitution that fails yields a wrong value, which is a FAIL line, so nothing is masked
set -uo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
PENDING="$DIR/pending.sh"
SCRIPT="$DIR/stage-hunks.sh"
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

# new_case: fresh repo whose f.txt has three hunks pending (lines 2, 15, 28);
# sets CASE_REPO.
new_case() {
  CASE_REPO=$(mktemp -d -p "$TMP")
  export CASE_REPO
  git init -q "$CASE_REPO"
  seq 1 30 >"$CASE_REPO/f.txt"
  git -C "$CASE_REPO" add f.txt
  git -C "$CASE_REPO" commit -q -m 'Base'
  seq 1 30 | sed -e 's/^2$/two/' -e 's/^15$/fifteen/' -e 's/^28$/twenty-eight/' >"$CASE_REPO/f.txt"
}

# run_stage <args...>: run the script; sets RC and ERR (stderr).
run_stage() {
  ERR=$("$SCRIPT" "$@" 2>&1 >/dev/null)
  RC=$?
}

pending() { "$PENDING" >/dev/null; }
commit_staged() { git -C "$CASE_REPO" commit -q -m "$1"; }
# The words the index changes in f.txt over HEAD.
staged_words() { git -C "$CASE_REPO" diff --cached -U0 | sed -n 's/^+\([a-z-]*\)$/\1/p' | paste -sd, -; }
err_has() { if [[ $ERR == *"$1"* ]]; then echo true; else echo false; fi; }

# 1. Before any row commits, hunks number as pending.sh printed them.
new_case
pending
check "pending.sh labels three hunks" "3" "$("$PENDING" | grep -c '^\[hunk ')"
run_stage f.txt 2
check "first row: exit 0" "0" "$RC"
check "first row: only hunk 2 staged" "fifteen" "$(staged_words)"

# 2. After an earlier row commits, the base numbering still holds.
new_case
pending
run_stage f.txt 1; commit_staged 'Row 1'
run_stage f.txt 3
check "later row: exit 0" "0" "$RC"
check "later row: hunk 3 by its pending.sh number" "twenty-eight" "$(staged_words)"
commit_staged 'Row 2'
check "later row: hunk 2 left unstaged" "fifteen" "$(git -C "$CASE_REPO" diff -U0 | sed -n 's/^+\([a-z-]*\)$/\1/p')"

# 3. Two hunks in one call, after an earlier row.
new_case
pending
run_stage f.txt 2; commit_staged 'Row 1'
run_stage f.txt 1 3
check "two hunks after a row: both staged" "two,twenty-eight" "$(staged_words)"

# 4. A hunk already committed is refused loudly, not restaged.
new_case
pending
run_stage f.txt 1; commit_staged 'Row 1'
run_stage f.txt 1
check "committed hunk: refused" "true" "$([[ $RC -ne 0 ]] && echo true || echo false)"
check "committed hunk: nothing staged" "" "$(staged_words)"

# 5. No base recorded: refused with a pointer to pending.sh.
new_case
run_stage f.txt 1
check "no base: exit 2" "2" "$RC"
check "no base: names pending.sh" "true" "$(err_has 'run pending.sh first')"

# 6. A base HEAD no longer descends from (an amended HEAD): refused.
new_case
pending
git -C "$CASE_REPO" commit -q --amend -m 'Base, amended'
run_stage f.txt 1
check "amended base: exit 2" "2" "$RC"
check "amended base: says why" "true" "$(err_has 'not an ancestor of HEAD')"

# 7. Out-of-range and malformed numbers: refused, nothing staged.
new_case
pending
for bad in 4 0 x; do
  run_stage f.txt "$bad"
  check "hunk '$bad': refused, nothing staged" "2|" "$RC|$(staged_words)"
done

# 8. Too few arguments: usage and exit 2.
run_stage f.txt
check "no hunk number: exit 2" "2" "$RC"
check "no hunk number: usage on stderr" "usage: stage-hunks.sh <source-path> <hunk-number>..." "$ERR"

echo
echo "Pass: $PASS  Fail: $FAIL"
[[ $FAIL -eq 0 ]] || exit 1
