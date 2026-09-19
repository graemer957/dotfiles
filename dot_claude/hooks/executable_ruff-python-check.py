#!/usr/bin/env python3
"""Run ruff over the Python file an Edit/Write call touched.

PostToolUse: runs `ruff check` and `ruff format --check` on the file_path when
it is an existing .py file, returning findings as additional context so the
hand-back carries them. ruff's defaults apply (no config file) and --no-cache
keeps .ruff_cache directories out of the trees it runs in. Files inside a team
work tree (a git repo under TEAM_ROOT) are skipped until TEAM_SKIP_UNTIL, then
nudge a decision on linting team Python. A missing ruff binary blocks until it
is installed.
"""

import datetime
import json
import os
import shutil
import subprocess
import sys

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


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    if payload.get("tool_name") not in ("Edit", "Write"):
        return
    path = os.path.normpath(payload.get("tool_input", {}).get("file_path", ""))
    if not path.endswith(".py") or not os.path.isfile(path):
        return
    if path.startswith(("/tmp/", "/var/tmp/")):
        return  # scratch files are not deliverables

    if in_team_repo(path):
        if today() >= TEAM_SKIP_UNTIL:
            emit(
                f"ruff skips team repos until {TEAM_SKIP_UNTIL.isoformat()}, which has passed. "
                "Ask Graeme whether to start linting team Python or move the date."
            )
        return

    if shutil.which("ruff") is None:
        block(
            "ruff is not installed. Stop and ask Graeme to install it (`cic ruff`), "
            "then re-run this check once he confirms."
        )
        return

    found = findings(path)
    if found:
        emit("ruff findings on the Python file this call touched:\n" + "\n".join(found))


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
