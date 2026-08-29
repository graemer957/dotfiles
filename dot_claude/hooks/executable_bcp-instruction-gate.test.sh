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

bash_case() {
  local name="$1" cmd="$2" transcript="$3" want="$4"
  local out
  out=$(jq -n --arg c "$cmd" --arg tr "$transcript" \
    '{tool_name:"Bash",tool_input:{command:$c},transcript_path:$tr}' | "$HOOK")
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

# Bash: mutating command naming an instruction path, bcp not invoked → deny.
bash_case "sed -i on SKILL.md"         "sed -i 's/a/b/' /home/g/dev/work/.claude/skills/review-pr/SKILL.md" "$WITHOUT_BCP" "deny"
bash_case "python heredoc, rel path"   $'python3 - <<\'EOF\'\np=\'.claude/skills/security-duty/SKILL.md\'\nEOF' "$WITHOUT_BCP" "deny"
bash_case "redirect into CLAUDE.md"    "printf x >> /home/g/dev/work/.claude/CLAUDE.md" "$WITHOUT_BCP" "deny"
bash_case "cp over chezmoi rule"       "cp /tmp/ci.md /home/g/.local/share/chezmoi/dot_claude/rules/ci.md" "$WITHOUT_BCP" "deny"
bash_case "tee into hook"              "cat /tmp/h.py | tee /home/g/.claude/hooks/new-guard.py" "$WITHOUT_BCP" "deny"
bash_case "stderr append into CLAUDE.md" "build 2>> /home/g/dev/work/.claude/CLAUDE.md" "$WITHOUT_BCP" "deny"
bash_case "both streams into hook"     "build &> /home/g/.claude/hooks/new-guard.py" "$WITHOUT_BCP" "deny"

# Bash: same commands with bcp invoked → fall through.
bash_case "sed -i, bcp ran"            "sed -i 's/a/b/' /home/g/dev/work/.claude/skills/review-pr/SKILL.md" "$WITH_BCP" "fall-through"

# Bash: read-only or non-instruction → fall through.
bash_case "cat SKILL.md"               "cat /home/g/dev/work/.claude/skills/review-pr/SKILL.md" "$WITHOUT_BCP" "fall-through"
bash_case "sed -n on CLAUDE.md"        "sed -n '1,20p' /home/g/dev/work/.claude/CLAUDE.md" "$WITHOUT_BCP" "fall-through"
bash_case "rg across skills"           "rg -n foo /home/g/dev/work/.claude/skills/" "$WITHOUT_BCP" "fall-through"
bash_case "sed -i on rust file"        "sed -i 's/a/b/' /home/g/dev/work/platformed/rust/shared/database/src/lib.rs" "$WITHOUT_BCP" "fall-through"
bash_case "redirect to memory file"    "printf x >> /home/g/dev/work/.claude/projects/-p/memory/MEMORY.md" "$WITHOUT_BCP" "fall-through"
bash_case "read, stderr merged"        "cat /home/g/dev/work/.claude/skills/review-pr/SKILL.md 2>&1 | head" "$WITHOUT_BCP" "fall-through"
bash_case "read, stderr discarded"     "ls -1 /home/g/.claude/hooks/ 2>/dev/null" "$WITHOUT_BCP" "fall-through"
bash_case "diff naming CLAUDE.md"      "git diff main HEAD -- CLAUDE.md .claude/ 2>&1" "$WITHOUT_BCP" "fall-through"
bash_case "rg output discarded"        "rg -n foo /home/g/dev/work/.claude/skills/ >/dev/null" "$WITHOUT_BCP" "fall-through"

# Non-edit tools → fall through.
test_case "Read tool ignored"          Read  "/home/g/dev/work/.claude/skills/review-pr/SKILL.md" "$WITHOUT_BCP" "fall-through"

echo
echo "Pass: $PASS  Fail: $FAIL"
exit $((FAIL > 0))
