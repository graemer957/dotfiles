#!/usr/bin/env python3
"""Run rumdl over every Markdown file an Edit/Write/Bash call touched.

PostToolUse: collects the .md paths the call named — file_path for Edit/Write,
any .md token in a Bash command — and runs `rumdl check -d MD013` on each one
that exists, returning findings as additional context so the hand-back carries
them. Reads (cat, rg) of a Markdown file also trigger a check; that is one
redundant lint, cheaper than a missed one. A missing rumdl binary is reported,
never skipped, matching the markdown rule.
"""

import json
import os
import re
import shutil
import subprocess
import sys

MD_TOKEN = re.compile(r"[\w./~-]+\.md\b")


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
        r = subprocess.run(["rumdl", "check", "-d", "MD013", p], capture_output=True, text=True)
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
