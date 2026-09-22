#!/usr/bin/env python3
"""Self-tests for shellcheck-shell-check.py.

Drives the hook's main() with synthetic PostToolUse payloads over fixture
scripts and checks what it reports. Team-repo cases stub head_version(), so no
git repository is needed.
Run: ./shellcheck-shell-check.test.py
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
    "hook", os.path.join(HERE, "shellcheck-shell-check.py")
)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

PASS = FAIL = 0


def run_hook(payload, head=None):
    """Block reason or additionalContext text the hook emits for payload, or "" when silent; head stubs the committed text of a team file."""
    hook.head_version = lambda path: head
    sys.stdin = io.StringIO(json.dumps(payload))
    out = io.StringIO()
    with redirect_stdout(out):
        hook.main()
    text = out.getvalue().strip()
    if not text:
        return ""
    emitted = json.loads(text)
    return emitted.get("reason") or emitted["hookSpecificOutput"]["additionalContext"]


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


def edit(path, tool="Edit"):
    return {"tool_name": tool, "tool_input": {"file_path": path}}


def bash(command, cwd=None):
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}


def fixture(root, name, text):
    path = os.path.join(root, name)
    with open(path, "w") as f:
        f.write(text)
    return path


UNQUOTED = '#!/bin/bash\nx="a b"\necho $x\n'

# Fixtures sit under $HOME, not /tmp, because the hook skips /tmp paths as scratch.
with tempfile.TemporaryDirectory(
    prefix=".shellcheck-hook-test.", dir=os.path.expanduser("~")
) as root:
    clean = fixture(root, "clean.sh", '#!/bin/bash\necho "ok"\n')
    unquoted = fixture(root, "unquoted.sh", UNQUOTED)
    dot_bash = fixture(root, "lib.bash", UNQUOTED)
    notes = fixture(root, "notes.md", "echo $x\n")
    grown = fixture(root, "grown.sh", UNQUOTED + 'y="c d"\necho $y\n')

    check("clean script is silent", run_hook(edit(clean)), "")
    check("finding reported", run_hook(edit(unquoted)), "SC2086")
    check("Write is checked too", run_hook(edit(unquoted, "Write")), "SC2086")
    check(".bash extension is checked", run_hook(edit(dot_bash)), "SC2086")
    check("non-shell file ignored", run_hook(edit(notes)), "")

    check(
        "Bash naming the file is checked", run_hook(bash(f"bash {unquoted}")), "SC2086"
    )
    check(
        "bare path resolves against the session cwd",
        run_hook(bash("cat unquoted.sh", cwd=root)),
        "SC2086",
    )
    check(
        "bare path resolves against a leading cd",
        run_hook(bash(f"cd {root} && cat unquoted.sh", cwd=os.path.expanduser("~"))),
        "SC2086",
    )
    check(
        "Bash naming a missing file is silent",
        run_hook(bash(f"cat {root}/nope.sh")),
        "",
    )
    check("Bash with no script token is silent", run_hook(bash(f"ls {root}")), "")

    team = run_hook(edit(grown), head=UNQUOTED)
    check("team file: finding the edit adds is reported", team, f"{grown}:5:")
    check(
        "team file: pre-existing finding is suppressed",
        "" if f"{grown}:3:" not in team else team,
        "",
    )
    check(
        "team file unchanged over HEAD is silent",
        run_hook(edit(unquoted), head=UNQUOTED),
        "",
    )
    check(
        "untracked team file reports everything",
        run_hook(edit(unquoted), head=""),
        "SC2086",
    )

    which = hook.shutil.which
    hook.shutil.which = lambda name: None
    try:
        check("missing shellcheck blocks", run_hook(edit(clean)), "not installed")
    finally:
        hook.shutil.which = which

with tempfile.NamedTemporaryFile(
    "w", suffix=".sh", dir="/tmp", delete=False
) as scratch:
    scratch.write(UNQUOTED)
try:
    check("scratch path skipped", run_hook(edit(scratch.name)), "")
    check("scratch path skipped via Bash", run_hook(bash(f"cat {scratch.name}")), "")
finally:
    os.unlink(scratch.name)

print(f"passed={PASS} failed={FAIL}")
sys.exit(FAIL != 0)
