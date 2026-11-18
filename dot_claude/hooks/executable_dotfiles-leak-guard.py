#!/usr/bin/env python3
"""Block private references from entering the public dotfiles.

The chezmoi source is published as a public GitHub repository, so anything
written into it, or into a live file chezmoi manages or will be asked to add,
is published on the next push. This PreToolUse hook denies a call that would
add a private term there: the employer, colleagues, customers, ticket IDs or
the private notes vault.

Terms come from a private list outside the public tree (TERMS_FILE, or the
path in $DOTFILES_LEAK_TERMS), one Python regex per line, so the list itself
never ships; NOTES_VAULT is the one built-in. A missing list leaves only the
built-in, since a machine without the work tree holds none of its terms.

A guarded path is the chezmoi source, a live file chezmoi manages, or a file
under ~/.claude's authored directories (where new files wait for `chezmoi
add`), judged after resolving symlinks. Only added text counts: a term already
in the file does not block an edit that keeps it, so an edit beside an existing
mention goes through.

- Edit/MultiEdit/Write: a term counted more often in the new text than in the
  text it replaces.
- Bash naming a guarded path (or run from inside the source) with a write
  token: a term in the command text, or in any non-guarded file it names
  (a commit message file, a copy source). `chezmoi add`: a term counted more
  often in each named live file than in its source copy.

The hook's own files are exempt, since they must name the built-in pattern.
"""

import json
import os
import re
import shlex
import subprocess
import sys

HOME = os.path.expanduser("~")
SOURCE = os.path.realpath(HOME + "/.local/share/chezmoi")
CLAUDE_HOME = HOME + "/.claude"
AUTHORED = ("skills", "hooks", "rules", "commands", "agents")
UNMANAGED_ROOTS = (HOME + "/dev/", HOME + "/Documents/", CLAUDE_HOME + "/projects/")
TERMS_FILE = HOME + "/dev/work/.claude/hooks/dotfiles-private-terms.txt"
NOTES_VAULT = re.compile(r"(?i)\bobsidian\b")
SELF = re.compile(r"(?:^|/)(?:executable_)?dotfiles-leak-guard(?:\.test)?\.py$")
MAX_READ = 1 << 20

WRITE_TOKEN = re.compile(
    r"sed\s+(?:-[a-zA-Z]*i|--in-place)|\bperl\s+-[a-zA-Z]*i|\btee\b"
    r"|(?<![0-9&])>>?(?!\s*(?:&|/dev/null))|<<"
    r"|\b(?:cp|mv|rsync|install|ln|python3?|perl|ruby|node|commit)\b"
    r"|commit\.sh|\bchezmoi\s+(?:re-)?add\b"
)
CHEZMOI_ADD = re.compile(r"\bchezmoi\s+add\b(.*?)(?:$|[;&|\n])")


def load_patterns():
    patterns = [NOTES_VAULT]
    path = os.environ.get("DOTFILES_LEAK_TERMS", TERMS_FILE)
    for line in read(path).splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(re.compile(line))
    return patterns


def read(path):
    try:
        if os.path.isfile(path) and os.path.getsize(path) <= MAX_READ:
            with open(path, encoding="utf-8", errors="ignore") as f:
                return f.read()
    except OSError:
        pass
    return ""


def source_path(real):
    """The chezmoi source file behind a live path, or None when unmanaged."""
    try:
        out = subprocess.run(
            ["chezmoi", "source-path", real],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def guarded(path):
    real = os.path.realpath(path)
    if real == SOURCE or real.startswith(SOURCE + "/"):
        return True
    if real == CLAUDE_HOME + "/CLAUDE.md" or any(
        real.startswith(f"{CLAUDE_HOME}/{d}/") for d in AUTHORED
    ):
        return True
    if not real.startswith(HOME + "/") or real.startswith(UNMANAGED_ROOTS):
        return False
    return source_path(real) is not None


def added(patterns, new, old=""):
    """Matched text of each pattern seen more often in new than in old."""
    hits = []
    for pattern in patterns:
        found = pattern.findall(new) if new else []
        if len(found) > len(pattern.findall(old)):
            first = pattern.search(new).group(0)
            hits.append(first)
    return hits


def words(command):
    try:
        return shlex.split(command, comments=False)
    except ValueError:
        return command.split()


def path_tokens(command, cwd):
    paths = []
    for word in words(command):
        word = word.lstrip("<>").split("=")[-1]
        if "/" not in word and word not in (".", ".."):
            continue
        word = os.path.expandvars(os.path.expanduser(word))
        paths.append(word if os.path.isabs(word) else os.path.join(cwd, word))
    return paths


def files_under(path):
    if os.path.isdir(path):
        for root, _, names in os.walk(path):
            for name in names:
                yield os.path.join(root, name)
    elif os.path.isfile(path):
        yield path


def check_bash(patterns, command, cwd):
    hits = []
    for match in CHEZMOI_ADD.finditer(command):
        for target in path_tokens(match.group(1), cwd):
            for path in files_under(target):
                if not SELF.search(path):
                    hits += added(
                        patterns,
                        read(path),
                        read(source_path(os.path.realpath(path)) or ""),
                    )
    paths = path_tokens(command, cwd)
    touches = guarded(cwd) or any(guarded(p) for p in paths)
    if touches and WRITE_TOKEN.search(command):
        hits += added(patterns, command)
        for path in paths:
            if not guarded(path):
                hits += added(patterns, read(path))
    return hits


def check_file(patterns, tool, args):
    path = args.get("file_path", "")
    if not path or SELF.search(path) or not guarded(path):
        return []
    if tool == "Write":
        return added(patterns, args.get("content", ""), read(os.path.realpath(path)))
    edits = args.get("edits") if tool == "MultiEdit" else [args]
    new = "\n".join(e.get("new_string", "") for e in edits or [])
    old = "\n".join(e.get("old_string", "") for e in edits or [])
    return added(patterns, new, old)


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    tool = payload.get("tool_name", "")
    args = payload.get("tool_input", {}) or {}
    patterns = load_patterns()
    if tool == "Bash":
        hits = check_bash(
            patterns, args.get("command", ""), payload.get("cwd") or os.getcwd()
        )
        where = "this command"
    elif tool in ("Edit", "MultiEdit", "Write"):
        hits = check_file(patterns, tool, args)
        where = args.get("file_path", "")
    else:
        return
    if not hits:
        return
    terms = ", ".join(sorted({f"`{h}`" for h in hits}))
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        f"Private reference blocked: {terms} in {where}. The chezmoi "
                        "source and the files it manages are published as a public "
                        "repository. Describe the concept without the private name "
                        "(name a note by its filename only, a person by role, a "
                        "ticket not at all), or keep the text in the private work "
                        "profile under ~/dev/work/.claude. Graeme loosens a term by "
                        "editing the list the hook reads; a rewording that only "
                        "disguises the term defeats the guard."
                    ),
                }
            }
        )
    )


if __name__ == "__main__":
    main()
