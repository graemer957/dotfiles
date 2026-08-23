---
paths:
  - "**/*.sh"
  - "**/*.bash"
---

# Shell scripts

- Run `shellcheck` on every shell script you create or edit, before handing the work back — quoting, word-splitting, and unchecked-exit bugs sit silent until an edge case or hostile input hits them. A new script passes clean; in an existing one, fix the findings your edit introduced or touched and flag pre-existing ones elsewhere. The tool is required on this machine: when `shellcheck` isn't on PATH, stop and report the missing tool instead of handing back unchecked work.
