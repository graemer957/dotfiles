#!/usr/bin/env bash
# Self-tests for bcp-proposal-gate.py.
# Feeds the hook synthetic Stop payloads over fixture transcripts and checks the decision.
# Run: ./bcp-proposal-gate.test.sh
set -uo pipefail

HOOK="$(dirname "$0")/bcp-proposal-gate.py"
PASS=0
FAIL=0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

HUMAN='{"type":"user","origin":{"kind":"human"},"message":{"content":"go"}}'
NOTIFY='{"type":"user","origin":{"kind":"task-notification"},"message":{"content":"<task-notification>"}}'
BCP='{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill","input":{"skill":"bcp"}}]}}'
QUEUED='{"type":"attachment","attachment":{"type":"queued_command","origin":{"kind":"human"},"prompt":"also this"}}'
QUEUED_BCP='{"type":"attachment","attachment":{"type":"queued_command","origin":{"kind":"human"},"prompt":"<command-name>/bcp</command-name>"}}'
READ_CHECKLIST='{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read","input":{"file_path":"/home/g/.claude/skills/bcp/authoring.md"}}]}}'
CAT_CHECKLIST='{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash","input":{"command":"cat /home/g/.claude/skills/bcp/authoring.md"}}]}}'
READ_OTHER='{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read","input":{"file_path":"/home/g/.claude/skills/bcp/registry.md"}}]}}'

say() { # assistant text entry
  jq -cn --arg t "$1" '{type:"assistant",message:{content:[{type:"text",text:$t}]}}'
}

SKILL_DIFF=$'Proposed edit to `SKILL.md`:\n\n```diff\n+- Own goals stay out.\n```'
PATH_DIFF=$'Edit to `.claude/rules/ci.md`:\n\n```diff\n-old\n+new\n```'
RUST_DIFF=$'Change to `lib.rs`:\n\n```diff\n-let x = 1;\n+let x = 2;\n```'
SKILL_PROSE='I updated SKILL.md as agreed.'
MD_DRAFT=$'New rule for `SKILL.md`:\n\n```markdown\n- Own goals stay out.\n```'
BARE_WORD_DIFF=$'The skill-file edit is applied; here is the workflow area it pairs with:\n\n```diff\n-a\n+b\n```'

SAY_SKILL_DIFF=$(say "$SKILL_DIFF")
SAY_PATH_DIFF=$(say "$PATH_DIFF")
SAY_RUST_DIFF=$(say "$RUST_DIFF")
SAY_SKILL_PROSE=$(say "$SKILL_PROSE")
SAY_ASK=$(say 'Shall I apply it?')
SAY_DONE=$(say 'Done.')
SAY_MD_DRAFT=$(say "$MD_DRAFT")
SAY_BARE_WORD_DIFF=$(say "$BARE_WORD_DIFF")
SAY_NOT_INSTRUCTION=$(say 'Not an instruction file.')
SAY_AGENT_DONE=$(say 'Agent finished.')

fixture() { # name, lines...
  local f="$TMP/$1"; shift
  printf '%s\n' "$@" > "$f"
}

check() {
  local name="$1" transcript="$2" want="$3" active="${4:-false}" last="${5:-}"
  local out
  if ! out=$(jq -n --arg tr "$transcript" --argjson a "$active" --arg l "$last" \
    '{hook_event_name:"Stop",transcript_path:$tr,stop_hook_active:$a,last_assistant_message:$l}' | "$HOOK"); then
    echo "FAIL $name  → hook exited non-zero"; FAIL=$((FAIL+1)); return
  fi
  if [[ -z "$out" && "$want" == "pass" ]]; then
    echo "OK   $name  → pass"; PASS=$((PASS+1))
  elif echo "$out" | jq -e '.decision == "block"' >/dev/null 2>&1 && [[ "$want" == "block" ]]; then
    echo "OK   $name  → block"; PASS=$((PASS+1))
  else
    echo "FAIL $name  → got: ${out:-<empty>}  | want: $want"; FAIL=$((FAIL+1))
  fi
}

