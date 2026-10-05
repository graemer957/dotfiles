#!/usr/bin/env bash
# Self-tests for bcp-instruction-gate.py.
# Feeds the hook synthetic PreToolUse payloads and checks the decision.
# Run: ./bcp-instruction-gate.test.sh
set -uo pipefail

HOOK="$(dirname "$0")/bcp-instruction-gate.py"
PASS=0
FAIL=0

HUMAN='{"type":"user","origin":{"kind":"human"},"message":{"content":"go"}}'
BCP='{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill","input":{"skill":"bcp"}}]}}'
READ='{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read","input":{"file_path":"/x"}}]}}'
NOTIFY='{"type":"user","origin":{"kind":"task-notification"},"message":{"content":"<task-notification>"}}'

WITH_BCP=$(mktemp)
WITHOUT_BCP=$(mktemp)
PREV_TURN_BCP=$(mktemp)
STALE_BCP=$(mktemp)
NOTIFY_BCP=$(mktemp)
printf '%s\n' "$HUMAN" "$BCP" > "$WITH_BCP"
printf '%s\n' "$HUMAN" "$READ" > "$WITHOUT_BCP"
# bcp in the draft turn, edit in the approval turn.
printf '%s\n' "$HUMAN" "$BCP" "$HUMAN" "$READ" > "$PREV_TURN_BCP"
# bcp two human turns back.
printf '%s\n' "$HUMAN" "$BCP" "$HUMAN" "$READ" "$HUMAN" "$READ" > "$STALE_BCP"
# Notifications don't open a turn, so bcp before two of them still counts.
printf '%s\n' "$HUMAN" "$BCP" "$NOTIFY" "$NOTIFY" "$READ" > "$NOTIFY_BCP"
trap 'rm -f "$WITH_BCP" "$WITHOUT_BCP" "$PREV_TURN_BCP" "$STALE_BCP" "$NOTIFY_BCP"' EXIT

