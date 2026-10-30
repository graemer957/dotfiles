---
name: refute
description: >-
  Decide whether a drafted change is worth an adversarial review, then run
  one: three independent refuters try to break the change, and only the
  objections that survive a check are reported. Use on /refute, before any
  change to a CLAUDE.md, when another skill's workflow calls for it, and to
  offer one before a change whose mistake would be costly and hard to see.
---

# Refute

## Scope

An adversarial review of a change that is drafted and not yet made: an instruction-file edit, a design, a plan, a fix. It answers "should we seek refuter reviews before we make that change?" and then acts on the answer. A pull request has its own review flow; this is for a change still in hand.

## Workflow

1. **Verdict.** Say in one line whether a review is worth it, and why.
   - A change to a `CLAUDE.md` that alters what it instructs gets one every time: that prose steers every session that loads it, and its author cannot read off what it will make a model do.
   - An edit that alters no instruction (a typo, a rewrap, a link fix) gets none. Say so, log the skip with its reason (step 5) and stop; a skip clears the one edit it was made for.
   - A change the log shows reviewed in an earlier session and unaltered since keeps that review: `refute_log.py summary` beside this file lists each review with its files and, in its note, the changes it covered. Log it as carried (step 5), naming the date, and stop.
   - For anything else, weigh what a wrong change costs (how hard it is to undo, how many sessions or people it reaches, whether anyone else has looked) against what the review costs, which `summary` prints. On a no, say so and stop; nothing is logged. On a yes, when the run was neither typed as `/refute` nor called for by a skill the user invoked, state the expected spend and wait for a go, since a review costs enough to be the user's call.
2. **Frame.** Write the change to a scratch file as a diff or as the new text, with a short label on each separable change. Give the refuters the text and the labels, and leave out the case for the change: an agent handed the argument tends to return it confirmed.
3. **Refute.** Spawn three fresh read-only agents in one message, each told to refute, to back every objection with quoted text and one situation that really arises, and to object when unsure. One lens each, reworded to fit the kind of change:
   - **Should it exist?** What goes wrong without it and how often, what already produces the same result, and whether something structural (a hook, a script, a narrower home) would do it better.
   - **What will it do that its author would not expect?** Over-application, a loophole the wording leaves, a collision with a neighbouring rule or caller, a safeguard it weakens.
   - **Apply it cold.** Take it exactly as written, name two real moments where it decides what happens, say what it does there, and flag every fork in the reading and every term that resolves nowhere.

   Each agent returns, for every label, either "survives" or an objection with the quoted text, the situation and the smallest fix.
4. **Check.** Refuters are told to object when unsure, so their reports overstate. Re-read the quoted text for each objection and keep it only when the text really produces the situation and the situation is one that comes up. Where several object to one change, keep the strongest.
5. **Log.** Run `refute_log.py record` beside this file with a `--target` for each file the change edits, given as the path the edit will land on (the chezmoi source for a managed file, the worktree's copy for a repository file; for a design or a plan, the file holding the draft), `--verdict reviewed`, a `--note` naming the change labels, `--changes`, `--changed` (how many drew an objection that held) and `--tokens` (the refuters' summed spend). A skip or a carried review from step 1 takes `--verdict skipped` or `--verdict carried` and its reason as the note. The instruction-file gate lets an edit to a `CLAUDE.md` through only when this skill has been invoked in the session and the log clears that path: a review or a carried review clears it for a day, a skip for one edit. The gate adds each edit it lets through to the log.
6. **Report** in the format below, strongest objection first, and stop: each fix is the reader's decision. When another skill invoked this run, the report goes to that skill in place of the user, and that skill says who decides the fixes. A change that later goes to its reader for approval carries the strongest objection it faced, including one that fell, since the reader is trusting the review in place of reading the prose.

## Output format

```markdown
| | Headlines |
|---|---|
| 🧪 Refuted | <N> changes, <M> with an objection that held |
| 🤔 For you | <N> decisions, and the lean where the run has one |
| 🪙 Tokens | <summed spend> |

| # | Change | Strongest objection | Fix |
|---|---|---|---|
| 1 | <label> | <one line> | <reword / drop / move> |

**Footnotes**
- **<label>:** <one line>
```

The second table lists the changes where an objection held; the rest are counted in the first and not listed. `headlines-exemplar.md` beside this file is a real run's report in this shape, with the reasons for it: match its brevity.

## Boundaries

- Don't make the change, or a fix to it, during the run — the run ends on the report, and whoever called it applies what is decided.
- Don't report an objection you have not checked against the text it quotes — an unchecked objection hands the reader the refuter's guess as a finding.
- Don't treat one review as covering a later change to the same file — the log clears a file for a day because it cannot tell two changes apart, so each change that alters an instruction still gets its own run.
- Don't spawn refuters on a verdict of no — the verdict step exists so that a review is spent only where a wrong change would cost more than the review does.

## Improving this skill

Skills decay. If while running this one you find something that would have sped you up or contradicts what's written here — a lens that returned only noise, a verdict that misjudged how far a change reached, a gate denial on a change that had its review — surface a proposed edit before moving on:

1. Draft the diff for this file in chat (lines + one-line why).
2. Wait for the user's go-ahead.
3. Edit the chezmoi source, then hand to the user to `chezmoi apply` before continuing.

Don't batch corrections across runs — surface each one the moment you spot it.

Before the final hand-back, look back over this run's tool calls for a mechanical sequence: commands with no decision between them. One qualifies for a script when this file prescribes it, when it ran three times this run, or when it did arithmetic or tallying by hand; a script runs identically every time, where prose drifts. Read this skill's Mechanical cell in the personal skill ledger first: it holds what earlier runs built and declined. Once the run's result is in front of the user, so the build never delays it, turn a sequence you judge worth it into a script, or extend the script that covers it, with a regression test beside it, choosing what to build from the `bcp` skill's `authoring.md`. The scripts beside a skill are yours to maintain, so the build and the line of this file that calls the script need no go-ahead beyond step 3's `chezmoi` hand-off; any other change to this file's text takes the steps above. Record the outcome in the cell whenever it changes, a first check that finds nothing included. Of this check, chat carries one line per script built or changed, with any changed line of this file as an inline diff; a clean check or a declined candidate goes in the cell alone, since it leaves the reader nothing to act on.
