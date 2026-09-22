#!/usr/bin/env python3
"""Check hook registrations across the profile settings files after a call names one.

PostToolUse: when an Edit/Write/Bash call names a Claude settings file (a
settings*.json under a .claude or dot_claude directory), parses the personal,
work and shared-fragment settings — the chezmoi source where one exists, so a
staged edit is checked before apply, else the live file — and reports as
additional context: a command under SHARED_HOOKS registered in a profile file,
which belongs in the shared fragment; a command registered in more than one
file, which one fragment registration would cover; a top-level key in the
fragment outside FRAGMENT_KEYS, which --settings pins across every profile.
Silent when clean, and for a file that is missing or does not parse mid-edit.
"""

import json
import os
import re
import sys

HOME = os.path.expanduser("~")
CHEZMOI = HOME + "/.local/share/chezmoi/dot_claude/"
SHARED_HOOKS = HOME + "/.claude/hooks/"
# Per role, candidates in precedence order.
FILES = {
    "personal": [CHEZMOI + "settings.json", HOME + "/.claude/settings.json"],
    "work": [HOME + "/dev/work/.claude/settings.json"],
    "shared": [
        CHEZMOI + "settings-shared-hooks.json",
        HOME + "/.claude/settings-shared-hooks.json",
    ],
}
FRAGMENT_KEYS = {"hooks", "//", "$schema"}
SETTINGS_TOKEN = re.compile(r"(?:\.claude|dot_claude)/settings[\w.-]*\.json\b")


def names_settings_file(payload):
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input", {})
    if tool in ("Edit", "Write"):
        text = tool_input.get("file_path", "")
    elif tool == "Bash":
        text = tool_input.get("command", "")
    else:
        return False
    return bool(SETTINGS_TOKEN.search(text))


def load(role):
    """(path, parsed JSON) for the first existing candidate of role; None when none exists or it does not parse."""
    for path in FILES[role]:
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    return path, json.load(f)
            except (OSError, json.JSONDecodeError):
                return None
    return None


def commands(settings):
    return [
        h["command"]
        for entries in settings.get("hooks", {}).values()
        for entry in entries
        for h in entry.get("hooks", [])
        if h.get("command")
    ]


def findings():
    out = []
    where = {}
    for role in FILES:
        item = load(role)
        if item is None:
            continue
        path, settings = item
        for cmd in set(commands(settings)):
            where.setdefault(cmd, []).append(path)
            if role != "shared" and cmd.startswith(SHARED_HOOKS):
                out.append(
                    f"{path}: {cmd} is registered in a profile file; hooks under "
                    f"{SHARED_HOOKS} run in every profile and belong in the shared fragment"
                )
        if role == "shared":
            for key in settings:
                if key not in FRAGMENT_KEYS:
                    out.append(
                        f"{path}: top-level key {key!r} pins that value across every "
                        "profile; the fragment is hooks only"
                    )
    for cmd, paths in where.items():
        if len(paths) > 1:
            out.append(
                f"{cmd} is registered in {', '.join(sorted(paths))}; one registration "
                "in the shared fragment covers every profile"
            )
    return out


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    if not names_settings_file(payload):
        return
    found = findings()
    if found:
        emit(
            "Hook-homes check on the settings files as they will apply:\n"
            + "\n".join(found)
        )


def emit(text):
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": text,
                }
            }
        )
    )


if __name__ == "__main__":
    main()
