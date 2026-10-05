#!/usr/bin/env python3
"""Record a Skill(bcp) run for bcp-instruction-gate as soon as it completes.

PostToolUse on Skill: touches the session's marker (per subagent when the
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
    if not isinstance(payload, dict) or payload.get("tool_name") != "Skill":
        return
    if (payload.get("tool_input") or {}).get("skill") != "bcp":
        return
    transcript = payload.get("transcript_path")
    if not transcript:
        return

    from bcp_window import marker_path

    marker = marker_path(transcript, payload.get("agent_id"))
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except OSError:
        return


if __name__ == "__main__":
    main()
