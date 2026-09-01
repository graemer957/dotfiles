---
paths:
  - "**/*.md"
---

# Markdown

- Markdown linting is `rumdl`; the PostToolUse markdown hook runs it on every
  file an edit touches, and the hook's `DISABLES` mapping is the single home
  of the per-path disable lists — take the `-d` list from there when running
  `rumdl` by hand, since a bare invocation reports findings the mapping
  exempts.
- In an existing file, fix the findings your edit introduced or touched and
  flag pre-existing ones elsewhere rather than fixing them, since that widens
  the diff beyond the change under review. A new file passes clean.
- A repo shipping its own `rumdl` config governs from there. The tool is
  required on this machine: when `rumdl` isn't on PATH, stop and report the
  missing tool instead of handing back unlinted work.
