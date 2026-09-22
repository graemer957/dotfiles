#!/usr/bin/env python3
"""Run ruff over every Python file an Edit/Write/Bash call touched.

PostToolUse: collects the .py paths the call named — file_path for Edit/Write,
any .py token in a Bash command, bare ones resolved against the command's
leading `cd <dir> &&` when it has one and the session cwd otherwise — and runs
`ruff check` and `ruff format --check` on each one that exists, returning
findings as additional context so the hand-back carries them. ruff's defaults
apply (no config file) and --no-cache keeps .ruff_cache directories out of the
trees it runs in. Reads and runs (cat, python3) of a Python file also trigger a
check; that is one redundant lint, cheaper than a missed one. Files inside a
team work tree (a git repo under TEAM_ROOT) are skipped until TEAM_SKIP_UNTIL,
then nudge a decision on linting team Python. A missing ruff binary blocks
until it is installed.
"""

import datetime
import json
import os
import re
import shutil
import subprocess
import sys

PY_TOKEN = re.compile(r"[\w./~-]+\.py\b")
CD_PREFIX = re.compile(r"^\s*cd\s+(?P<dir>[^\s;&|]+)\s*(?:&&|;)")

HOME = os.path.expanduser("~")
TEAM_ROOT = HOME + "/dev/work/"
TEAM_SKIP_UNTIL = datetime.date(2026, 12, 16)


def in_team_repo(path):
    top = subprocess.run(
        ["git", "-C", os.path.dirname(path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    return top.returncode == 0 and (top.stdout.strip() + "/").startswith(TEAM_ROOT)


def today():
    return datetime.datetime.now(datetime.UTC).date()


def findings(path):
    """ruff's lint findings plus a formatting finding, as report lines; a tool failure with no output surfaces as one."""
    out = []
    for args in (
        ["check", "--no-cache", "--output-format", "concise", "--quiet"],
        ["format", "--check", "--no-cache", "--quiet"],
    ):
        r = subprocess.run(
            ["ruff", *args, path], capture_output=True, text=True, check=False
        )
        if r.returncode == 0:
            continue
        lines = r.stdout.strip() or r.stderr.strip()
        if args[0] == "format" and r.returncode == 1:
            lines = f"{path}: would be reformatted by `ruff format`"
        out.append(lines)
    return out


def resolve_base(payload):
    """Directory bare paths resolve against: a Bash command's leading `cd <dir> &&`, else the session cwd."""
    base = payload.get("cwd") or os.getcwd()
    if payload.get("tool_name") == "Bash":
        m = CD_PREFIX.match(payload.get("tool_input", {}).get("command", ""))
        if m:
            base = os.path.join(base, os.path.expanduser(m["dir"].strip("'\"")))
    return base


def touched_paths(payload):
    """Existing, non-scratch .py files the call named, in first-seen order."""
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input", {})
    if tool in ("Edit", "Write"):
        candidates = [tool_input.get("file_path", "")]
    elif tool == "Bash":
        candidates = PY_TOKEN.findall(tool_input.get("command", ""))
    else:
        return []

    base = resolve_base(payload)
    paths = []
    for c in candidates:
        c = os.path.normpath(os.path.join(base, os.path.expanduser(c)))
        if c.startswith(("/tmp/", "/var/tmp/")):
            continue  # scratch files are not deliverables
        if c.endswith(".py") and os.path.isfile(c) and c not in paths:
            paths.append(c)
    return paths


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    paths = touched_paths(payload)
    team = [p for p in paths if in_team_repo(p)]
    personal = [p for p in paths if p not in team]

    notes = []
    if team and today() >= TEAM_SKIP_UNTIL:
        notes.append(
            f"ruff skips team repos until {TEAM_SKIP_UNTIL.isoformat()}, which has passed. "
            "Ask Graeme whether to start linting team Python or move the date."
        )

    if personal:
        if shutil.which("ruff") is None:
            block(
                "ruff is not installed. Stop and ask Graeme to install it (`cic ruff`), "
                "then re-run this check once he confirms."
            )
            return
        found = [line for p in personal for line in findings(p)]
        if found:
            notes.append(
                "ruff findings on Python this call touched:\n" + "\n".join(found)
            )

    if notes:
        emit("\n".join(notes))


def emit(text):
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": text,
                }
            }
        )
    )


def block(reason):
    print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    main()
