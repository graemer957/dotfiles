"""Session-transcript queries for the bcp gates.

A human turn opens at a message Graeme typed: a `user` entry, or a mid-turn
`queued_command` attachment, whose `origin.kind` is `human`. Tool results, task
notifications, agent hand-backs and compaction summaries carry another or no
origin, so they never open one. Transcripts written before `origin` existed
fall back to treating a non-meta `user` entry without a `tool_result` block as
human.

bcp counts as run at an assistant tool_use that loads the skill or reads its
authoring checklist (`runs_bcp`), or at a human message invoking `/bcp`. The
skill call loads the workflow only; the checklist is `authoring.md`, so reading
it is the nearer evidence that the rules were in front of the model. The
transcript can reach disk after the next tool call's hooks read it, so
`bcp-mark.py` also touches a per-session marker the moment such a call
completes; a marker newer than the window's opening message counts as a run.

`load` raises OSError on an unreadable transcript, so each caller picks its own
fail-open behaviour.
"""

import json
import re
from datetime import datetime
from pathlib import Path

BCP_COMMAND = "<command-name>/bcp</command-name>"
CHECKLIST = re.compile(r"skills/bcp/authoring\.md$")
# A Bash read that prints the checklist: `rg -c` or `wc` over it shows none of it.
CHECKLIST_READ = re.compile(
    r"(?:\bcat\b|\bsed\s+-n\b)[^|;&\n]*skills/bcp/authoring\.md\b"
)


def runs_bcp(tool, tool_input):
    """True for a tool call that loads the bcp skill or reads its authoring checklist."""
    tool_input = tool_input or {}
    if tool == "Skill":
        return tool_input.get("skill") == "bcp"
    if tool == "Read":
        return bool(CHECKLIST.search(tool_input.get("file_path") or ""))
    if tool == "Bash":
        return bool(CHECKLIST_READ.search(tool_input.get("command") or ""))
    return False


def load(transcript_path):
    entries = []
    for line in Path(transcript_path).read_text(errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def blocks(entry):
    if entry.get("type") == "attachment":
        attachment = entry.get("attachment") or {}
        if attachment.get("type") == "queued_command":
            return [{"type": "text", "text": str(attachment.get("prompt") or "")}]
        return []
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return (
        [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []
    )


def _origin_kind(entry):
    holder = entry.get("attachment") if entry.get("type") == "attachment" else entry
    return ((holder or {}).get("origin") or {}).get("kind")


def _is_prompt(entry):
    """A user message or queued command, whoever sent it: not a tool result."""
    if entry.get("type") == "attachment":
        return bool(blocks(entry))
    return entry.get("type") == "user" and all(
        b.get("type") != "tool_result" for b in blocks(entry)
    )


def _is_human(entry, has_origin):
    if not _is_prompt(entry):
        return False
    if has_origin:
        return _origin_kind(entry) == "human"
    return entry.get("type") == "user" and not entry.get("isMeta")


def invokes_bcp(entry, has_origin):
    if entry.get("type") == "assistant":
        return any(
            b.get("type") == "tool_use" and runs_bcp(b.get("name"), b.get("input"))
            for b in blocks(entry)
        )
    return _is_human(entry, has_origin) and any(
        BCP_COMMAND in (b.get("text") or "") for b in blocks(entry)
    )


def has_origin(entries):
    return any(
        "origin" in e or "origin" in (e.get("attachment") or {}) for e in entries
    )


def human_window(entries, turns):
    """Index where the last `turns` human turns begin (0 when there are fewer)."""
    origin = has_origin(entries)
    humans = [i for i, e in enumerate(entries) if _is_human(e, origin)]
    return humans[-turns] if len(humans) >= turns else 0


def last_prompt(entries):
    """Index of the last prompt of any origin: where the current stop chain began."""
    prompts = [i for i, e in enumerate(entries) if _is_prompt(e)]
    return prompts[-1] if prompts else 0


def bcp_ran(entries, turns):
    """True when bcp ran within the last `turns` human turns."""
    origin = has_origin(entries)
    return any(invokes_bcp(e, origin) for e in entries[human_window(entries, turns) :])


def marker_path(transcript_path, agent_id=None):
    """The marker `bcp-mark.py` touches: one per session, or per subagent."""
    name = f"bcp-ran-{agent_id}" if agent_id else "bcp-ran"
    return Path(transcript_path).with_suffix("") / name


def marked_since_window(entries, turns, marker):
    """True when `marker` is no older than the message opening the last `turns` turns.

    With fewer turns, or an opening message carrying no timestamp, any marker counts.
    """
    try:
        mtime = marker.stat().st_mtime
    except OSError:
        return False
    origin = has_origin(entries)
    humans = [i for i, e in enumerate(entries) if _is_human(e, origin)]
    if len(humans) < turns:
        return True
    stamp = entries[humans[-turns]].get("timestamp")
    try:
        opened = datetime.fromisoformat(stamp).timestamp()
    except (TypeError, ValueError):
        return True
    return mtime >= opened
