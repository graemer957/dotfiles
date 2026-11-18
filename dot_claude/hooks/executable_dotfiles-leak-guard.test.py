#!/usr/bin/env python3
"""Self-tests for dotfiles-leak-guard.py.

Drives the hook's main() with synthetic PreToolUse payloads against a fixture
home in a temporary directory: a fake chezmoi source, a fake ~/.claude, a
private tree, and a terms list of made-up words, so no real term appears here.
`source_path` is stubbed to map the fixture's live files onto the fake source.
Run: ./dotfiles-leak-guard.test.py
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
    "hook", os.path.join(HERE, "dotfiles-leak-guard.py")
)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

PASS = FAIL = 0
TMP = os.path.realpath(tempfile.mkdtemp())
HOME = TMP + "/home"
SOURCE = HOME + "/.local/share/chezmoi"
CLAUDE = HOME + "/.claude"
PRIVATE = HOME + "/dev/work/.claude"
TERMS = TMP + "/terms.txt"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


write(TERMS, "# fixture\n\n(?i)\\bacme\\b\n\\bZED-\\d+\\b\n\\bZanzibar\\b\n")
write(SOURCE + "/dot_claude/CLAUDE.md", "Rules mention acme once.\n")
write(CLAUDE + "/CLAUDE.md", "Rules mention acme once.\n")
write(SOURCE + "/dot_claude/skills/pub/SKILL.md", "Public skill.\n")
write(CLAUDE + "/skills/pub/SKILL.md", "Public skill.\n")
write(HOME + "/.config/app/managed.conf", "x\n")
write(HOME + "/.config/app/unmanaged.conf", "x\n")
write(PRIVATE + "/CLAUDE.md", "Private.\n")
write(TMP + "/msg.txt", "Fix the ZED-12 bug\n")
write(TMP + "/clean-msg.txt", "Fix a bug\n")
os.makedirs(PRIVATE + "/skills", exist_ok=True)
os.symlink(CLAUDE + "/skills/pub", PRIVATE + "/skills/pub")

LIVE_TO_SOURCE = {
    CLAUDE + "/CLAUDE.md": SOURCE + "/dot_claude/CLAUDE.md",
    CLAUDE + "/skills/pub/SKILL.md": SOURCE + "/dot_claude/skills/pub/SKILL.md",
    HOME + "/.config/app/managed.conf": SOURCE + "/dot_config/app/managed.conf",
}

hook.HOME = HOME
hook.SOURCE = SOURCE
hook.CLAUDE_HOME = CLAUDE
hook.UNMANAGED_ROOTS = (HOME + "/dev/", HOME + "/Documents/", CLAUDE + "/projects/")
hook.source_path = LIVE_TO_SOURCE.get
os.environ["DOTFILES_LEAK_TERMS"] = TERMS
os.environ["HOME"] = HOME


def run_hook(payload):
    """The deny reason the hook emits for payload, or "" when silent."""
    sys.stdin = io.StringIO(json.dumps(payload))
    out = io.StringIO()
    with redirect_stdout(out):
        hook.main()
    text = out.getvalue().strip()
    if not text:
        return ""
    return json.loads(text)["hookSpecificOutput"]["permissionDecisionReason"]


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


def edit(path, old, new):
    return {
        "tool_name": "Edit",
        "tool_input": {"file_path": path, "old_string": old, "new_string": new},
    }


def write_call(path, content):
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


def bash(command, cwd=TMP):
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}


# Edit / Write
check(
    "edit to the source adding a term",
    run_hook(edit(SOURCE + "/dot_claude/CLAUDE.md", "once", "once, and Zanzibar")),
    "`Zanzibar`",
)
check(
    "edit keeping a term the old text already had",
    run_hook(edit(SOURCE + "/dot_claude/CLAUDE.md", "acme once", "acme twice")),
    "",
)
check(
    "case-insensitive term",
    run_hook(edit(SOURCE + "/dot_claude/CLAUDE.md", "once", "once, ACME too")),
    "`ACME`",
)
check(
    "ticket pattern",
    run_hook(edit(CLAUDE + "/skills/pub/SKILL.md", "Public", "Public (ZED-4411)")),
    "`ZED-4411`",
)
check(
    "built-in notes-vault term",
    run_hook(edit(SOURCE + "/dot_claude/CLAUDE.md", "once", "once, see Obsidian")),
    "`Obsidian`",
)
check(
    "edit to the private tree",
    run_hook(edit(PRIVATE + "/CLAUDE.md", "Private", "Private Zanzibar")),
    "",
)
check(
    "edit through a symlink into a public skill",
    run_hook(edit(PRIVATE + "/skills/pub/SKILL.md", "Public", "Public Zanzibar")),
    "`Zanzibar`",
)
check(
    "edit to a managed live file outside ~/.claude",
    run_hook(edit(HOME + "/.config/app/managed.conf", "x", "Zanzibar")),
    "`Zanzibar`",
)
check(
    "edit to an unmanaged live file",
    run_hook(edit(HOME + "/.config/app/unmanaged.conf", "x", "Zanzibar")),
    "",
)
check(
    "new file under ~/.claude/skills waiting for chezmoi add",
    run_hook(write_call(CLAUDE + "/skills/new/SKILL.md", "Ask Zanzibar.")),
    "`Zanzibar`",
)
check(
    "write keeping the existing count",
    run_hook(write_call(SOURCE + "/dot_claude/CLAUDE.md", "Rewritten, acme once.\n")),
    "",
)
check(
    "write adding a second mention",
    run_hook(write_call(SOURCE + "/dot_claude/CLAUDE.md", "acme and acme\n")),
    "`acme`",
)
check(
    "write outside the home directory",
    run_hook(write_call("/var/tmp/scratch.md", "Zanzibar")),
    "",
)
check(
    "the hook's own files are exempt",
    run_hook(
        edit(
            SOURCE + "/dot_claude/hooks/executable_dotfiles-leak-guard.py",
            "a",
            "Obsidian",
        )
    ),
    "",
)

# Bash
check(
    "sed -i writing a term into the source",
    run_hook(bash(f"sed -i 's/once/Zanzibar/' {SOURCE}/dot_claude/CLAUDE.md")),
    "`Zanzibar`",
)
check(
    "read-only search of the source for a term",
    run_hook(bash(f"rg -n 'Zanzibar|ZED-1' {SOURCE}/dot_claude 2>&1")),
    "",
)
check(
    "commit message file carrying a term, run from the source",
    run_hook(bash(f"git commit -F {TMP}/msg.txt", cwd=SOURCE)),
    "`ZED-12`",
)
check(
    "clean commit message file",
    run_hook(bash(f"git commit -F {TMP}/clean-msg.txt", cwd=SOURCE)),
    "",
)
check(
    "commit subject passed on the command line",
    run_hook(bash(f'{CLAUDE}/skills/chezmoi-commits/commit.sh "Note acme setup"')),
    "`acme`",
)
check(
    "write outside any guarded path",
    run_hook(bash(f"echo Zanzibar > {PRIVATE}/notes.md")),
    "",
)
write(CLAUDE + "/skills/pub/SKILL.md", "Public skill for Zanzibar.\n")
check(
    "chezmoi add of a live file adding a term",
    run_hook(bash(f"chezmoi add {CLAUDE}/skills/pub/SKILL.md")),
    "`Zanzibar`",
)
check(
    "chezmoi add of a live file whose terms the source already has",
    run_hook(bash(f"chezmoi add {CLAUDE}/CLAUDE.md")),
    "",
)
check(
    "chezmoi add of a directory",
    run_hook(bash(f"chezmoi add {CLAUDE}/skills/pub")),
    "`Zanzibar`",
)

# Terms list
os.environ["DOTFILES_LEAK_TERMS"] = TMP + "/missing.txt"
check(
    "missing list keeps the built-in",
    run_hook(edit(SOURCE + "/dot_claude/CLAUDE.md", "once", "once, Obsidian")),
    "`Obsidian`",
)
check(
    "missing list drops the private terms",
    run_hook(edit(SOURCE + "/dot_claude/CLAUDE.md", "once", "once, Zanzibar")),
    "",
)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
