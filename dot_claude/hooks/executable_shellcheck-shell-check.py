#!/usr/bin/env python3
"""Run shellcheck over every shell script an Edit/Write/Bash call touched.

PostToolUse: collects the .sh/.bash paths the call named — file_path for
Edit/Write, any such token in a Bash command, bare ones resolved against the
command's leading `cd <dir> &&` when it has one and the session cwd otherwise —
and runs `shellcheck` on each one that exists, returning findings as additional
context so the hand-back carries them. A file inside a team work tree (a git
repo under TEAM_ROOT) reports only findings the working copy adds over HEAD,
keyed on rule + line text so shifted line numbers don't read as new;
pre-existing findings there are the team's, not the session's. Reads and runs
(cat, bash) of a script also trigger a check; that is one redundant lint,
cheaper than a missed one. A missing shellcheck binary blocks until it is
installed.
"""

import collections
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

SH_TOKEN = re.compile(r"[\w./~-]+\.(?:sh|bash)\b")
CD_PREFIX = re.compile(r"^\s*cd\s+(?P<dir>[^\s;&|]+)\s*(?:&&|;)")
FINDING = re.compile(
    r"^.*?:(?P<line>\d+):(?P<col>\d+): (?P<level>\w+): (?P<msg>.*) \[(?P<rule>SC\d+)\]$"
)

HOME = os.path.expanduser("~")
TEAM_ROOT = HOME + "/dev/work/"


def run_check(path):
    """shellcheck's findings for path as (line, col, rule, message); a tool failure with no findings surfaces as one."""
    r = subprocess.run(
        ["shellcheck", "-f", "gcc", path],
        capture_output=True,
        text=True,
        check=False,
    )
    out = [
        (int(m["line"]), m["col"], m["rule"], f"{m['level']}: {m['msg']}")
        for m in (FINDING.match(l) for l in r.stdout.splitlines())
        if m
    ]
    if r.returncode not in (0, 1) and not out:
        out.append((0, "0", "SHELLCHECK", (r.stderr or r.stdout).strip()))
    return out


def head_version(path):
    """Committed text of a team-repo file: None outside a team work tree, "" when untracked."""
    d = os.path.dirname(path)
    top = subprocess.run(
        ["git", "-C", d, "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if top.returncode != 0 or not (top.stdout.strip() + "/").startswith(TEAM_ROOT):
        return None
    rel = os.path.relpath(path, top.stdout.strip())
    shown = subprocess.run(
        ["git", "-C", d, "show", "HEAD:" + rel],
        capture_output=True,
        text=True,
        check=False,
    )
    return shown.stdout if shown.returncode == 0 else ""


def new_findings(path):
    """Findings to report: everything for a personal file; for a team-repo file, only those the working copy adds over HEAD."""
    current = run_check(path)
    head = head_version(path)
    if head is None:
        return current
    with tempfile.TemporaryDirectory() as td:
        tmp = os.path.join(td, os.path.basename(path))
        with open(tmp, "w") as f:
            f.write(head)
        baseline = run_check(tmp)
    head_lines = head.splitlines()
    with open(path) as f:
        cur_lines = f.read().splitlines()

    def key(finding, lines):
        line, _, rule, _ = finding
        return (rule, lines[line - 1].strip() if 0 < line <= len(lines) else "")

    seen = collections.Counter(key(f, head_lines) for f in baseline)
    fresh = []
    for f in current:
        k = key(f, cur_lines)
        if seen[k]:
            seen[k] -= 1
        else:
            fresh.append(f)
    return fresh


def resolve_base(payload):
    """Directory bare paths resolve against: a Bash command's leading `cd <dir> &&`, else the session cwd."""
    base = payload.get("cwd") or os.getcwd()
    if payload.get("tool_name") == "Bash":
        m = CD_PREFIX.match(payload.get("tool_input", {}).get("command", ""))
        if m:
            base = os.path.join(base, os.path.expanduser(m["dir"].strip("'\"")))
    return base


def touched_paths(payload):
    """Existing, non-scratch shell scripts the call named, in first-seen order."""
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input", {})
    if tool in ("Edit", "Write"):
        candidates = [tool_input.get("file_path", "")]
    elif tool == "Bash":
        candidates = SH_TOKEN.findall(tool_input.get("command", ""))
    else:
        return []

    base = resolve_base(payload)
    paths = []
    for c in candidates:
        c = os.path.normpath(os.path.join(base, os.path.expanduser(c)))
        if c.startswith(("/tmp/", "/var/tmp/")):
            continue  # scratch scripts are not deliverables
        if c.endswith((".sh", ".bash")) and os.path.isfile(c) and c not in paths:
            paths.append(c)
    return paths


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    paths = touched_paths(payload)
    if not paths:
        return

    if shutil.which("shellcheck") is None:
        block(
            "shellcheck is not installed. Stop and ask Graeme to install it, "
            "then re-run this check once he confirms."
        )
        return

    findings = []
    for p in paths:
        for line, col, rule, msg in new_findings(p):
            findings.append(f"{p}:{line}:{col}: [{rule}] {msg}")
    if findings:
        emit(
            "shellcheck findings on shell scripts this call touched (team-repo files list only what the working copy adds over HEAD):\n"
            + "\n".join(findings)
        )


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
