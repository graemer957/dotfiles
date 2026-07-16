# Authoring instruction files

Conventions for writing or editing a SKILL.md, CLAUDE.md, path-scoped rule, or hook.

## Frontmatter (SKILL.md)

- Gate auto-invocation with `disable-model-invocation: true` when the skill should fire only on explicit invocation — never via "don't auto-invoke" prose in the body.
- Description = what + when, action-first, third person: it is the surface the model matches to decide relevance.

## Body

- Lean: instructions, not rationale — don't restate the description, narrate why, or prescribe tooling the reader's machine may lack.
- Standard section order: Scope → Definitions → Workflow → Output format → Boundaries → Improving this skill. Omit sections with nothing to say.
- Output formats as code-fenced templates so the consumer sees the shape, not prose about it.
- Boundaries as explicit Don't-X bullets — the one place negative framing belongs.
- Every co-authored skill ends with the "Improving this skill" loop: copy the numbered steps verbatim from a sibling; adapt only the trigger list to the skill's own failure modes.

## Audit checklist — run before hand-off, naming which sources ran

1. **These conventions** (the sections above).
2. **The instruction-file checklist**: missing why clauses; weasel hedges ("if installed", "where possible"); overlapping or redundant rules; absolutes that should be defaults with an escape hatch; negative framings outside Boundaries; scope ambiguity; contradictions across files; triggers too narrow to justify always-loaded cost.
3. **Anthropic's prompting best-practices doc** — read it, don't paraphrase from memory: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
4. **The host project's comment/documentation conventions**, when the artifact is checked into a repo.

Reconcile conflicts explicitly — e.g. Don't-X boundaries vs positive framing resolves to: negatives allowed only in Boundaries. Grep the artifact for leftover references to anything the edit changed. Close with the self-check: "did I apply the principles I just checked against?"
