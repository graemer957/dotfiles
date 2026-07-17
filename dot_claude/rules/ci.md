---
paths:
  - ".github/**"
---

# CI workflows

- Version pins inside run steps (pinned curl + checksum installs) are invisible to dependency automation, so they rot silently. Prefer an installer-action manifest (e.g. `taiki-e/install-action`) that rides routine dependency bumps — but confirm the tool is on the action's supported list first: non-listed tools silently fall back to `cargo-binstall`, so the checksum win isn't automatic. Where no manifest applies, pin + checksum and flag the pin as needing a periodic freshness sweep.
- A pipeline exits with its last command's status, and `run:` steps default to `bash -e` **without** `pipefail` — so `cmd | tee log` goes green when `cmd` fails. If a pipe's status-bearing command isn't last, add `shell: bash` (explicitly naming the shell selects `bash -eo pipefail`, unlike the default) or set workflow-level `defaults.run.shell: bash`. Pipes ending in the command that matters need nothing.
