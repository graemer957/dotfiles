#!/usr/bin/env python3
"""Run rumdl over every Markdown file an Edit/Write/Bash call touched.

PostToolUse: collects the .md paths the call named — file_path for Edit/Write,
any .md token in a Bash command — and runs `rumdl check` on each one that
exists, with the disable list DISABLES maps its path to, returning findings as
additional context so the hand-back carries them. Reads (cat, rg) of a
Markdown file also trigger a check; that is one redundant lint, cheaper than a
missed one. A missing rumdl binary is reported, never skipped, matching the
markdown rule.
"""

import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys

MD_TOKEN = re.compile(r"[\w./~-]+\.md\b")

HOME = os.path.expanduser("~")

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

    paths = []
    for c in candidates:
        c = os.path.expanduser(c)
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
        r = subprocess.run(["rumdl", "check", "-d", disables_for(p), p], capture_output=True, text=True)
        if r.returncode != 0:
            findings.append(r.stdout.strip() or r.stderr.strip())
    if findings:
        emit("rumdl findings on Markdown this call touched (fix what the edit introduced, flag the rest):\n" + "\n".join(findings))


def emit(text):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": text,
        }
    }))


if __name__ == "__main__":
    main()
