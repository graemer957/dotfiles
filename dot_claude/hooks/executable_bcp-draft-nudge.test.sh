#!/usr/bin/env bash
# Self-tests for bcp-draft-nudge.py.
# Feeds the hook synthetic UserPromptSubmit payloads over fixture transcripts and
# checks whether it adds the reminder.
# Run: ./bcp-draft-nudge.test.sh
set -uo pipefail

HOOK="$(dirname "$0")/bcp-draft-nudge.py"
PASS=0
FAIL=0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

HUMAN='{"type":"user","origin":{"kind":"human"},"message":{"content":"go"}}'
BCP='{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill","input":{"skill":"bcp"}}]}}'
READ_CHECKLIST='{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read","input":{"file_path":"/home/g/.claude/skills/bcp/authoring.md"}}]}}'

say() { # assistant text entry
  jq -cn --arg t "$1" '{type:"assistant",message:{content:[{type:"text",text:$t}]}}'
}

SAY_DONE=$(say 'Done.')
SAY_PATH=$(say 'I would change .claude/skills/review-pr/SKILL.md to say so.')
SAY_BARE=$(say 'The skill ran and the hook passed.')

fixture() { # name, lines...
  local f="$TMP/$1"; shift
  printf '%s\n' "$@" > "$f"
}

check() {
  local name="$1" transcript="$2" prompt="$3" want="$4"
  local out
  if ! out=$(jq -n --arg tr "$transcript" --arg p "$prompt" \
    '{hook_event_name:"UserPromptSubmit",transcript_path:$tr,prompt:$p}' | "$HOOK"); then
    echo "FAIL $name  → hook exited non-zero"; FAIL=$((FAIL+1)); return
  fi
  if [[ -z "$out" && "$want" == "silent" ]]; then
    echo "OK   $name  → silent"; PASS=$((PASS+1))
  elif echo "$out" | jq -e '.hookSpecificOutput.additionalContext | test("authoring.md")' >/dev/null 2>&1 \
    && [[ "$want" == "nudge" ]]; then
    echo "OK   $name  → nudge"; PASS=$((PASS+1))
  else
    echo "FAIL $name  → got: ${out:-<empty>}  | want: $want"; FAIL=$((FAIL+1))
  fi
}

fixture plain "$HUMAN" "$SAY_DONE"
fixture path "$HUMAN" "$SAY_PATH"
fixture bare "$HUMAN" "$SAY_BARE"
fixture bcp "$HUMAN" "$BCP" "$SAY_DONE"
fixture read "$HUMAN" "$READ_CHECKLIST" "$SAY_DONE"
fixture stale "$HUMAN" "$BCP" "$SAY_DONE" "$HUMAN" "$SAY_DONE"
fixture recorded "$HUMAN" "$BCP" "$SAY_DONE" "$HUMAN"
fixture recorded_stale "$HUMAN" "$BCP" "$SAY_DONE" "$HUMAN" "$SAY_DONE" "$HUMAN"
fixture path_then_bcp "$HUMAN" "$BCP" "$SAY_PATH"

# The prompt names an instruction file, bcp didn't run in the turn just ended → nudge.
check "prompt names a skill"         "$TMP/plain" "tighten the review-pr skill" nudge
check "prompt names a hook"          "$TMP/plain" "the hook fired again, fix it" nudge
check "prompt names CLAUDE.md"       "$TMP/plain" "add that to CLAUDE.md" nudge
check "prompt names a rules path"    "$TMP/plain" "edit .claude/rules/ci.md" nudge
check "bcp two turns back"           "$TMP/stale" "now the skill" nudge
check "recorded prompt, stale bcp"   "$TMP/recorded_stale" "now the skill" nudge
check "missing transcript"           "/nonexistent/t.jsonl" "update the skill" nudge

# The turn just ended named one by path → nudge on a bare go-ahead.
check "assistant named a path"       "$TMP/path" "yes, do that" nudge

# bcp ran in the turn just ended → silent.
check "bcp ran last turn"            "$TMP/bcp" "now the skill" silent
check "checklist read last turn"     "$TMP/read" "now the skill" silent
check "prompt already on disk"       "$TMP/recorded" "now the skill" silent
check "path named after bcp"         "$TMP/path_then_bcp" "yes, do that" silent

# Nothing names an instruction file → silent.
check "plain prompt"                 "$TMP/plain" "run the tests" silent
check "assistant's bare words"       "$TMP/bare" "carry on" silent
check "upskilling is not a skill"    "$TMP/plain" "upskilling the team on webhooks" silent
check "missing transcript, plain"    "/nonexistent/t.jsonl" "run the tests" silent

out=$(printf 'not json' | "$HOOK")
if [[ -z "$out" ]]; then
  echo "OK   malformed payload  → silent"; PASS=$((PASS+1))
else
  echo "FAIL malformed payload  → got: $out"; FAIL=$((FAIL+1))
fi

echo
echo "Pass: $PASS  Fail: $FAIL"
exit $((FAIL > 0))
