#!/usr/bin/env python3
"""Block renaming a GitHub branch through `gh api`.

Renaming a branch an open PR is raised from closes that PR, and a closed PR
can't be reopened once its head branch name is gone: the PR stays closed under
Graeme's name. The work CLAUDE.md fixes a branch's name once its PR is open.

Emits a PreToolUse `deny` for any command that pairs `gh api` with a
`branches/<name>/rename` endpoint, whatever the method or quoting. Everything
else falls through to normal permission handling. Runs unconditionally: a
prefix-anchored `if:` gate skips compound commands.
"""

import json
import re
import sys

GH_API = re.compile(r"\bgh\s+api\b")
RENAME_ENDPOINT = re.compile(r"branches/\S+/rename\b")


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    if payload.get("tool_name") != "Bash":
        return
    command = payload.get("tool_input", {}).get("command", "")
    if not (GH_API.search(command) and RENAME_ENDPOINT.search(command)):
        return
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "Branch rename blocked. Renaming a branch closes any PR raised from it, "
                        "and the closed PR stays on Graeme's record. A branch keeps its name once "
                        "its PR is open — pick a new name for new work instead, or hand back."
                    ),
                }
            }
        )
    )


if __name__ == "__main__":
    main()
