#!/usr/bin/env bash
# Self-tests for bcp-instruction-gate.py.
# Feeds the hook synthetic PreToolUse payloads and checks the decision.
# Run: ./bcp-instruction-gate.test.sh
set -u

HOOK="$(dirname "$0")/bcp-instruction-gate.py"
PASS=0
FAIL=0

WITH_BCP=$(mktemp)
WITHOUT_BCP=$(mktemp)
printf '%s\n' '{"name":"Skill","input":{"skill":"bcp","args":""}}' > "$WITH_BCP"
printf '%s\n' '{"name":"Read","input":{"file_path":"/x"}}' > "$WITHOUT_BCP"
trap 'rm -f "$WITH_BCP" "$WITHOUT_BCP"' EXIT

test_case() {
  local name="$1" tool="$2" path="$3" transcript="$4" want="$5"
  local out
  out=$(jq -n --arg t "$tool" --arg p "$path" --arg tr "$transcript" \
    '{tool_name:$t,tool_input:{file_path:$p},transcript_path:$tr}' | "$HOOK")
  if [[ -z "$out" && "$want" == "fall-through" ]]; then
    echo "OK   $name  → silent (fall through)"; PASS=$((PASS+1))
  elif echo "$out" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null 2>&1 && [[ "$want" == "deny" ]]; then
    echo "OK   $name  → deny"; PASS=$((PASS+1))
  else
    echo "FAIL $name  → got: ${out:-<empty>}  | want: $want"; FAIL=$((FAIL+1))
  fi
}

# Instruction files, bcp not invoked → deny.
test_case "personal skill, no bcp"     Edit  "/home/g/dev/work/.claude/skills/review-pr/SKILL.md" "$WITHOUT_BCP" "deny"
test_case "repo skill, no bcp"         Edit  "/home/g/dev/work/platformed/.claude/skills/i18n/SKILL.md" "$WITHOUT_BCP" "deny"
test_case "skill supporting file"      Edit  "/home/g/.claude/skills/bcp/registry.md" "$WITHOUT_BCP" "deny"
test_case "global CLAUDE.md (chezmoi)" Edit  "/home/g/.local/share/chezmoi/dot_claude/CLAUDE.md" "$WITHOUT_BCP" "deny"
test_case "work CLAUDE.md"             Edit  "/home/g/dev/work/.claude/CLAUDE.md" "$WITHOUT_BCP" "deny"
test_case "project CLAUDE.md"          Edit  "/home/g/dev/work/platformed/CLAUDE.md" "$WITHOUT_BCP" "deny"
test_case "rule (chezmoi source)"      Edit  "/home/g/.local/share/chezmoi/dot_claude/rules/ci.md" "$WITHOUT_BCP" "deny"
test_case "hook script"                Write "/home/g/dev/work/.claude/hooks/new-guard.py" "$WITHOUT_BCP" "deny"
test_case "Write of brand-new skill"   Write "/home/g/dev/work/platformed/.claude/skills/new/SKILL.md" "$WITHOUT_BCP" "deny"

# Same paths with bcp invoked → fall through.
test_case "personal skill, bcp ran"    Edit  "/home/g/dev/work/.claude/skills/review-pr/SKILL.md" "$WITH_BCP" "fall-through"
test_case "CLAUDE.md, bcp ran"         Edit  "/home/g/dev/work/.claude/CLAUDE.md" "$WITH_BCP" "fall-through"

# Non-instruction paths → fall through regardless.
test_case "ordinary rust file"         Edit  "/home/g/dev/work/platformed/rust/shared/database/src/lib.rs" "$WITHOUT_BCP" "fall-through"
test_case "memory file"                Write "/home/g/dev/work/.claude/projects/-p/memory/MEMORY.md" "$WITHOUT_BCP" "fall-through"
test_case "settings.json"              Edit  "/home/g/dev/work/.claude/settings.json" "$WITHOUT_BCP" "fall-through"
test_case "docs mentioning skills"     Edit  "/home/g/dev/work/platformed/docs/skills-overview.md" "$WITHOUT_BCP" "fall-through"

# Fail-open: unreadable transcript → fall through.
test_case "missing transcript"         Edit  "/home/g/dev/work/.claude/skills/review-pr/SKILL.md" "/nonexistent/t.jsonl" "fall-through"

# Non-edit tools → fall through.
test_case "Bash tool ignored"          Bash  "/home/g/dev/work/.claude/skills/review-pr/SKILL.md" "$WITHOUT_BCP" "fall-through"

echo
echo "Pass: $PASS  Fail: $FAIL"
exit $((FAIL > 0))
