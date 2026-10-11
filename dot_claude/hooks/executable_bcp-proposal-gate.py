#!/usr/bin/env python3
"""Hold back a turn that shows an instruction-file draft the bcp checklist has not seen.

Stop: when the assistant's text since the last prompt holds a diff or markdown
fence, that text names an instruction file (SKILL.md, CLAUDE.md, or a .claude/
or dot_claude/ skills/rules/hooks path), and bcp has not run in the last two
human turns before the last fenced draft, blocks the stop with instructions to
run the checklist and re-present. A proposal shown for approval is already the
artifact, so the audit belongs before the draft that shows it. The window
matches bcp-instruction-gate.py's, so a diff of an edit that gate let through
is not blocked here.

The text is already on screen when Stop fires: the block can't hide a
non-compliant draft, only force the compliant one to follow it unasked.
Proposals written as prose, with no fence, pass unseen, as does a draft that
names its target only by role ("the skill file"): the bare word matches
ordinary prose about skills, and a false match here costs Graeme a second
reading.

The scan starts at the last prompt of any origin, so a stop woken by a task
notification doesn't re-judge a draft its own chain already answered. A
second stop in the same chain (`stop_hook_active`) always passes, so a false
match costs one short continuation. Fail-open on an unreadable transcript.
"""

import json
import re
import sys

from bcp_window import blocks, has_origin, human_window, invokes_bcp, last_prompt, load

DRAFT_FENCE = re.compile(r"^\s*```(?:diff|markdown|md)\b", re.MULTILINE)
INSTRUCTION_TERM = re.compile(
    r"SKILL\.md|CLAUDE\.md|(?:\.claude|dot_claude)/(?:skills|rules|hooks)/",
    re.IGNORECASE,
)

REASON = (
    "Proposal gate: this turn shows a fenced draft naming an instruction file, and "
    "the bcp authoring checklist has not been in front of you in this turn or the "
    "last. If the draft targets an instruction file: read the bcp skill's "
    "authoring.md (invoke Skill(bcp) first if the skill has not loaded this "
    "session), run its checklist against the draft, and re-present the compliant "
    "version, saying it supersedes the one above and what the checklist changed. "
    "If it targets anything else, say so in one line and stop."
)


def text_of(entry):
    return "\n".join(
        b.get("text") or "" for b in blocks(entry) if b.get("type") == "text"
    )


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    if not isinstance(payload, dict) or payload.get("stop_hook_active"):
        return
    try:
        entries = load(payload.get("transcript_path") or "")
    except OSError:
        return

    chain = last_prompt(entries)
    texts = [
        (i, text_of(e))
        for i, e in enumerate(entries[chain:], chain)
        if e.get("type") == "assistant"
    ]
    final = payload.get("last_assistant_message") or ""
    if final and not any(final.strip() == t.strip() for _, t in texts):
        texts.append((len(entries), final))

    drafts = [i for i, t in texts if DRAFT_FENCE.search(t)]
    if not drafts or not any(INSTRUCTION_TERM.search(t) for _, t in texts):
        return

    origin = has_origin(entries)
    if any(
        invokes_bcp(e, origin) for e in entries[human_window(entries, 2) : drafts[-1]]
    ):
        return

    print(json.dumps({"decision": "block", "reason": REASON}))


if __name__ == "__main__":
    main()
