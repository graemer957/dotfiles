#!/usr/bin/env bash
# Self-tests for commit.sh, run against throwaway git repositories and a
# `chezmoi` shim; the real chezmoi source tree is never touched.
# Run: ./commit.test.sh
# shellcheck disable=SC2312 # a substitution that fails yields a wrong value, which is a FAIL line, so nothing is masked
# shellcheck disable=SC2016 # backticks in subjects are literal, as in a real call
set -uo pipefail

SCRIPT="$(cd "$(dirname "$0")" && pwd)/commit.sh"
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

# chezmoi shim: `source-path` prints the case repo; `execute-template` logs
# the call and fails when the input contains RENDER_FAILS, else passes through.
mkdir "$TMP/bin"
cat >"$TMP/bin/chezmoi" <<'SHIM'
#!/usr/bin/env bash
case $1 in
    source-path) printf '%s\n' "$CASE_REPO" ;;
    execute-template)
        echo called >>"$RENDER_LOG"
        input=$(cat)
        if [[ $input == *RENDER_FAILS* ]]; then exit 1; fi
        printf '%s\n' "$input" ;;
    *) exit 64 ;;
esac
SHIM
chmod +x "$TMP/bin/chezmoi"
export PATH="$TMP/bin:$PATH"
export RENDER_LOG="$TMP/render.log"

check() {
  local name="$1" expected="$2" actual="$3"
  if [[ "$actual" == "$expected" ]]; then
    echo "OK   $name"; PASS=$((PASS+1))
  else
    echo "FAIL $name"; FAIL=$((FAIL+1))
    printf '  expected: %s\n  actual:   %s\n' "$expected" "$actual"
  fi
}

# new_case: fresh repo with one base commit; sets CASE_REPO.
new_case() {
  CASE_REPO=$(mktemp -d -p "$TMP")
  export CASE_REPO
  git init -q "$CASE_REPO"
  echo base >"$CASE_REPO/base.txt"
  git -C "$CASE_REPO" add base.txt
  git -C "$CASE_REPO" commit -q -m 'Base'
}

# run_commit <args...>: run the script; sets RC and ERR (stderr).
run_commit() {
  ERR=$("$SCRIPT" "$@" 2>&1 >/dev/null)
  RC=$?
}

head_subject() { git -C "$CASE_REPO" log -1 --format=%s; }
commit_count() { git -C "$CASE_REPO" rev-list --count HEAD; }
head_files() { git -C "$CASE_REPO" show --name-only --format= HEAD | paste -sd, -; }
staged() { git -C "$CASE_REPO" diff --cached --name-only | paste -sd, -; }
err_has() { if [[ $ERR == *"$1"* ]]; then echo true; else echo false; fi; }

# 1. Named paths are staged and committed under the subject; other files stay out.
new_case
echo ok >"$CASE_REPO/a.txt"; echo other >"$CASE_REPO/b.txt"
run_commit 'Add `a`' a.txt
check "commit: exit 0" "0" "$RC"
check "commit: subject verbatim, backticks kept" 'Add `a`' "$(head_subject)"
check "commit: only the named path" "a.txt" "$(head_files)"
check "commit: unnamed untracked file left alone" "?? b.txt" "$(git -C "$CASE_REPO" status --short)"

# 2. No paths: whatever is already staged is committed.
new_case
echo ok >"$CASE_REPO/a.txt"; git -C "$CASE_REPO" add a.txt
run_commit 'Stage only'
check "no paths: commits pre-staged files" "Stage only|a.txt" "$(head_subject)|$(head_files)"

# 3. No arguments: usage and exit 2.
new_case
run_commit
check "no args: exit 2" "2" "$RC"
check "no args: usage on stderr" "usage: commit.sh <subject> [source-path...]" "$ERR"

# 4. Empty staging set: fails, no commit.
new_case
run_commit 'Nothing to commit'
check "empty staging: non-zero exit" "true" "$([[ $RC -ne 0 ]] && echo true || echo false)"
check "empty staging: no commit added" "1" "$(commit_count)"

# 5. Broken Python refused before any commit; row stays staged.
new_case
printf 'def broken(:\n' >"$CASE_REPO/x.py"
run_commit 'Add `x`' x.py
check "bad python: exit 1" "1" "$RC"
check "bad python: nothing committed" "1" "$(commit_count)"
check "bad python: row stays staged" "x.py" "$(staged)"
check "bad python: names the file" "true" "$(err_has 'does not parse: x.py')"

# 6. Valid Python, shell, JSON and TOML all commit.
new_case
printf 'x = 1\n' >"$CASE_REPO/ok.py"
printf '#!/usr/bin/env bash\necho hi\n' >"$CASE_REPO/ok.sh"
printf '{"a": 1}\n' >"$CASE_REPO/ok.json"
printf 'a = 1\n' >"$CASE_REPO/ok.toml"
run_commit 'Add valid files' ok.py ok.sh ok.json ok.toml
check "valid py/sh/json/toml: committed" "0|Add valid files" "$RC|$(head_subject)"

# 7. Each checked type refuses a broken file.
for bad in 'bad.sh:if then' 'bad.bash:fi' 'bad.json:{"a":' 'bad.toml:a = '; do
  new_case
  printf '%s\n' "${bad#*:}" >"$CASE_REPO/${bad%%:*}"
  run_commit 'Add bad' "${bad%%:*}"
  check "bad ${bad%%:*}: refused, nothing committed" "1|1" "$RC|$(commit_count)"
done

