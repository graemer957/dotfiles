# BCP registry

Index of every Best Current Practice. Each entry's `Home` is where its adherence text currently lives (updated whenever a BCP migrates); `Detect` is the hint a violation-detection pass uses — "judgement" marks entries that can't be mechanically screened.

## Ambient — home: CLAUDE.md bullets

### structural-fix-over-doc-rule
- Statement: when a fix is a new "remember to…" instruction (doc, CLAUDE.md rule, skill step), first look for the structural fix that makes the footgun impossible — a shared dependency, a recipe that chains the steps, a lint, a type that makes the bad state unrepresentable. Documentation-as-mitigation is the fallback only when tooling genuinely can't enforce the invariant.
- Home: personal CLAUDE.md § Best Current Practices (final)
- Trigger: proposing any fix or new process rule
- Detect: judgement — new "remember to X" rules in diffs or docs that paper over an enforceable footgun

### sweep-needs-a-gate
- Statement: a point-in-time remediation fixes only the snapshot it branched from; work on parallel branches silently reintroduces the anti-pattern when it merges. Pair every repo-wide hygiene sweep with a gate that runs on every PR.
- Home: personal CLAUDE.md § Best Current Practices (final)
- Trigger: planning or reviewing repo-wide hygiene/remediation work
- Detect: remediation changes with no companion always-on check

### comments-present-not-past
- Statement: a comment documents the current invariant and its why — never the change that produced it, what the code used to do, or why the new way is better. That history belongs in the diff, the PR body, and blame.
- Home: personal CLAUDE.md § Best Current Practices (final); host projects may restate it in their own CLAUDE.md
- Trigger: writing or reviewing code comments
- Detect: search comments for "instead of", "previously", "no longer", "used to", "replaced", "now"; judgement filter for false positives

### immutable-text-states-invariants
- Statement: write-once text (commit messages above all) carries only what stays permanently true — the structural invariant, never a point-in-time measurement or forward claim ("~3 min saved", "2× faster"). Measurements belong where they can be re-measured and dated: the PR body, a scorecard.
- Home: personal CLAUDE.md § Best Current Practices (final)
- Trigger: drafting commit messages or any write-once artifact
- Detect: pre-commit review of drafts for magnitudes, timings, or speed-up claims (post-commit the text is immutable — detection is only useful before landing)

### throw-on-violated-invariants
- Statement: a "can't happen" branch — a programming-error invariant, not a recoverable runtime condition — fails loudly (throw/assert) rather than degrading into a swallowed failure state; silent degradation hides the bug from monitoring and turns a code error into a mystery report. Reserve graceful handling for genuinely-expected failures.
- Home: personal CLAUDE.md § Best Current Practices (final)
- Trigger: writing error handling
- Detect: judgement — new error paths that map impossible states to default values or UI flags

### verify-pattern-precedent
- Statement: before recommending a pattern as "established in the codebase", search for it; sparse usage or single-file confinement is weak precedent — flag it as such rather than presenting it as the convention.
- Home: personal CLAUDE.md § Best Current Practices (final)
- Trigger: citing codebase precedent
- Detect: judgement — conversational claim, not mechanically screenable

### consistency-widening-in-scope
- Statement: three nested checks when changing code, the obligation softening as scope grows — added lines consistent with each other; ideally consistent with the file (reuse its patterns over a locally-nicer bespoke variant); highlight drift from the broader project and let the owner decide convergence.
- Home: personal CLAUDE.md § Best Current Practices (final)
- Trigger: any code change
- Detect: judgement — review-time

### re-read-nearby-comments
- Statement: when editing or reviewing code, re-read nearby comments and asserts; flag or update any gone stale in the same pass — stale documentation next to live code is worse than none, and review is the only window where the flag reaches the author.
- Home: personal CLAUDE.md § Best Current Practices (final)
- Trigger: any code edit or review
- Detect: judgement — comments adjacent to diff hunks

### conform-to-documented-standard
- Statement: check a deliverable's documented spec or an existing example up front, and re-check the whole artifact against it as the final hand-off step — not just the part last edited. Summarise analysis into the deliverable rather than transplanting it. When corrected on one detail, re-scan the entire artifact in one pass.
- Home: personal CLAUDE.md § Best Current Practices (final)
- Trigger: producing any deliverable with a documented standard
- Detect: judgement — hand-off gate

