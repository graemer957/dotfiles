---
name: bcp
description: Graeme's Best Current Practices (BCPs) — durable engineering rules indexed in a registry, plus conventions for authoring instruction files. Use when creating or editing any SKILL.md, CLAUDE.md, .claude/rules/ file, or hook; when asked to audit an artifact or diff against the BCPs; or when graduating a new BCP candidate into a home.
---

# Best Current Practices

## Scope

1. **Authoring** — writing or editing an instruction file (SKILL.md, CLAUDE.md, rule, hook): apply `authoring.md`.
2. **Auditing** — checking an artifact or diff against the BCPs: apply `registry.md`.
3. **Lifecycle** — intake, graduation, and registry upkeep of BCPs.

## Registry

`registry.md` indexes every BCP: statement, home, trigger, detection hint. Each entry carries a standalone statement so an audit pass runs from the registry alone — but the registry is not the home: the authoritative adherence text lives at each BCP's home (a CLAUDE.md bullet, a path-scoped rule, or a supporting file in this skill), and on wording drift the home wins.

## Workflow

1. Identify the task: authoring, audit, or lifecycle.
2. **Authoring**: read `authoring.md` before writing; run its audit checklist before hand-off, naming which checklist sources ran.
3. **Audit**: read `registry.md`; select entries whose trigger matches the artifact; report violations one at a time, most severe first.
4. **Lifecycle** (new BCP candidate): confirm it is durable and cross-project; a practice that is work-specific by nature homes in the work-level CLAUDE.md instead, but is indexed here all the same; add a registry entry; place its adherence text by trigger shape — file-type-bound → path-scoped rule in `~/.claude/rules/`; task-moment → a supporting file in this skill; unscopeable → a terse CLAUDE.md bullet. A home only counts if it loads: confirm it's discoverable in every launch profile that needs it — a `CLAUDE_CONFIG_DIR` profile sees `~/.claude` skills and rules only via the launcher's symlink bridge. New areas become supporting files here (e.g. `rust.md`), read only when their scope applies. If the new BCP introduces a task-moment trigger for this skill, extend the description's use-when list in the same edit.

## Boundaries

- Don't home a BCP in two places — homes are single; the registry points.
- Don't put provenance (names, PR numbers, incidents) in this skill or the registry — both are public; provenance stays in private session memory.

## Improving this skill

Skills decay. If while running this one you find something that would have sped you up or contradicts what's written here — an auto-load miss on an instruction-file edit, a registry entry left stale after a migration, a BCP violated because its home never loaded, a trigger-shape call that placed a BCP wrongly — surface a proposed edit before moving on:

1. Draft the diff for this file in chat (lines + one-line why).
2. Wait for the user's go-ahead.
3. Edit the chezmoi source, then hand to the user to `chezmoi apply` before continuing.

Don't batch corrections across runs — surface each one the moment you spot it.
