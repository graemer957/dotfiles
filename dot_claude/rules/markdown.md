---
paths:
  - "**/*.md"
---

# Markdown

- Run `rumdl check` on every Markdown file you create or edit, before handing the work back — nothing else in the loop lints these files, so drift accumulates invisibly. A new file passes clean; in an existing file, fix the findings your edit introduced or touched and flag pre-existing ones elsewhere rather than fixing them, since that widens the diff beyond the change under review. The tool is required on this machine: when `rumdl` isn't on PATH, stop and report the missing tool instead of handing back unlinted work.
- Personal Markdown — memory files, skills, rules, Obsidian notes — relaxes line length (`rumdl check -d MD013`): these files use single long prose lines and leave wrapping to the viewer. Memory topic files and `MEMORY.md` additionally relax the leading-heading rule (`-d MD013,MD041`): they open with YAML frontmatter and carry no H1 by design. The relaxations ride the command because `rumdl` discovers config files only from the working directory, never the checked file's ancestors. Repo Markdown runs bare `rumdl check`, leaving each repo's own config in charge.