### no-private-note-references
- Statement: never reference private personal notes in shared artifacts (PRs, commits, public docs); inline-summarise the concept and link public sources instead.
- Home: personal CLAUDE.md § Best Current Practices (final)
- Trigger: writing anything shared
- Detect: search shared artifacts for private-vault references (e.g. "Obsidian", vault paths)

## File-scoped — home: path-scoped rules in ~/.claude/rules/

### derive-dont-mirror-state
- Statement: if a value can be computed from existing state or props, derive it during render rather than storing a second copy kept in sync by an effect — the mirrored copy buys an extra render, a stale-value window, and a reset obligation. The tell: a state setter inside an effect whose only job is to track another value.
- Home: ~/.claude/rules/react.md (final)
- Trigger: React state code
- Detect: search for effects whose body only sets state derived from other state/props

### exhaustive-destructuring
- Statement: code whose job is to visit every field of a struct (manual Debug/serialise impls, mappers, conversion fns) opens with a full destructure and no `..` rest pattern, so a new field becomes a compile error at every site that must decide about it. Same-crate types only (foreign non-exhaustive structs force `..`); not for ordinary field access.
- Home: ~/.claude/rules/rust.md (final)
- Trigger: writing or reviewing field-visiting Rust
- Detect: find manual Debug/serialise/From impls; check for `..` rest patterns; judgement on whether the type is field-visiting

### pinned-installs-rot
- Statement: version pins inside CI run steps (pinned curl + checksum installs) are invisible to dependency automation, so they rot silently. Prefer an installer-action manifest that rides routine dependency bumps — confirming the tool is on the action's verified list, since fallback install paths may skip verification; otherwise record the pin somewhere a freshness sweep will find it.
- Home: ~/.claude/rules/ci.md (final)
- Trigger: adding or editing CI tool-install steps
- Detect: search workflows for pinned download-and-verify installs; compare pinned versions against upstream latest

## Task-moment — home: this skill

### audit-instruction-files
- Statement: run the authoring.md audit checklist on every instruction-file edit, naming which sources ran, then self-check: "did I apply the principles I just checked against?"
- Home: authoring.md (final)
- Trigger: writing or editing a SKILL.md, CLAUDE.md, rule, or hook
- Detect: the checklist is the detector

### skill-authoring-conventions
- Statement: conventions only hold when they live where the work happens and fire by construction, not recall — for skill authoring that mechanism is authoring.md's frontmatter and body conventions, applied at write time.
- Home: authoring.md (final)
- Trigger: SKILL.md authoring
- Detect: audit existing SKILL.md files against authoring.md

### periodic-currency-audit
- Statement: a push-based update stream measures activity, not currency — quiet weeks are silence, not health (majors held back, git-source and transitive-only dependencies invisible). Bound drift with a periodic pull-based staleness audit.
- Home: registry only; execution deliberately dropped for Rust (2026-07: the audit-tool candidate proved broken for the workspace, so the push stream is the accepted coverage — revisit only if a blind spot bites)
- Trigger: dependency-maintenance planning
- Detect: date of the last staleness audit against the intended cadence

## Work-level — home: work CLAUDE.md

### team-standard-commands
- Statement: artifacts checked into a team repo (skills, docs, CI, recipes) prescribe only commands every consumer's machine can run — a command only one machine has fails silently for everyone else. Check repo precedent before committing a command; a personal tool can also be genuine team tooling, so verify rather than assume either way.
- Home: work-level CLAUDE.md (final; machine-specific examples stay private)
- Trigger: authoring anything checked into a team repo
- Detect: search shared artifacts for personal-only tooling

### pr-review-workflow
- Statement: PR review findings stay within the diff's changed files; verify against stacked child PRs before and after the review; grade a proposed fix separately from its hazard; findings adversarially validated by minimal-context agents before reaching the reviewer, then staged as one pending review the reviewer submits themself.
- Home: `review-pr` skill in the work profile (final)
- Trigger: reviewing a pull request
- Detect: judgement — review-time