# 8. One broken file among good ones blocks the whole row.
new_case
printf 'x = 1\n' >"$CASE_REPO/good.py"; printf '{\n' >"$CASE_REPO/bad.json"
run_commit 'Mixed row' good.py bad.json
check "mixed row: refused, both stay staged" "1|1|bad.json,good.py" "$RC|$(commit_count)|$(staged)"

# 9. The staged blob is checked, not the working tree: a split file's early row.
new_case
printf 'x = 1\n' >"$CASE_REPO/s.py"; git -C "$CASE_REPO" add s.py
printf 'def broken(:\n' >"$CASE_REPO/s.py"
run_commit 'Staged part is valid'
check "valid staged blob commits despite broken worktree" "0|Staged part is valid" "$RC|$(head_subject)"
new_case
printf 'def broken(:\n' >"$CASE_REPO/s.py"; git -C "$CASE_REPO" add s.py
printf 'x = 1\n' >"$CASE_REPO/s.py"
run_commit 'Staged part is broken'
check "broken staged blob refused despite valid worktree" "1|1" "$RC|$(commit_count)"

# 10. Extensionless files: a bash shebang is checked, other shebangs are not.
new_case
printf '#!/usr/bin/env bash\nif then\n' >"$CASE_REPO/tool"
run_commit 'Add tool' tool
check "bash shebang, no extension: refused" "1|1" "$RC|$(commit_count)"
new_case
printf '#!/usr/bin/env python3\nif then\n' >"$CASE_REPO/tool"
run_commit 'Add tool' tool
check "non-bash shebang, no extension: not checked" "0|Add tool" "$RC|$(head_subject)"

# 11. Staged deletions are not parse-checked and commit.
new_case
printf 'x = 1\n' >"$CASE_REPO/gone.py"
git -C "$CASE_REPO" add gone.py; git -C "$CASE_REPO" commit -q -m 'Add gone'
git -C "$CASE_REPO" rm -q gone.py
run_commit 'Drop `gone`'
check "deletion commits" "0|Drop \`gone\`" "$RC|$(head_subject)"

# 12. Templates are rendered, then checked as the type they render to.
new_case
printf '{"a": 1}\n' >"$CASE_REPO/dot_c.json.tmpl"
: >"$RENDER_LOG"
run_commit 'Add template' dot_c.json.tmpl
check "template rendering to valid json: committed" "0|Add template" "$RC|$(head_subject)"
check "template rendering to valid json: rendered once" "called" "$(cat "$RENDER_LOG")"
new_case
printf '{"a": RENDER_FAILS}\n' >"$CASE_REPO/dot_c.json.tmpl"
run_commit 'Add template' dot_c.json.tmpl
check "template that fails to render: refused" "1|1" "$RC|$(commit_count)"
new_case
printf '{"a":\n' >"$CASE_REPO/dot_c.json.tmpl"
run_commit 'Add template' dot_c.json.tmpl
check "template rendering to invalid json: refused" "1|1" "$RC|$(commit_count)"

# 13. A template feeding an unchecked type is never rendered.
new_case
rm -f "$RENDER_LOG"
printf 'RENDER_FAILS\n' >"$CASE_REPO/dot_notes.txt.tmpl"
run_commit 'Add notes' dot_notes.txt.tmpl
check "unchecked template type: committed, never rendered" "0|no render" "$RC|$([[ -e $RENDER_LOG ]] && echo rendered || echo 'no render')"

# 14. Paths with spaces survive the NUL-separated staged list.
new_case
printf 'def broken(:\n' >"$CASE_REPO/my file.py"
run_commit 'Add spaced' 'my file.py'
check "spaced path: refused and named" "1|true" "$RC|$(err_has 'does not parse: my file.py')"

# 15. A split file's pre-staged hunks and the row's named paths land in one commit.
new_case
printf 'early\n' >"$CASE_REPO/split.txt"
git -C "$CASE_REPO" add split.txt
printf 'early\nlate\n' >"$CASE_REPO/split.txt"
echo whole >"$CASE_REPO/whole.txt"
run_commit 'Add row' whole.txt
check "split row: exit 0" "0" "$RC"
check "split row: both files in the commit" "split.txt,whole.txt" "$(head_files)"
check "split row: the late hunk stays unstaged" "" "$(staged)"
check "split row: committed blob is the early version" "early" "$(git -C "$CASE_REPO" show HEAD:split.txt)"

# 16. The fish and tmux checkers refuse a broken file and pass a sound one.
new_case
mkdir -p "$CASE_REPO/dot_config/fish"
printf 'if true\n' >"$CASE_REPO/dot_config/fish/bad.fish"
run_commit 'Add fish' dot_config/fish/bad.fish
check "fish checker: broken file refused" "1|true" "$RC|$(err_has 'does not parse: dot_config/fish/bad.fish')"
new_case
mkdir -p "$CASE_REPO/dot_config/fish"
printf 'if true\n  echo ok\nend\n' >"$CASE_REPO/dot_config/fish/good.fish"
run_commit 'Add fish' dot_config/fish/good.fish
check "fish checker: sound file committed" "0|Add fish" "$RC|$(head_subject)"
new_case
printf 'bind\n' >"$CASE_REPO/dot_tmux.conf"
run_commit 'Add tmux' dot_tmux.conf
check "tmux checker: broken conf refused" "1|true" "$RC|$(err_has 'does not parse: dot_tmux.conf')"
new_case
printf 'set -g mouse on\n' >"$CASE_REPO/dot_tmux.conf"
run_commit 'Add tmux' dot_tmux.conf
check "tmux checker: sound conf committed" "0|Add tmux" "$RC|$(head_subject)"

echo
echo "Pass: $PASS  Fail: $FAIL"
[[ $FAIL -eq 0 ]] || exit 1
