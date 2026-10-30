#!/usr/bin/env python3
"""Record refuter reviews, and answer whether a file has had one.

Each run of the refute skill appends one line here: when, which files the
change under review edits, the verdict, the token spend, how many of the
changes drew an objection that held, and a note naming the changes. The
instruction-file gate reads the log through `cleared` before it lets an edit to
an always-loaded instruction file through, and adds a line through `passed` for
each edit it lets through. A review clears its files for the whole window,
since nothing here can tell two changes to one file apart; a skip clears one
edit. `summary` gives the figures the practice is judged on: what reviews cost,
how many edits they cleared, and every skip and carried review with its note.

  refute_log.py record --target FILE [--target FILE ...] --note TEXT
                       --verdict reviewed|skipped|carried
                       [--changes N] [--changed N] [--tokens N]
  refute_log.py summary
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

NAME = "refute-log.jsonl"
WINDOW_HOURS = 24
REVIEWED = "reviewed"
SKIPPED = "skipped"
# A review from an earlier session, re-recorded so a walk that outlasts the
# window can still land its edits.
CARRIED = "carried"
VERDICTS = (REVIEWED, SKIPPED, CARRIED)
EDIT = "edit"


def logs():
    """The log this profile writes, then the default profile's, without repeats."""
    homes = [os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude", "~/.claude"]
    paths = [Path(home).expanduser() / NAME for home in homes]
    return list(dict.fromkeys(paths))


def canonical(path):
    return os.path.realpath(os.path.expanduser(path))


def entries(log):
    try:
        lines = Path(log).read_text(errors="replace").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            out.append(entry)
    return out


def cleared(path, now=None, candidates=None):
    """True when the log lets an edit to `path` through at `now`.

    A review or a carried review within the window does, however many edits
    follow it. A skip does until the next edit let through, so a "no
    instruction changes" call covers the one edit it was made for.
    """
    now = now or datetime.datetime.now().astimezone()
    target = canonical(path)
    oldest = now - datetime.timedelta(hours=WINDOW_HOURS)
    for log in candidates or logs():
        skip_open = False
        for entry in entries(log):
            if target not in entry.get("targets", []):
                continue
            try:
                at = datetime.datetime.fromisoformat(entry.get("at", ""))
            except (TypeError, ValueError):
                continue
            if not oldest <= at <= now:
                continue
            verdict = entry.get("verdict")
            if verdict in (REVIEWED, CARRIED):
                return True
            if verdict == SKIPPED:
                skip_open = True
            elif verdict == EDIT:
                skip_open = False
        if skip_open:
            return True
    return False


def append(entry, now=None, log=None):
    now = now or datetime.datetime.now().astimezone()
    entry = {"at": now.isoformat(timespec="seconds"), **entry}
    with open(Path(log or logs()[0]), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def record(targets, verdict, changes, changed, tokens, note, now=None, log=None):
    entry = {
        "targets": [canonical(t) for t in targets],
        "verdict": verdict,
        "changes": changes,
        "changed": changed,
        "tokens": tokens,
        "note": note,
    }
    return append(entry, now, log)


def passed(path, now=None, log=None):
    """Note an edit the gate let through."""
    return append({"targets": [canonical(path)], "verdict": EDIT}, now, log)


def listed(found, verdict):
    """One indented line per entry of `verdict`: date, files, note."""
    return [
        f"  {e.get('at', '')[:10]}  {', '.join(e.get('targets', []))}: {e.get('note')}"
        for e in found
        if e.get("verdict") == verdict
    ]


def since(found, day):
    """The entries dated on or after `day` (YYYY-MM-DD); all of them for ''."""
    return [e for e in found if e.get("at", "")[:10] >= day]


def summary(found):
    """The lines `summary` prints for a list of entries."""
    reviews = [e for e in found if e.get("verdict") == REVIEWED]
    changes = sum(e.get("changes") or 0 for e in reviews)
    changed = sum(e.get("changed") or 0 for e in reviews)
    edits = sum(e.get("verdict") == EDIT for e in found)
    lines = [f"reviews      {len(reviews)}", *listed(found, REVIEWED)]
    if reviews:
        lines.append(f"changes      {changed} of {changes} drew an objection that held")
    costed = [e for e in reviews if e.get("tokens")]
    if costed:
        tokens = sum(e["tokens"] for e in costed)
        over = sum(e.get("changes") or 0 for e in costed)
        per_change = f", {tokens / over:,.0f} a change" if over else ""
        lines.append(
            f"tokens       {tokens:,} over {len(costed)} costed reviews "
            f"({tokens / len(costed):,.0f} a review{per_change})"
        )
    lines.append(
        f"edits        {edits} let through, against {changes} changes reviewed"
    )
    for label, verdict in (("skips", SKIPPED), ("carried", CARRIED)):
        rows = listed(found, verdict)
        lines += [f"{label:<12} {len(rows)}", *rows]
    if found:
        lines.append(f"since        {min(e.get('at', '') for e in found)[:10]}")
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    rec = sub.add_parser("record")
    rec.add_argument("--target", action="append", required=True)
    rec.add_argument("--verdict", choices=VERDICTS, required=True)
    rec.add_argument("--note", required=True)
    rec.add_argument("--changes", type=int, default=0)
    rec.add_argument("--changed", type=int, default=0)
    rec.add_argument("--tokens", type=int, action="append", help="one per refuter")
    summ = sub.add_parser("summary")
    summ.add_argument("--since", metavar="YYYY-MM-DD", default="")
    args = ap.parse_args()

    if args.command == "record":
        entry = record(
            args.target,
            args.verdict,
            args.changes,
            args.changed,
            sum(args.tokens) if args.tokens else None,
            args.note,
        )
        print(f"logged       {entry['verdict']}: " + ", ".join(entry["targets"]))
        return 0
    found = [e for log in logs() for e in entries(log)]
    print("\n".join(summary(since(found, args.since))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
