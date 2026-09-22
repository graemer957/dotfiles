---
paths:
  - "**/*.sh"
  - "**/*.bash"
---

# Shell scripts

- Shell linting is `shellcheck`: quoting, word-splitting, and unchecked-exit
  bugs sit silent until an edge case or hostile input hits them. The
  PostToolUse shell hook runs it on every `.sh` or `.bash` path an Edit,
  Write, or Bash call names: the hook's silence after an edit means clean,
  and a hand-run (for a script the hook didn't see, such as an extensionless
  one with a bash shebang) is a bare `shellcheck <file>`. The tool is required
  on this machine: a missing binary blocks the hook, so stop and report it
  rather than hand back unchecked work.
- In a personal file, fix the findings your edit introduced or touched and
  raise pre-existing ones in session rather than fixing them, since that
  widens the diff beyond the change under review. In a team repo (a git work
  tree under the hook's `TEAM_ROOT`) the hook lists only findings the working
  copy adds over `HEAD`: fix those before hand-back and leave pre-existing
  ones unmentioned — the linter isn't team-adopted, so they are neither yours
  to fix nor worth the user's attention. A new script passes clean.
