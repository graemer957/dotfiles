# Authoring instruction files

Conventions for writing or editing a SKILL.md, CLAUDE.md, path-scoped rule, or hook.

## Frontmatter (SKILL.md)

- Gate auto-invocation with `disable-model-invocation: true` when the skill should fire only on explicit invocation — never via "don't auto-invoke" prose in the body.
- Description = what + when, action-first, third person: it is the surface the model matches to decide relevance.
- A new, renamed, or deleted skill updates its row in the personal skill ledger (model, Mechanical, Headlines, one-line description) in the same edit; the ledger is the model authority the harness audit reconciles against.

## Body

- Lean: instructions, not rationale — don't restate the description, narrate why, or prescribe tooling the reader's machine may lack.
- Standard section order: Scope → Definitions → Workflow → Output format → Boundaries → Improving this skill. Omit sections with nothing to say.
- Output formats as code-fenced templates so the consumer sees the shape, not prose about it.
- An output template carries only what its reader acts on: the outcome and the pending decisions. What a run produces for its own record (costs, tallies, applied bookkeeping) goes to a file the template names, shown on ask — a block the template lists is produced on every run, whatever a general brevity rule says.
- A template for the message a run stops on to hand its reader an outcome and decisions (a review, a triage, an audit), read in chat, has three parts in this order, and a part with nothing in it is left out. The reader skims it in a terminal, and a table is looked up by label where prose is read from start to finish, so the first table alone gives the outcome. A row or a footnote states something only the run knows and the reader may act on. Once the message has been through a real run, the skill keeps that filled message beside its SKILL.md as `headlines-exemplar.md` and the template points at it, since an example settles how brief the message is where an adjective cannot.

  ```markdown
  | | Headlines |
  |---|---|
  | <one emoji> <label> | <a few words> |

  <the table of what the reader decides>

  **Footnotes**
  - **<label>:** <one line>
  ```

- Boundaries as explicit Don't-X bullets — the one place negative framing belongs.
- A rule that names a command or flag ("never `X`", "don't run `Y`") gets a hook or lint beside it, or states why tooling can't enforce it — a deterministic match left as prose is a fortnightly audit catch instead of a same-day one.
- Every co-authored skill ends with the "Improving this skill" loop: copy the numbered steps and the mechanical-sequence paragraph verbatim from a sibling; adapt only the trigger list to the skill's own failure modes.
- A qualifying mechanical sequence becomes a script matched to the skill's audience, so it runs wherever the skill does: a team-repo skill gets a `just` recipe, the team's standard entry point; a personal skill gets a bash script beside its SKILL.md for glue, and Rust or Python, weighed per case, once the sequence holds logic.

## Audit checklist — run before hand-off, naming which sources ran

1. **These conventions** (the sections above).
2. **The instruction-file checklist**: missing why clauses; weasel hedges ("if installed", "where possible"); overlapping or redundant rules; absolutes that should be defaults with an escape hatch; negative framings outside Boundaries; scope ambiguity; contradictions across files; triggers too narrow to justify always-loaded cost.
3. **Anthropic's prompting best-practices doc** — read it, don't paraphrase from memory: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices>. It applies to any model-facing instruction text (CLAUDE.md bullets and rules included, not just API prompts); skip it only when the edit adds no new instruction semantics (typo, rewrap, link fix), and name the skip.
4. **The host project's comment/documentation conventions**, when the artifact is checked into a repo.
5. **The ambient BCPs** in the global CLAUDE.md's Best Current Practices, starting with structural fix over doc rule: an instruction edit is itself a doc rule, so name the structural alternative, or why tooling can't enforce the invariant, before sharing the draft.

Reconcile conflicts explicitly — e.g. Don't-X boundaries vs positive framing resolves to: negatives allowed only in Boundaries. Grep the artifact for leftover references to anything the edit changed. Close with the self-check: "did I apply the principles I just checked against?"
