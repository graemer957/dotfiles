#!/usr/bin/env python3
"""Record a bcp run for bcp-instruction-gate as soon as it completes.

PostToolUse on Skill, Read and Bash: when the call loaded the bcp skill or read
its authoring checklist, touches the session's marker (per subagent when the
payload carries an agent_id), which the gate reads alongside the transcript,
since the transcript can reach disk after the next tool call's hooks run.
Silent always; any failure falls back to the transcript alone.
"""

import json
import sys


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    if not isinstance(payload, dict):
        return
    tool = payload.get("tool_name")
    if tool not in ("Skill", "Read", "Bash"):
        return
    transcript = payload.get("transcript_path")
    if not transcript:
        return

    from bcp_window import marker_path, runs_bcp

    if not runs_bcp(tool, payload.get("tool_input")):
        return

    marker = marker_path(transcript, payload.get("agent_id"))
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except OSError:
        return


if __name__ == "__main__":
    main()