fixture a "$HUMAN" "$SAY_SKILL_DIFF"
fixture b "$HUMAN" "$SAY_PATH_DIFF"
fixture c "$HUMAN" "$SAY_SKILL_DIFF" "$SAY_ASK"
fixture d "$HUMAN" "$BCP" "$HUMAN" "$SAY_SKILL_DIFF"
fixture e "$HUMAN"
fixture f "$HUMAN" "$BCP" "$SAY_SKILL_DIFF"
fixture g "$HUMAN" "$BCP" "$NOTIFY" "$SAY_SKILL_DIFF"
fixture h "$HUMAN" "$SAY_RUST_DIFF"
fixture i "$HUMAN" "$SAY_SKILL_PROSE"
fixture j "$HUMAN" "$SAY_SKILL_DIFF" "$HUMAN" "$SAY_DONE"
fixture k "$HUMAN" "$SAY_MD_DRAFT"
fixture l "$HUMAN" "$SAY_SKILL_DIFF" "$BCP" "$SAY_DONE"
fixture m "$HUMAN" "$SAY_SKILL_DIFF" "$BCP" "$SAY_SKILL_DIFF"
fixture n "$HUMAN" "$SAY_PATH_DIFF" "$SAY_NOT_INSTRUCTION" "$NOTIFY" "$SAY_AGENT_DONE"
fixture o "$HUMAN" "$BCP" "$QUEUED" "$SAY_SKILL_DIFF"
fixture p "$HUMAN" "$QUEUED_BCP" "$SAY_SKILL_DIFF"
fixture q "$HUMAN" "$BCP" "$HUMAN" "$SAY_DONE" "$HUMAN" "$SAY_SKILL_DIFF"
fixture r "$HUMAN" "$READ_CHECKLIST" "$SAY_SKILL_DIFF"
fixture s "$HUMAN" "$CAT_CHECKLIST" "$SAY_SKILL_DIFF"
fixture t "$HUMAN" "$READ_OTHER" "$SAY_SKILL_DIFF"
fixture u "$HUMAN" "$SAY_BARE_WORD_DIFF"

# Instruction-file diff, no bcp in this turn or the last → block.
check "skill diff, no bcp"         "$TMP/a" block
check "rule-path diff, no bcp"     "$TMP/b" block
check "diff mid-turn, prose last"  "$TMP/c" block
check "diff only in payload"       "$TMP/e" block false "$SKILL_DIFF"
check "markdown-fenced skill draft" "$TMP/k" block
check "bcp after the draft only"   "$TMP/l" block
check "bcp two turns back"         "$TMP/q" block
check "another bcp file read"      "$TMP/t" block

# bcp ran in this turn or the last → pass; notifications don't open a turn.
check "skill diff, bcp ran"        "$TMP/f" pass
check "bcp in the previous turn"   "$TMP/d" pass
check "bcp before a queued msg"    "$TMP/o" pass
check "bcp before notifications"   "$TMP/g" pass
check "re-presented after bcp"     "$TMP/m" pass
check "queued /bcp counts"         "$TMP/p" pass
check "checklist read counts"      "$TMP/r" pass
check "checklist cat counts"       "$TMP/s" pass
check "notification wake re-judges nothing" "$TMP/n" pass

# Not an instruction-file diff → pass.
check "rust diff"                  "$TMP/h" pass
check "skill named, no diff"       "$TMP/i" pass
check "skill diff in earlier turn" "$TMP/j" pass
check "bare word beside a diff"    "$TMP/u" pass

# Loop guard and fail-open.
check "second stop passes"         "$TMP/a" pass true
check "missing transcript"         "/nonexistent/t.jsonl" pass

echo
echo "Pass: $PASS  Fail: $FAIL"
exit $((FAIL > 0))
