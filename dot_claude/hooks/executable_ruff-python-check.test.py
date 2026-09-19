#!/usr/bin/env python3
"""Self-tests for ruff-python-check.py.

Drives the hook's main() with synthetic PostToolUse payloads over fixture files
and checks what it reports. Team-repo cases stub in_team_repo() and today(), so
no git repository or clock change is needed.
Run: ./ruff-python-check.test.py
"""

import datetime
import importlib.util
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "hook", os.path.join(HERE, "ruff-python-check.py")
)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

PASS = FAIL = 0
BEFORE = hook.TEAM_SKIP_UNTIL - datetime.timedelta(days=1)


def run_hook(payload, team=False, today=BEFORE):
    """Block reason or additionalContext text the hook emits for payload, or "" when silent."""
    hook.in_team_repo = lambda path: team
    hook.today = lambda: today
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


def fixture(root, name, text):
    path = os.path.join(root, name)
    with open(path, "w") as f:
        f.write(text)
    return path


# Fixtures sit under $HOME, not /tmp, because the hook skips /tmp paths as scratch.
with tempfile.TemporaryDirectory(
    prefix=".ruff-hook-test.", dir=os.path.expanduser("~")
) as root:
    clean = fixture(root, "clean.py", 'print("ok")\n')
    unused = fixture(root, "unused.py", 'import os\n\nprint("ok")\n')
    messy = fixture(root, "messy.py", "print( 'ok' )\n")
    notes = fixture(root, "notes.md", "import os\n")

    check("clean file is silent", run_hook(edit(clean)), "")
    check("lint finding reported", run_hook(edit(unused)), "F401")
    check("format finding reported", run_hook(edit(messy)), "would be reformatted")
    check("Write is checked too", run_hook(edit(unused, "Write")), "F401")
    check("non-Python file ignored", run_hook(edit(notes)), "")
    check("Bash call ignored", run_hook(edit(unused, "Bash")), "")

    check("team file skipped before date", run_hook(edit(unused), team=True), "")
    check(
        "team file nudges once date passes",
        run_hook(edit(unused), team=True, today=hook.TEAM_SKIP_UNTIL),
        "start linting team Python",
    )

    which = hook.shutil.which
    hook.shutil.which = lambda name: None
    try:
        check("missing ruff blocks", run_hook(edit(clean)), "cic ruff")
    finally:
        hook.shutil.which = which

    check(
        "no cache left behind",
        "" if not os.path.exists(os.path.join(root, ".ruff_cache")) else "cache",
        "",
    )

with tempfile.NamedTemporaryFile(
    "w", suffix=".py", dir="/tmp", delete=False
) as scratch:
    scratch.write("import os\n")
try:
    check("scratch path skipped", run_hook(edit(scratch.name)), "")
finally:
    os.unlink(scratch.name)

print(f"passed={PASS} failed={FAIL}")
sys.exit(FAIL != 0)
