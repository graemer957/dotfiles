#!/usr/bin/env python3
"""Self-tests for rumdl-markdown-check.py.

Drives the hook's main() with synthetic PostToolUse payloads over fixture files
and checks what it reports. Team-repo cases stub head_version() with the
fixture's "committed" text, so no git repository or commit is needed.
Run: ./rumdl-markdown-check.test.py
"""

import importlib.util
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "hook", os.path.join(HERE, "rumdl-markdown-check.py")
)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

PASS = FAIL = 0


def run_hook(payload, head=None):
    """additionalContext text the hook emits for payload, or "" when silent; head stubs the committed text."""
    hook.head_version = (lambda path: head) if head is not None else (lambda path: None)
    sys.stdin = io.StringIO(json.dumps(payload))
    out = io.StringIO()
    with redirect_stdout(out):
        hook.main()
    text = out.getvalue().strip()
    return json.loads(text)["hookSpecificOutput"]["additionalContext"] if text else ""


def check(name, got, want):
    """want is a substring the output must contain, or "" for silence."""
    global PASS, FAIL
    ok = (got == "") if want == "" else (want in got)
    print(
        ("OK   " if ok else "FAIL ")
        + name
        + ("" if ok else f"  → got: {got or '<silent>'} | want: {want or '<silent>'}")
    )
    PASS, FAIL = PASS + ok, FAIL + (not ok)


def edit(path):
    return {"tool_name": "Edit", "tool_input": {"file_path": path}}


def bash(command, cwd):
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}


# Fixtures sit under $HOME, not /tmp, because the hook skips /tmp paths as scratch.
with tempfile.TemporaryDirectory(
    prefix=".rumdl-hook-test.", dir=os.path.expanduser("~")
) as root:
    personal = os.path.join(root, "bad.md")
    with open(personal, "w") as f:
        f.write("text\n- a\n")  # MD032 at line 2
    committed = "# T\n\ntext\n- a\n\nmore\n"  # MD032 at line 4
    team = os.path.join(root, "doc.md")
    with open(team, "w") as f:
        f.write(committed)

    check(
        "personal file: every finding", run_hook(edit(personal)), "bad.md:2:1: [MD032]"
    )
    check("team file: pre-existing is silent", run_hook(edit(team), head=committed), "")

    with open(team, "w") as f:
        f.write(
            "intro\n" + committed + "- c\n"
        )  # old finding shifts to line 5, new one at line 8
    got = run_hook(edit(team), head=committed)
    check("team file: new finding reported", got, "doc.md:8:1: [MD032]")
    check(
        "team file: shifted one stays quiet", "" if "doc.md:5:" not in got else got, ""
    )
    check(
        "team file: untracked reports all",
        run_hook(edit(team), head=""),
        "doc.md:5:1: [MD032]",
    )

    check(
        "bash: bare path via leading cd",
        run_hook(bash(f"cd {root} && cat bad.md", "/")),
        "bad.md:2:1: [MD032]",
    )
    check(
        "bash: bare path via session cwd",
        run_hook(bash("cat bad.md", root)),
        "bad.md:2:1: [MD032]",
    )
    check("bash: bare path absent from cwd", run_hook(bash("cat bad.md", "/")), "")

with tempfile.NamedTemporaryFile(
    "w", suffix=".md", dir="/tmp", delete=False
) as scratch:
    scratch.write("text\n- a\n")
try:
    check("scratch path skipped", run_hook(edit(scratch.name)), "")
finally:
    os.unlink(scratch.name)

print(f"passed={PASS} failed={FAIL}")
sys.exit(FAIL != 0)
