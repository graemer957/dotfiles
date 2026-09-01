#!/usr/bin/env python3
"""Inject path-scoped rules for files a tool call names, wherever they live.

The native rules loader matches ~/.claude/rules/*.md `paths:` globs
against the project root only, so files outside it (worktrees, Obsidian,
.claude config trees, chezmoi source) never load their rules — and Bash
commands (cat/sed/linters) load none at all, since rules key on the
dedicated file tools. On an Edit/Write (the edited file) or a Bash call
(every path-looking token in the command text, resolved against the
call's cwd), this PostToolUse hook re-reads each rule's frontmatter,
matches the absolute paths, and returns matching rule bodies as
additionalContext — once per rule per session, tracked in a tmpfs marker
directory. Bash token extraction is permissive by design: a stray token
that resolves to a matching path merely injects a relevant rule early,
so false positives are harmless; a command naming no path (a bare
tree-wide lint) injects nothing. In-tree files are deliberately not
skipped: a duplicate of the native injection costs one context copy per
rule per session, and covers sessions where native injection misfires.

Glob support is the subset the rules use: leading `**/`, trailing `/**`,
plain suffixes, `?`, `[...]`. A rule whose globs need more (braces,
extglob, flow-style `paths:`) is reported via systemMessage once per
session rather than silently never matching.

INJECT_RULES_DIR overrides the rules directory (tests only).
"""

import fnmatch
import json
import os
import re
import sys
from pathlib import Path

PREAMBLE = (
    "A file this tool call names is covered by path-scoped rules, which "
    "do not auto-load for files outside the project root. Apply these "
    "rules to this work before handing it back:"
)

BASH_TOKEN = re.compile(r'"([^"]*)"|\'([^\']*)\'|(\S+)')

UNSUPPORTED_CHARS = "{}()"


def rule_globs(text):
    """Parse the frontmatter `paths:` block. Returns (globs, warning)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], None
    globs = []
    in_paths = False
    saw_paths = False
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if re.match(r"^paths:\s*$", line):
            in_paths = saw_paths = True
            continue
        if line.startswith("paths:"):
            return [], "flow-style `paths:` list (unsupported)"
        if in_paths:
            m = re.match(r'^\s+-\s*"?([^"]+?)"?\s*$', line)
            if m:
                globs.append(m.group(1))
            elif line.strip():
                in_paths = False
    if saw_paths and not globs:
        return [], "`paths:` present but no globs extracted"
    return globs, None


def to_abs_pattern(glob):
    """Rewrite a project-root-relative glob to match absolute paths."""
    if glob.startswith("**/"):
        return "*/" + glob[3:]
    if glob.endswith("/**"):
        return "*/" + glob[:-3] + "/*"
    return "*/" + glob


def bash_candidate_paths(command, cwd):
    """Tokens of a Bash command that look like file paths, absolutised."""
    paths = set()
    for dq, sq, bare in BASH_TOKEN.findall(command):
        tok = (dq or sq or bare).lstrip("<>").rstrip("();,")
        if tok.startswith("-"):
            continue
        assignment = re.match(r"^[A-Za-z_][A-Za-z0-9_]*=(.*)$", tok)
        if assignment:
            tok = assignment.group(1)
        if "/" not in tok and "." not in tok:
            continue
        tok = os.path.expanduser(tok)
        if not os.path.isabs(tok):
            tok = os.path.normpath(os.path.join(cwd, tok))
        paths.add(tok)
    return paths


def rule_body(text):
    """The rule text with its frontmatter block removed."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                return "\n".join(lines[i + 1:]).strip()
    return text.strip()


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input", {})
    if tool in ("Edit", "Write"):
        file_paths = [tool_input.get("file_path", "")]
    elif tool == "Bash":
        cwd = payload.get("cwd") or os.getcwd()
        file_paths = sorted(bash_candidate_paths(tool_input.get("command", ""), cwd))
    else:
        return
    file_paths = [p for p in file_paths if p]
    if not file_paths:
        return

    session = re.sub(r"[^A-Za-z0-9_-]", "_", payload.get("session_id", "unknown"))
    state = Path(f"/tmp/claude-rule-inject-{os.getuid()}") / session
    state.mkdir(parents=True, exist_ok=True)

    rules_dir = Path(os.environ.get("INJECT_RULES_DIR", Path.home() / ".claude/rules"))
    injected = []
    warnings = []
    for rule in sorted(rules_dir.glob("*.md")):
        name = rule.stem
        try:
            text = rule.read_text(errors="replace")
        except OSError:
            continue
        globs, warning = rule_globs(text)
        bad = [g for g in globs if any(c in g for c in UNSUPPORTED_CHARS)]
        if warning or bad:
            marker = state / f"warn-{name}"
            if not marker.exists():
                marker.touch()
                detail = warning or f"glob(s) {bad} use unsupported shapes"
                warnings.append(f"rule '{name}': {detail}")
        if (state / name).exists():
            continue
        if any(
            fnmatch.fnmatchcase(p, to_abs_pattern(g))
            for p in file_paths
            for g in globs
            if g not in bad
        ):
            injected.append(f'<rule name="{name}">\n{rule_body(text)}\n</rule>')
            (state / name).touch()

    out = {}
    if injected:
        out["hookSpecificOutput"] = {
            "hookEventName": "PostToolUse",
            "additionalContext": PREAMBLE + "\n" + "\n".join(injected),
        }
    if warnings:
        out["systemMessage"] = (
            "inject-rules.py cannot match some rule globs (rules affected "
            "will not inject out-of-tree): " + "; ".join(warnings)
        )
    if out:
        print(json.dumps(out))


if __name__ == "__main__":
    main()
