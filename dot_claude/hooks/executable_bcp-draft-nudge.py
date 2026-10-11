#!/usr/bin/env python3
"""Ask for the bcp authoring checklist before an instruction-file draft is composed.

UserPromptSubmit: when the prompt names an instruction file (SKILL.md,
CLAUDE.md, a .claude/ or dot_claude/ skills/rules/hooks path, or the bare word
"skill" or "hook"), or the assistant's text in the turn just ended names one by
path, and bcp did not run in that turn, adds one sentence of context asking for
the checklist to be read and applied before any draft is shown.

No hook runs before assistant text is displayed, so the prompt is the last
point ahead of a draft; bcp-proposal-gate.py acts once the draft is on screen.
The sentence is advisory, and a false match costs only its length, so the bare
words count in the prompt. The assistant's own text is matched by path alone:
it mentions skills in most turns of any session that uses one.

Silent on an unreadable transcript when the prompt alone doesn't match.
"""

import json
import re
import sys

from bcp_window import bcp_ran, blocks, human_window, load

PATH_TERM = re.compile(
    r"SKILL\.md|CLAUDE\.md|(?:\.claude|dot_claude)/(?:skills|rules|hooks)/",
    re.IGNORECASE,
)
PROMPT_TERM = re.compile(rf"{PATH_TERM.pattern}|\bskills?\b|\bhooks?\b", re.IGNORECASE)

NUDGE = (
    "An instruction file (a skill, hook, rule or CLAUDE.md) is named, so a change "
    "to one may follow. Before showing any draft or proposal of such a change, read "
    "the bcp skill's authoring.md and run its audit checklist against the draft, "
    "naming the sources that ran: the first version Graeme sees is the audited one. "
    "This applies only when an instruction file is being changed."
)


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    if not isinstance(payload, dict):
        return
    try:
        entries = load(payload.get("transcript_path") or "")
    except OSError:
        entries = []

    # The prompt being submitted may already be on disk, so the turn just
    # ended runs up to the last assistant entry.
    done = len(entries)
    while done and entries[done - 1].get("type") != "assistant":
        done -= 1
    ended = entries[:done]
    last_turn = "\n".join(
        b.get("text") or ""
        for e in ended[human_window(ended, 1) :]
        if e.get("type") == "assistant"
        for b in blocks(e)
        if b.get("type") == "text"
    )

    named = PROMPT_TERM.search(str(payload.get("prompt") or "")) or PATH_TERM.search(
        last_turn
    )
    if not named or bcp_ran(ended, 1):
        return

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": NUDGE,
                }
            }
        )
    )


if __name__ == "__main__":
    main()
