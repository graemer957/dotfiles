#!/usr/bin/env bash
# Self-tests for bcp-mark.py.
# Feeds the hook synthetic PostToolUse payloads and checks which marker it touches.
# Run: ./bcp-mark.test.sh
set -uo pipefail

HOOK="$(dirname "$0")/bcp-mark.py"
PASS=0
FAIL=0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

mark_case() {
  local name="$1" payload="$2" marker="$3" want="$4"
  rm -rf "${TMP:?}/s"
  if ! out=$(printf '%s' "$payload" | "$HOOK"); then
    echo "FAIL $name  → hook exited non-zero"; FAIL=$((FAIL+1)); return
  fi
  if [[ -n "$out" ]]; then
    echo "FAIL $name  → printed: $out"; FAIL=$((FAIL+1)); return
  fi
  local got=absent
  [[ -e "$TMP/s/$marker" ]] && got=present
  if [[ "$got" == "$want" ]]; then
    echo "OK   $name  → $marker $got"; PASS=$((PASS+1))
  else
    echo "FAIL $name  → $marker $got | want: $want"; FAIL=$((FAIL+1))
  fi
}

T="$TMP/s.jsonl"
mark_case "Skill(bcp) marks the session" \
  "{\"tool_name\":\"Skill\",\"tool_input\":{\"skill\":\"bcp\"},\"transcript_path\":\"$T\"}" bcp-ran present
mark_case "Skill(bcp) with args"         \
  "{\"tool_name\":\"Skill\",\"tool_input\":{\"skill\":\"bcp\",\"args\":\"authoring\"},\"transcript_path\":\"$T\"}" bcp-ran present
mark_case "subagent marks its own"       \
  "{\"tool_name\":\"Skill\",\"tool_input\":{\"skill\":\"bcp\"},\"transcript_path\":\"$T\",\"agent_id\":\"a1\"}" bcp-ran-a1 present
mark_case "subagent leaves session's"    \
  "{\"tool_name\":\"Skill\",\"tool_input\":{\"skill\":\"bcp\"},\"transcript_path\":\"$T\",\"agent_id\":\"a1\"}" bcp-ran absent
mark_case "another skill"                \
  "{\"tool_name\":\"Skill\",\"tool_input\":{\"skill\":\"i18n\"},\"transcript_path\":\"$T\"}" bcp-ran absent
mark_case "another command"              \
  "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"bcp\"},\"transcript_path\":\"$T\"}" bcp-ran absent
mark_case "checklist read marks"         \
  "{\"tool_name\":\"Read\",\"tool_input\":{\"file_path\":\"/home/g/.claude/skills/bcp/authoring.md\"},\"transcript_path\":\"$T\"}" bcp-ran present
mark_case "checklist cat marks"          \
  "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"cat /home/g/dev/work/.claude/skills/bcp/authoring.md\"},\"transcript_path\":\"$T\"}" bcp-ran present
mark_case "subagent's checklist read"    \
  "{\"tool_name\":\"Read\",\"tool_input\":{\"file_path\":\"/home/g/.claude/skills/bcp/authoring.md\"},\"transcript_path\":\"$T\",\"agent_id\":\"a1\"}" bcp-ran-a1 present
mark_case "another file read"            \
  "{\"tool_name\":\"Read\",\"tool_input\":{\"file_path\":\"/home/g/.claude/skills/bcp/registry.md\"},\"transcript_path\":\"$T\"}" bcp-ran absent
mark_case "checklist counted, not shown" \
  "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"rg -c Audit /home/g/.claude/skills/bcp/authoring.md\"},\"transcript_path\":\"$T\"}" bcp-ran absent
mark_case "another tool"                 \
  "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"/home/g/.claude/skills/bcp/authoring.md\"},\"transcript_path\":\"$T\"}" bcp-ran absent
mark_case "no transcript path"           \
  '{"tool_name":"Skill","tool_input":{"skill":"bcp"}}' bcp-ran absent
mark_case "malformed payload"            'not json' bcp-ran absent

echo
echo "Pass: $PASS  Fail: $FAIL"
exit $((FAIL > 0))
