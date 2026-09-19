#!/usr/bin/env bash
# Self-tests for gh-branch-rename-guard.py.
# Feeds the hook synthetic PreToolUse payloads and checks the decision.
# Run: ./gh-branch-rename-guard.test.sh
set -u

HOOK="$(dirname "$0")/gh-branch-rename-guard.py"
PASS=0
FAIL=0

test_case() {
  local name="$1"; local cmd="$2"; local want="$3"
  local out
  out=$(printf '%s\n' "$cmd" | jq -Rn '{tool_name:"Bash",tool_input:{command:input}}' | "$HOOK")
  if [[ -z "$out" && "$want" == "fall-through" ]]; then
    echo "OK   $name  → silent (fall through)"; PASS=$((PASS+1))
  elif echo "$out" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null 2>&1 && [[ "$want" == "deny" ]]; then
    echo "OK   $name  → deny"; PASS=$((PASS+1))
  else
    echo "FAIL $name  → got: ${out:-<empty>}  | want: $want"; FAIL=$((FAIL+1))
  fi
}

# Every spelling of the rename endpoint.
test_case "POST rename, -f new_name"     'gh api -X POST repos/platformed-com/platformed/branches/gr/x/rename -f new_name=gr/y' "deny"
test_case "placeholder repo path"        'gh api -X POST repos/{owner}/{repo}/branches/gr/p4d-1234/rename -f new_name=gr/p4d-1234/backend' "deny"
test_case "leading slash, --method"      'gh api --method POST /repos/o/r/branches/main-ish/rename --field new_name=z' "deny"
test_case "quoted endpoint"              'gh api -X POST "repos/o/r/branches/gr/x/rename" -f new_name=gr/y' "deny"
test_case "method defaulted by -f"       'gh api repos/o/r/branches/gr/x/rename -f new_name=gr/y' "deny"
test_case "after cd and &&"              'cd /tmp && gh api -X POST repos/o/r/branches/gr/x/rename -f new_name=y' "deny"
test_case "env-prefixed"                 'GH_HOST=github.com gh api -X POST repos/o/r/branches/x/rename -f new_name=y' "deny"

# Neighbouring calls that stay allowed.
test_case "branch GET"                   'gh api repos/o/r/branches/gr/x'                                          "fall-through"
test_case "branch protection GET"        'gh api repos/o/r/branches/main/protection'                               "fall-through"
test_case "branches list"                'gh api repos/o/r/branches --paginate'                                   "fall-through"
test_case "pr view"                      'gh pr view 5783 --json headRefName'                                     "fall-through"
test_case "git branch -m (local only)"   'git branch -m gr/x gr/y'                                                "fall-through"
test_case "rename word elsewhere"        'rg -n rename .claude/skills'                                            "fall-through"

echo
echo "$PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
