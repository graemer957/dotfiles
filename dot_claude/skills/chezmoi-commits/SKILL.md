---
name: chezmoi-commits
description: >-
  Split the pending changes in the chezmoi source tree into small, distinct
  commits with house-style subjects — one concern per commit, subject only —
  and hand back a table of the proposed commits for approval before any
  commit lands. Use on /chezmoi-commits after editing dotfiles, skills,
  rules or hooks that chezmoi manages.
disable-model-invocation: true
model: opus
---

# Chezmoi commits

## Scope

Everything pending in the chezmoi source tree: staged, unstaged and
untracked. The source tree is rarely the session cwd, so every git command
runs as `git -C <src>` with `<src>` from `chezmoi source-path`.

## Definitions

House style is what the repo's own log shows (`git log --oneline -40`); when
the log and this list disagree, the log wins.

- The subject is the whole message: the change is small enough for one line
  to carry it, and the diff carries the rest.
- Imperative mood, the verb first and bare (`Add`, `Drop`, `Fix`, `Require`,
  `Skip`), under about 60 characters.
- The why follows a colon when it fits: `Skip the retry prompt: two custom
  steps fail on purpose as a signal`.
- Backticks around every command, identifier, filename and flag.
- One concern per commit: a change plus the files that exist only because of
  it (a hook with its test, a skill with its supporting file).

## Workflow

1. Run `pending.sh` (beside this file) for the status, the diff against
   `HEAD` and every untracked file in full.
2. Group hunks by the problem they close, not by directory. Order the groups
   so each commit leaves the tree coherent: a hook before the rule that names
   it, a function before the alias that calls it. A file whose hunks serve two
   groups is split at commit time: write the wanted hunks, diff header
   intact, to a patch file and `git apply --cached` it.
3. Hand back the table (Output format) and stop for the go-ahead: the table
   is the review surface, and a subject is cheaper to fix there than after it
   is signed.
4. On the go, for each row in order: `git -C <src> add <files>`, then
   `git -C <src> commit -F <file>` with the subject written to `<file>` first
   (backticks in a `-m` string get command-substituted). Commits are signed
   through the 1Password agent, so run each in the foreground and wait for
   its prompt; a failed prompt leaves `HEAD` unchanged, so stop and hand that
   row back.
5. Close with `git -C <src> log --oneline -<rows>`.

## Output format

```markdown
| # | Subject | Files |
| - | ------- | ----- |
| 1 | Add `cargo_targets` to list Cargo `target/` dirs by size | `functions/cargo_targets.fish` |
| 2 | Gate `rsync` and download-to-file writes | `hooks/executable_bcp-instruction-gate.py`, `hooks/executable_bcp-instruction-gate.test.sh` |

Commit in this order?
```

Each file shows its last two path components — widen only when two would otherwise render alike; `git add` in step 4 still takes the full source path.

A file split across rows carries `(part)` after its name in each.

## Boundaries

- Don't commit before the go-ahead.
- Don't add a body or a trailer.
- Don't `chezmoi apply` or `chezmoi add`: syncing source and live files is
  the user's step, before or after the commits.
- Don't push; the remote moves on an explicit ask.
- Don't amend or rebase to fix a grouping after the fact: a wrong commit is
  followed by a correcting one, or reverted by the user.

## Improving this skill

Skills decay. If while running this one you find something that would have
sped you up or contradicts what's written here — a subject the log's style
contradicts, a `chezmoi` or `git` invocation that rotted, a grouping rule
that produced a commit the user re-split, a signing step that misbehaved —
surface a proposed edit before moving on:

1. Draft the diff for this file in chat (lines + one-line why).
2. Wait for the user's go-ahead.
3. Edit the chezmoi source, then hand to the user to `chezmoi apply` before
   continuing.

Don't batch corrections across runs — surface each one the moment you spot
it.

Before the final hand-back, look back over this run's tool calls for a
mechanical sequence: commands with no decision between them. One qualifies
for a script when this file prescribes it, when it ran three times this run,
or when it did arithmetic or tallying by hand; a script runs identically
every time, where prose drifts. Propose a qualifying sequence through the
steps above, choosing what to build from `authoring.md`. Record the outcome
in this skill's Mechanical cell in the personal skill ledger whenever it
changes, a first check that finds nothing included.
