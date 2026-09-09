#!/usr/bin/env python3
"""Run rumdl over every Markdown file an Edit/Write/Bash call touched.

PostToolUse: collects the .md paths the call named — file_path for Edit/Write,
any .md token in a Bash command, bare ones resolved against the command's
leading `cd <dir> &&` when it has one and the session cwd otherwise — and runs
`rumdl check` on each one that exists, with the disable list DISABLES maps its
path to, returning findings as additional context so the hand-back carries
them. A file inside a team work tree (a git repo under TEAM_ROOT) reports only
findings the working copy adds over HEAD, keyed on rule + line text so shifted
line numbers don't read as new; pre-existing findings there are the team's, not
the session's. Reads (cat, rg) of a Markdown file also trigger a check; that is
one redundant lint, cheaper than a missed one. A missing rumdl binary is
reported, never skipped, matching the markdown rule.
"""

import collections
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

MD_TOKEN = re.compile(r"[\w./~-]+\.md\b")
CD_PREFIX = re.compile(r"^\s*cd\s+(?P<dir>[^\s;&|]+)\s*(?:&&|;)")
FINDING = re.compile(r"^.*?:(?P<line>\d+):(?P<col>\d+): \[(?P<rule>MD\d+)\] (?P<msg>.*)$")

HOME = os.path.expanduser("~")
TEAM_ROOT = HOME + "/dev/work/"

# Per-path disable lists — first match wins; ~/.claude/rules/markdown.md defers
# here. MD013 is off everywhere: soft wrapping is the convention, viewers
# handle line length. fnmatch's * crosses /, so patterns match at any depth.
DISABLES = [
    # memory index: no H1; band headings sit flush against their lists — deliberate density
    ("*/.claude/projects/*/memory/MEMORY.md", "MD013,MD022,MD032,MD041"),
    # memory topic files: YAML frontmatter, no H1
    ("*/.claude/projects/*/memory/*.md", "MD013,MD041"),
    # Obsidian vault notes: H1 section headings; lists flush under headings
    (HOME + "/Documents/Obsidian/*.md", "MD013,MD025,MD032"),
]
DEFAULT_DISABLE = "MD013"


def disables_for(path):
    for pattern, rules in DISABLES:
        if fnmatch.fnmatch(path, pattern):
            return rules
    return DEFAULT_DISABLE


def run_check(path, disables):
    """rumdl's findings for path as (line, col, rule, message); a tool failure with no findings surfaces as one."""
    r = subprocess.run(["rumdl", "check", "-d", disables, path], capture_output=True, text=True)
    out = [(int(m["line"]), m["col"], m["rule"], m["msg"])
           for m in (FINDING.match(l) for l in r.stdout.splitlines()) if m]
    if r.returncode != 0 and not out and r.stderr.strip():
        out.append((0, "0", "RUMDL", r.stderr.strip()))
    return out


def head_version(path):
    """Committed text of a team-repo file: None outside a team work tree, "" when untracked."""
    d = os.path.dirname(path)
    top = subprocess.run(["git", "-C", d, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode != 0 or not (top.stdout.strip() + "/").startswith(TEAM_ROOT):
        return None
    rel = os.path.relpath(path, top.stdout.strip())
    shown = subprocess.run(["git", "-C", d, "show", "HEAD:" + rel], capture_output=True, text=True)
    return shown.stdout if shown.returncode == 0 else ""


def new_findings(path, disables):
    """Findings to report: everything for a personal file; for a team-repo file, only those the working copy adds over HEAD."""
    current = run_check(path, disables)
    head = head_version(path)
    if head is None:
        return current
    with tempfile.TemporaryDirectory() as td:
        tmp = os.path.join(td, os.path.basename(path))
        with open(tmp, "w") as f:
            f.write(head)
        baseline = run_check(tmp, disables)
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


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input", {})
    if tool in ("Edit", "Write"):
        candidates = [tool_input.get("file_path", "")]
    elif tool == "Bash":
        candidates = MD_TOKEN.findall(tool_input.get("command", ""))
    else:
        return

    base = resolve_base(payload)
    paths = []
    for c in candidates:
        c = os.path.normpath(os.path.join(base, os.path.expanduser(c)))
        if c.startswith(("/tmp/", "/var/tmp/")):
            continue  # scratch drafts (PR bodies, notes) are not deliverables
        if c.endswith(".md") and os.path.isfile(c) and c not in paths:
            paths.append(c)
    if not paths:
        return

    if shutil.which("rumdl") is None:
        emit("rumdl is not installed; the markdown rule requires it — report this at hand-back, don't skip it.")
        return

    findings = []
    for p in paths:
        for line, col, rule, msg in new_findings(p, disables_for(p)):
            findings.append(f"{p}:{line}:{col}: [{rule}] {msg}")
    if findings:
        emit("rumdl findings on Markdown this call touched (team-repo files list only what the working copy adds over HEAD):\n" + "\n".join(findings))


def emit(text):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": text,
        }
    }))


if __name__ == "__main__":
    main()
