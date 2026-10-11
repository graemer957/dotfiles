#!/usr/bin/env python3
"""Gate instruction-file edits on bcp having run in this turn or the last.

On an Edit/Write to an instruction file — a SKILL.md, a CLAUDE.md, anything
under a .claude/{skills,rules,hooks}/ directory, or their chezmoi sources
(dot_claude/...) — or a Bash command that both names such a path and carries a
mutating token (sed -i, redirection, tee, an interpreter, cp/mv/rm), checks the
session transcript for a bcp run (the skill loaded, or its authoring checklist
read) within the last two human turns (the turn that showed a draft and the one
that approved it), or, for a call from a subagent, anywhere in that subagent's
own transcript, since the hook payload carries the main session's. The marker
`bcp-mark.py` touches counts the same way, since the transcript can lag the
hook. Absent both, denies the call with instructions to read the checklist and
retry; present, stays silent.
Non-instruction paths always fall through, as does a Bash command that only
reads (cat/rg/sed -n) an instruction file, including one that redirects stderr
or discards output.

Bash is matched on the command text because its payload carries no file_path:
the path is whatever the command string names, so the same patterns run over
the string, anchored at a path boundary rather than a leading slash so relative
paths (`.claude/skills/x/SKILL.md`) match too. A false positive costs one
checklist read; a miss costs the audit — so the mutating-token net is broad.
A redirection or `tee` is judged by its target: it counts as a write only when
the target itself names an instruction path, or is a shell variable the command
string cannot resolve. `2>&1` and `/dev/null` are how a read command silences
noise, so counting them as writes would gate reading an instruction file as
well as editing one.

Running a script kept under a skills or hooks folder is not an edit, whichever
interpreter or shebang starts it: its text was audited when it was written, so
the command is judged with that run left out. Two things gate a run whatever
starts it: an argument naming an instruction path, since a script handed a
target writes it, and the script's own text naming one outside comments, since
such a script may write it unasked. The gate reads the script to tell; one it
cannot read, one fed a here-document, and a command the shell-word parser
rejects are judged on the command text alone.

Fail-open on a missing or unreadable transcript: the gate backstops recall,
and locking out every instruction edit on a harness quirk costs more than one
missed audit — the rule and memory layers still stand.
"""

import json
import os
import re
import shlex
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
    r"|\bpython[23]?\b|\bperl\b|\bruby\b"
    r"|\bnode\b|\bcp\b|\bmv\b|\brm\b|\bdd\b|\brsync\b"
    r"|\brumdl\s+(?:fmt\b|check\b.*--fix\b)"
    # Downloads write their target: `curl -o`/`--output`, `wget -O`/`--output-document`.
    r"|\bcurl\b.*\s(?:-[a-zA-Z]*o|--output)\b|\bwget\b.*\s(?:-[a-zA-Z]*O|--output-document)\b)"
)

# Writes judged by their target. `(?!>)` keeps `>>` from backtracking to a
# bare `>` and slipping the target check.
TARGETED_WRITE = re.compile(
    r"(?:>>?(?!>)|\btee\b(?:\s+-\S+)*)\s*(?!&\d|/dev/null\b)(\S+)"
)


INTERPRETERS = frozenset(
    ("python", "python2", "python3", "bash", "sh", "zsh", "fish", "nu")
    + ("node", "perl", "ruby")
)
# Interpreter flags that take no value and leave the next word the script.
PLAIN_FLAGS = frozenset({"-u", "-B", "-E", "-I", "-s", "-x"})
ASSIGNMENT = re.compile(r"^\w+=")
GATED_SCRIPT = re.compile(
    r"(?:^|/)(?:\.claude|dot_claude)/(?:skills|hooks)/.+(?<!\.md)$"
)
INSTRUCTION_LITERAL = re.compile(
    r"SKILL\.md|CLAUDE\.md|(?:\.claude|dot_claude)/(?:skills|rules|hooks)/"
)
SEPARATORS = frozenset(";|&()\n")


def writes_instruction_path(command):
    """True when a redirect or `tee` targets an instruction path, or a variable."""
    return any(
        "$" in target or any(p.search(target) for p in COMMAND_PATHS)
        for target in TARGETED_WRITE.findall(command)
    )


