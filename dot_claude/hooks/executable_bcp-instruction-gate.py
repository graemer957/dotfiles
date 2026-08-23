#!/usr/bin/env python3
"""Gate instruction-file edits on the bcp skill having been invoked this session.

On an Edit/Write to an instruction file — a SKILL.md, a CLAUDE.md, anything
under a .claude/{skills,rules,hooks}/ directory, or their chezmoi sources
(dot_claude/...) — checks the session transcript for a Skill(bcp) invocation.
Absent one, denies the edit with instructions to invoke the skill and retry;
present, stays silent. Non-instruction paths always fall through.

Fail-open on a missing or unreadable transcript: the gate backstops recall,
and locking out every instruction edit on a harness quirk costs more than one
missed audit — the rule and memory layers still stand.
"""

import json
import re
import sys
from pathlib import Path

INSTRUCTION_PATHS = (
    re.compile(r"/SKILL\.md$"),
    re.compile(r"/CLAUDE\.md$"),
    re.compile(r"/\.claude/(skills|rules|hooks)/"),
    re.compile(r"/dot_claude/(skills|rules|hooks)/"),
)

BCP_MARKERS = ('"skill":"bcp"', "Launching skill: bcp")


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    if payload.get("tool_name") not in ("Edit", "Write"):
        return

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not any(p.search(file_path) for p in INSTRUCTION_PATHS):
        return

    transcript = payload.get("transcript_path", "")
    try:
        text = Path(transcript).read_text(errors="replace")
    except OSError:
        return

    if any(m in text for m in BCP_MARKERS):
        return

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "Instruction-file gate: this edit targets a skill/CLAUDE.md/rule/hook, "
                "and the bcp skill has not been invoked this session. Invoke Skill(bcp), "
                "apply its authoring checklist to the change (and to any draft already "
                "shared in chat), then retry this exact edit."
            ),
        }
    }))


if __name__ == "__main__":
    main()
