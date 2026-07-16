---
paths:
  - "**/*.tsx"
  - "**/*.jsx"
---

# React

- If a value can be computed from existing state or props, derive it during render — never store a second copy kept in sync by an effect. The mirrored copy buys an extra render, a stale-value window, and a reset obligation; the derived form can't have those bugs. The tell: a state setter inside an effect whose only job is to track another value.