def segments(command):
    """The command's shell words, split at `;`, `&&`, `||`, `|`, newlines and parentheses."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";|&()<>\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    out, words = [], []
    for token in lexer:
        if set(token) <= SEPARATORS:
            out.append(words)
            words = []
        else:
            words.append(token)
    out.append(words)
    return [w for w in out if w]


def script_run(words):
    """(script, arguments) when the words run a script kept under a skills or hooks folder."""
    i = 0
    while i < len(words) and ASSIGNMENT.match(words[i]):
        i += 1
    if i < len(words) and os.path.basename(words[i]) in INTERPRETERS:
        i += 1
        while i < len(words) and words[i] in PLAIN_FLAGS:
            i += 1
    if i == len(words) or words[i].startswith("-"):
        return None
    if not GATED_SCRIPT.search(words[i]):
        return None
    return words[i], words[i + 1 :]


def names_instruction_file(script, cwd):
    """Whether the script's text names an instruction path outside comments; None if unreadable."""
    path = Path(os.path.expandvars(os.path.expanduser(script)))
    if not path.is_absolute():
        path = Path(cwd or ".") / path
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return None
    return any(
        INSTRUCTION_LITERAL.search(line)
        for line in lines
        if not line.lstrip().startswith(("#", "//"))
    )


def judge_script_runs(command, cwd):
    """(gated, rest): whether a script run must be gated, and the command without the harmless runs."""
    try:
        parts = segments(command)
    except ValueError:
        return False, command
    kept, dropped = [], False
    for words in parts:
        run = script_run(words)
        if not run or any(a.startswith("<<") for a in run[1]):
            kept.append(words)
            continue
        script, arguments = run
        if any(p.search(a) for a in arguments for p in COMMAND_PATHS):
            return True, command
        named = names_instruction_file(script, cwd)
        if named:
            return True, command
        if named is None:
            kept.append(words)
        else:
            dropped = True
    if not dropped:
        return False, command
    return False, " ; ".join(" ".join(words) for words in kept)


def bcp_seen(payload):
    """bcp in the last two human turns, or anywhere in the calling subagent's own run."""
    # Imported here so a missing module touches only instruction-path calls.
    from bcp_window import (
        bcp_ran,
        has_origin,
        invokes_bcp,
        load,
        marked_since_window,
        marker_path,
    )

    transcript = payload.get("transcript_path") or ""
    agent_id = payload.get("agent_id")
    if agent_id:
        if marker_path(transcript, agent_id).exists():
            return True
        own = Path(transcript).with_suffix("") / "subagents" / f"agent-{agent_id}.jsonl"
        try:
            entries = load(own)
        except OSError:
            entries = []
        if any(invokes_bcp(e, has_origin(entries)) for e in entries):
            return True
    entries = load(transcript)
    return bcp_ran(entries, 2) or marked_since_window(
        entries, 2, marker_path(transcript)
    )


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    if not isinstance(payload, dict):
        return

    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input", {})
    if tool in ("Edit", "Write"):
        if not any(
            p.search(tool_input.get("file_path", "")) for p in INSTRUCTION_PATHS
        ):
            return
    elif tool == "Bash":
        command = tool_input.get("command", "")
        if not any(p.search(command) for p in COMMAND_PATHS):
            return
        gated, command = judge_script_runs(command, payload.get("cwd"))
        if not gated:
            if not any(p.search(command) for p in COMMAND_PATHS):
                return
            if not (MUTATING.search(command) or writes_instruction_path(command)):
                return
    else:
        return

    try:
        if bcp_seen(payload):
            return
    except OSError:
        return

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "Instruction-file gate: this edit targets a skill/CLAUDE.md/rule/hook, "
                        "and the bcp authoring checklist, which instruction files are checked "
                        "against, has not been in front of you in this turn or the last. "
                        "Read the bcp skill's authoring.md (invoke Skill(bcp) first if "
                        "the skill has not loaded this session), apply its checklist to the change "
                        "(and to any draft already shared in chat), then retry this exact edit."
                    ),
                }
            }
        )
    )


if __name__ == "__main__":
    main()
