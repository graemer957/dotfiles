---
paths:
  - "**/*.md"
---

# Markdown

- Markdown linting is `rumdl`. The PostToolUse markdown hook runs it on every
  `.md` path an Edit, Write, or Bash call names, with the disable list the
  hook's `DISABLES` mapping gives that path — the single home of those lists.
  A finding is what `rumdl` reports under that list: the hook's silence after
  an edit means clean, and a hand-run (for a file the hook didn't see) takes
  the same `-d` list, since a bare invocation reports rules the mapping
  exempts.
- Fix findings by hand. `rumdl fmt` and `rumdl check --fix` rewrite every
  fixable rule in the file, including the ones the mapping disables, so an
  auto-fix undoes the deliberate formatting those disables protect.
- In a personal file, fix the findings your edit introduced or touched and
  raise pre-existing ones in session rather than fixing them, since that
  widens the diff beyond the change under review. In a team repo (a git work
  tree under the hook's `TEAM_ROOT`) the hook lists only findings the working
  copy adds over `HEAD`: fix those before hand-back and leave pre-existing
  ones unmentioned — the linter isn't team-adopted, so they are neither yours
  to fix nor worth the user's attention. A new file passes clean.
- A repo shipping its own `rumdl` config governs from there. The tool is
  required on this machine: when `rumdl` isn't on PATH, stop and report the
  missing tool instead of handing back unlinted work.
