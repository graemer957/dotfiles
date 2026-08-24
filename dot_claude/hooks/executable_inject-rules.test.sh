#!/usr/bin/env bash
# Self-tests for inject-rules.py.
# Feeds the hook synthetic PostToolUse payloads against fixture rules and
# checks which rules inject. Run: ./inject-rules.test.sh
set -u

HOOK="$(dirname "$0")/inject-rules.py"
PASS=0
FAIL=0

FIXTURES=$(mktemp -d)
trap 'rm -rf "$FIXTURES"; rm -rf "/tmp/claude-rule-inject-$(id -u)"/test-* 2>/dev/null' EXIT

mk_rule() { printf '%s\n' "---" "paths:" "${@:2}" "---" "" "body of $1" > "$FIXTURES/$1.md"; }
mk_rule markdown '  - "**/*.md"'
mk_rule rust '  - "**/*.rs"' '  - "**/Cargo.toml"'
mk_rule skills '  - "**/SKILL.md"' '  - ".claude/skills/**"'
mk_rule ci '  - ".github/**"'
printf '%s\n' "---" "paths:" '  - "**/*.{ts,tsx}"' "---" "" "body of braces" > "$FIXTURES/braces.md"
printf '%s\n' "---" 'paths: ["**/*.css"]' "---" "" "body of flow" > "$FIXTURES/flow.md"

# test_case NAME SESSION TOOL PATH WANT
# WANT: comma-separated rule names expected to inject, "silent", or "warns".
test_case() {
  local name="$1" session="$2" tool="$3" path="$4" want="$5"
  local out ctx
  out=$(jq -n --arg t "$tool" --arg p "$path" --arg s "test-$session" \
    '{tool_name:$t,tool_input:{file_path:$p},session_id:$s}' | INJECT_RULES_DIR="$FIXTURES" "$HOOK")
  ctx=$(echo "$out" | jq -r '.hookSpecificOutput.additionalContext // ""' 2>/dev/null)
  case "$want" in
    silent)
      if [[ -z "$out" ]]; then echo "OK   $name → silent"; PASS=$((PASS+1))
      else echo "FAIL $name → got: $out | want: silent"; FAIL=$((FAIL+1)); fi ;;
    warns)
      if echo "$out" | jq -e '.systemMessage' >/dev/null 2>&1; then
        echo "OK   $name → warns"; PASS=$((PASS+1))
      else echo "FAIL $name → got: ${out:-<empty>} | want: systemMessage"; FAIL=$((FAIL+1)); fi ;;
    *)
      local ok=1 rule
      IFS=, read -ra rules <<< "$want"
      for rule in "${rules[@]}"; do
        grep -q "<rule name=\"$rule\">" <<< "$ctx" || ok=0
      done
      [[ $(grep -c '<rule name=' <<< "$ctx") -eq ${#rules[@]} ]] || ok=0
      if [[ $ok -eq 1 ]]; then echo "OK   $name → $want"; PASS=$((PASS+1))
      else echo "FAIL $name → got: ${out:-<empty>} | want: $want"; FAIL=$((FAIL+1)); fi ;;
  esac
}

# Out-of-tree surfaces match their rules.
test_case "worktree markdown"     s1 Edit  "/home/g/dev/work/worktrees/platformed-x/docs/a.md" "markdown"
test_case "obsidian note"         s2 Write "/home/g/Documents/Obsidian/Notes/note.md" "markdown"
test_case "worktree rust"         s3 Edit  "/home/g/dev/work/worktrees/platformed-x/rust/lib.rs" "rust"
test_case "worktree Cargo.toml"   s4 Edit  "/home/g/dev/work/worktrees/platformed-x/Cargo.toml" "rust"
test_case "worktree workflow"     s5 Edit  "/home/g/dev/work/worktrees/platformed-x/.github/workflows/ci.yml" "ci"
test_case "config-dir skill"      s6 Edit  "/home/g/dev/work/.claude/skills/foo/notes.md" "markdown,skills"
test_case "SKILL.md two rules"    s7 Write "/home/g/.claude/skills/foo/SKILL.md" "markdown,skills"

# In-tree files inject too (deliberate: duplicates the native loader).
test_case "in-tree markdown"      s8 Edit  "/home/g/dev/work/platformed/docs/a.md" "markdown"

# Dedupe: same rule injects once per session; a new rule still fires.
test_case "dedupe first"          s9 Edit  "/a/b.md" "markdown"
test_case "dedupe second"         s9 Edit  "/a/c.md" "silent"
test_case "dedupe rule-scoped"    s9 Edit  "/a/d.rs" "rust"

# Unsupported glob shapes warn once per session, never match.
test_case "brace glob warns"      s10 Edit "/a/b.ts" "warns"
test_case "flow-style warns"      s11 Edit "/a/b.css" "warns"

# Fall-throughs. A fresh session still warns about bad fixture globs on
# its first edit; an unmatched file is only fully silent once it has.
test_case "unmatched ext warns first" s12 Edit "/a/b.txt" "warns"
test_case "unmatched extension"   s12 Edit  "/a/c.txt" "silent"
test_case "non-edit tool"         s13 Bash  "/a/b.md" "silent"
test_case "missing file_path"     s14 Edit  "" "silent"

# Smoke test against the real rules dir: catches parser drift from the
# real frontmatter style. Unique session id each run; no dedupe residue.
REAL_SESSION="test-real-$$"
REAL_OUT=$(jq -n --arg s "$REAL_SESSION" \
  '{tool_name:"Edit",tool_input:{file_path:"/home/g/dev/work/worktrees/platformed-x/docs/a.md"},session_id:$s}' \
  | "$HOOK" | jq -r '.hookSpecificOutput.additionalContext // ""')
if grep -q '<rule name="markdown">' <<< "$REAL_OUT" && grep -q 'rumdl' <<< "$REAL_OUT"; then
  echo "OK   real rules smoke → markdown injects with body"; PASS=$((PASS+1))
else
  echo "FAIL real rules smoke → got: ${REAL_OUT:-<empty>}"; FAIL=$((FAIL+1))
fi

echo
echo "Pass: $PASS  Fail: $FAIL"
exit $((FAIL > 0))