test_case() {
  local name="$1" tool="$2" path="$3" transcript="$4" want="$5"
  local out
  if ! out=$(jq -n --arg t "$tool" --arg p "$path" --arg tr "$transcript" \
    '{tool_name:$t,tool_input:{file_path:$p},transcript_path:$tr}' | "$HOOK"); then
    echo "FAIL $name  → hook pipeline exited non-zero"; FAIL=$((FAIL+1)); return
  fi
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
  if ! out=$(jq -n --arg c "$cmd" --arg tr "$transcript" \
    '{tool_name:"Bash",tool_input:{command:$c},transcript_path:$tr}' | "$HOOK"); then
    echo "FAIL $name  → hook pipeline exited non-zero"; FAIL=$((FAIL+1)); return
  fi
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
test_case "bcp in the previous turn"   Edit  "/home/g/dev/work/.claude/CLAUDE.md" "$PREV_TURN_BCP" "fall-through"
test_case "bcp two turns back"         Edit  "/home/g/dev/work/.claude/CLAUDE.md" "$STALE_BCP" "deny"
test_case "notifications aren't turns" Edit  "/home/g/dev/work/.claude/CLAUDE.md" "$NOTIFY_BCP" "fall-through"

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
bash_case "rumdl check --fix on CLAUDE.md" "rumdl check --fix /home/g/dev/work/.claude/CLAUDE.md" "$WITHOUT_BCP" "deny"
bash_case "curl -o over hook"          "curl -sSL https://x/y.py -o /home/g/.claude/hooks/new-guard.py" "$WITHOUT_BCP" "deny"
bash_case "wget -O over rule"          "wget -q https://x/ci.md -O /home/g/.claude/rules/ci.md" "$WITHOUT_BCP" "deny"
bash_case "rsync into skills"          "rsync -a /tmp/skill/ /home/g/dev/work/.claude/skills/new/" "$WITHOUT_BCP" "deny"
bash_case "tee -a into skill"          "echo x | tee -a /home/g/dev/work/.claude/skills/x/SKILL.md" "$WITHOUT_BCP" "deny"
bash_case "redirect to variable, skill named" $'cat > $S/pr.md <<\'EOF\'\nsee .claude/skills/x/SKILL.md\nEOF' "$WITHOUT_BCP" "deny"

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
bash_case "rumdl check (no --fix)"     "rumdl check -d MD013 /home/g/dev/work/.claude/CLAUDE.md" "$WITHOUT_BCP" "fall-through"
bash_case "curl without -o"            "curl -sSL https://x/y | head -5 # see .claude/skills/x/SKILL.md" "$WITHOUT_BCP" "fall-through"
bash_case "redirect to scratchpad, skill named" "nu /home/g/dev/work/.claude/skills/x/inventory.nu > /tmp/claude-1000/s/out.json" "$WITHOUT_BCP" "fall-through"
bash_case "tee to scratchpad, skill named"      "nu /home/g/dev/work/.claude/skills/x/inventory.nu | tee /tmp/claude-1000/s/out.json" "$WITHOUT_BCP" "fall-through"

# Subagent calls: the payload carries the main transcript plus agent_id, and the
# subagent's own run lives at <main without .jsonl>/subagents/agent-<id>.jsonl.
agent_case() {
  local name="$1" own_line="$2" want="$3" main="$TMP_AGENT/s.jsonl" out
  mkdir -p "$TMP_AGENT/s/subagents"
  printf '%s\n' "$HUMAN" "$READ" > "$main"
  printf '%s\n' "$own_line" > "$TMP_AGENT/s/subagents/agent-a1.jsonl"
  out=$(jq -n --arg tr "$main" \
    '{tool_name:"Edit",tool_input:{file_path:"/home/g/dev/work/.claude/skills/x/SKILL.md"},transcript_path:$tr,agent_id:"a1"}' | "$HOOK")
  if [[ -z "$out" && "$want" == "fall-through" ]] || { [[ -n "$out" && "$want" == "deny" ]]; }; then
    echo "OK   $name  → $want"; PASS=$((PASS+1))
  else
    echo "FAIL $name  → got: ${out:-<empty>}  | want: $want"; FAIL=$((FAIL+1))
  fi
}
TMP_AGENT=$(mktemp -d)
agent_case "subagent ran bcp itself"   "$BCP" "fall-through"
agent_case "subagent without bcp"      "$READ" "deny"
rm -rf "$TMP_AGENT"

# The transcript can lag the hook: a marker bcp-mark.py touched since the window
# opened counts in its place; one older than the window doesn't.
TMP_MARK=$(mktemp -d)
H1='{"type":"user","origin":{"kind":"human"},"timestamp":"2026-01-01T01:00:00Z","message":{"content":"go"}}'
H2='{"type":"user","origin":{"kind":"human"},"timestamp":"2026-01-01T02:00:00Z","message":{"content":"go"}}'
for s in fresh stale; do
  printf '%s\n' "$HUMAN" "$READ" "$H1" "$READ" "$H2" "$READ" > "$TMP_MARK/$s.jsonl"
  mkdir -p "$TMP_MARK/$s"
done
touch "$TMP_MARK/fresh/bcp-ran"
touch -d 2026-01-01T00:30:00Z "$TMP_MARK/stale/bcp-ran"
test_case "marker, transcript lagging" Edit  "/home/g/dev/work/.claude/CLAUDE.md" "$TMP_MARK/fresh.jsonl" "fall-through"
test_case "marker before the window"   Edit  "/home/g/dev/work/.claude/CLAUDE.md" "$TMP_MARK/stale.jsonl" "deny"
# A subagent's marker carries its agent_id.
mkdir -p "$TMP_MARK/agent/subagents"
printf '%s\n' "$HUMAN" "$READ" > "$TMP_MARK/agent.jsonl"
printf '%s\n' "$READ" > "$TMP_MARK/agent/subagents/agent-a1.jsonl"
touch "$TMP_MARK/agent/bcp-ran-a1"
out=$(jq -n --arg tr "$TMP_MARK/agent.jsonl" \
  '{tool_name:"Edit",tool_input:{file_path:"/home/g/dev/work/.claude/skills/x/SKILL.md"},transcript_path:$tr,agent_id:"a1"}' | "$HOOK")
if [[ -z "$out" ]]; then
  echo "OK   subagent marker  → fall-through"; PASS=$((PASS+1))
else
  echo "FAIL subagent marker  → got: $out  | want: fall-through"; FAIL=$((FAIL+1))
fi
rm -rf "$TMP_MARK"

# Non-edit tools → fall through.
test_case "Read tool ignored"          Read  "/home/g/dev/work/.claude/skills/review-pr/SKILL.md" "$WITHOUT_BCP" "fall-through"

echo
echo "Pass: $PASS  Fail: $FAIL"
exit $((FAIL > 0))
