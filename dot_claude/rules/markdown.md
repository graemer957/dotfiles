---
paths:
  - "**/*.md"
---

# Markdown

- Run `rumdl check -d MD013` on every Markdown file you create or edit, before handing the work back — nothing else in the loop lints these files, so drift accumulates invisibly. Line length is off everywhere: we soft-wrap and leave wrapping to the viewer. A new file passes clean; in an existing file, fix the findings your edit introduced or touched and flag pre-existing ones elsewhere rather than fixing them, since that widens the diff beyond the change under review. A repo shipping its own `rumdl` config governs from there. The tool is required on this machine: when `rumdl` isn't on PATH, stop and report the missing tool instead of handing back unlinted work.
- Three kinds relax further, on one cumulative `-d` list, because `rumdl` discovers config files only from the working directory, never the checked file's ancestors:
  - Memory topic files (`-d MD013,MD041`): they open with YAML frontmatter and carry no H1 by design.
  - `MEMORY.md` (`-d MD013,MD022,MD032,MD041`): the index carries no H1, and its band headings sit flush against the lists either side — deliberate density in a file loaded into context every session.
  - Obsidian notes (`-d MD013,MD025,MD032`): vault notes use H1 section headings and lists flush under their headings by design.
