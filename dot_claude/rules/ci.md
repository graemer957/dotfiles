---
paths:
  - ".github/**"
---

# CI workflows

- Version pins inside run steps (pinned curl + checksum installs) are invisible to dependency automation, so they rot silently. Prefer an installer-action manifest (e.g. `taiki-e/install-action`) that rides routine dependency bumps — but confirm the tool is on the action's supported list first: non-listed tools silently fall back to `cargo-binstall`, so the checksum win isn't automatic. Where no manifest applies, pin + checksum and flag the pin as needing a periodic freshness sweep.
- A pipeline exits with its last command's status, and `run:` steps default to `bash -e` **without** `pipefail` — so `cmd | tee log` goes green when `cmd` fails. Guard the class by construction: workflow-level `defaults: run: shell: bash` (explicitly naming the shell selects `bash -eo pipefail`, unlike the default). When editing a workflow that lacks it, add it — as its own commit, since it can surface latent pipe failures — or flag it when reviewing. Per-step `shell: bash` is the fallback only where a job needs a different default shell.
- An `env:` hoist of a `${{ }}` expression is injection containment, not an abstraction — name the variable after its source so the data's provenance stays visible at the use site: `github.actor` → `GH_ACTOR`, `inputs.apt-packages` → `APT_PACKAGES`, `steps.<id>.outputs.<out>` → `<ID>_<OUT>`, `vars.X` / `secrets.X` keep their name. Same expression, same name, everywhere in the repo; a role-based rename (`HELD_BY`) hides that the value is attacker-adjacent context. For deeply nested paths keep the trailing segment (`github.event.workflow_run.head_branch` → `GH_HEAD_BRANCH`), adding leading segments only to disambiguate.
