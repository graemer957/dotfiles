#!/usr/bin/env python3
"""Self-tests for hook-homes-check.py.

Drives the hook's main() with synthetic PostToolUse payloads over fixture
settings files, pointing FILES and SHARED_HOOKS at a temporary layout so no
real settings are read.
Run: ./hook-homes-check.test.py
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
    "hook", os.path.join(HERE, "hook-homes-check.py")
)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

PASS = FAIL = 0


def run_hook(payload):
    """additionalContext text the hook emits for payload, or "" when silent."""
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


def bash(command):
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def registration(*commands):
    return {
        "PostToolUse": [
            {"matcher": "Edit", "hooks": [{"type": "command", "command": c}]}
            for c in commands
        ]
    }


def write(path, settings):
    with open(path, "w") as f:
        json.dump(settings, f)


NAMES = edit("/x/.claude/settings.json")

with tempfile.TemporaryDirectory(prefix="hook-homes-test.") as root:
    personal = os.path.join(root, "personal.json")
    work = os.path.join(root, "work.json")
    shared = os.path.join(root, "shared.json")
    missing = os.path.join(root, "missing.json")
    hook.SHARED_HOOKS = os.path.join(root, "hooks") + "/"
    hook.FILES = {"personal": [personal], "work": [work], "shared": [shared]}
    every = hook.SHARED_HOOKS + "every.py"
    work_only = os.path.join(root, "work-hooks", "only.py")

    def layout(p=None, w=None, s=None):
        write(personal, p or {})
        write(work, w or {})
        write(shared, s or {"hooks": registration(every)})

    layout(w={"hooks": registration(work_only)})
    check("clean layout is silent", run_hook(NAMES), "")

    layout(w={"hooks": registration(work_only, every)})
    got = run_hook(NAMES)
    check(
        "shared-directory hook in a profile file", got, "belong in the shared fragment"
    )
    check("same command in two files", got, "one registration in the shared fragment")

    layout(p={"hooks": registration(work_only)}, w={"hooks": registration(work_only)})
    check(
        "profile-only script in both profile files",
        run_hook(NAMES),
        "one registration in the shared fragment",
    )

    layout(s={"hooks": registration(every), "model": "opus"})
    check("scalar key in the fragment", run_hook(NAMES), "pins that value")

    layout(s={"hooks": registration(every), "//": "note", "$schema": "x"})
    check("fragment note and schema keys allowed", run_hook(NAMES), "")

    layout(w={"hooks": registration(every)})
    check(
        "Edit elsewhere is silent despite a finding",
        run_hook(edit("/x/notes.md")),
        "",
    )
    check(
        "Bash naming a settings file reports",
        run_hook(bash("cat ~/.claude/settings-shared-hooks.json")),
        "belong in the shared fragment",
    )
    check(
        "chezmoi source path also triggers",
        run_hook(edit("/h/.local/share/chezmoi/dot_claude/settings.json")),
        "belong in the shared fragment",
    )
    check("Bash without a settings path is silent", run_hook(bash("ls")), "")

    hook.FILES = {"personal": [personal], "work": [missing, work], "shared": [shared]}
    check(
        "missing first candidate falls through to the next",
        run_hook(NAMES),
        "belong in the shared fragment",
    )
    hook.FILES = {"personal": [personal], "work": [work], "shared": [shared]}

    with open(work, "w") as f:
        f.write("{ not json")
    check("unparseable file is skipped", run_hook(NAMES), "")

print(f"passed={PASS} failed={FAIL}")
sys.exit(FAIL != 0)
