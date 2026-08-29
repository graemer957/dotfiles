#!/usr/bin/env python3
"""Gate instruction-file edits on the bcp skill having been invoked this session.

On an Edit/Write to an instruction file — a SKILL.md, a CLAUDE.md, anything
under a .claude/{skills,rules,hooks}/ directory, or their chezmoi sources
(dot_claude/...) — or a Bash command that both names such a path and carries a
mutating token (sed -i, redirection, tee, an interpreter, cp/mv/rm), checks the
session transcript for a Skill(bcp) invocation. Absent one, denies the call
with instructions to invoke the skill and retry; present, stays silent.
Non-instruction paths always fall through, as does a Bash command that only
reads (cat/rg/sed -n) an instruction file, including one that redirects stderr
or discards output.

Bash is matched on the command text because its payload carries no file_path:
the path is whatever the command string names, so the same patterns run over
the string, anchored at a path boundary rather than a leading slash so relative
paths (`.claude/skills/x/SKILL.md`) match too. A false positive costs one
Skill(bcp) call; a miss costs the audit — so the mutating-token net is broad.
A redirection is the one token narrow enough to judge by its target: `2>&1` and
`/dev/null` are how a read command silences noise, so counting them as writes
would gate reading an instruction file as well as editing one.

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

# Same set, anchored at a path boundary for scanning a Bash command string.
COMMAND_PATHS = (
    re.compile(r"(?:^|[\s/'\"=(])SKILL\.md\b"),
    re.compile(r"(?:^|[\s/'\"=(])CLAUDE\.md\b"),
    re.compile(r"(?:^|[\s/'\"=(])\.claude/(skills|rules|hooks)/"),
    re.compile(r"(?:^|[\s/'\"=(])dot_claude/(skills|rules|hooks)/"),
)

MUTATING = re.compile(
    r"(?:sed\s+(?:-[a-zA-Z]*i|--in-place)"
    # `(?!>)` keeps `>>` from backtracking to a bare `>` and slipping the
    # target check below.
    r"|>>?(?!>)\s*(?!&\d|/dev/null\b)"
    r"|\btee\b|\bpython[23]?\b|\bperl\b|\bruby\b"
    r"|\bnode\b|\bcp\b|\bmv\b|\brm\b|\brumdl\s+fmt\b|\bdd\b)"
)

BCP_MARKERS = ('"skill":"bcp"', "Launching skill: bcp")


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input", {})
    if tool in ("Edit", "Write"):
        if not any(p.search(tool_input.get("file_path", "")) for p in INSTRUCTION_PATHS):
            return
    elif tool == "Bash":
        command = tool_input.get("command", "")
        if not MUTATING.search(command):
            return
        if not any(p.search(command) for p in COMMAND_PATHS):
            return
    else:
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
