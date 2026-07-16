---
paths:
  - "**/*.rs"
---

# Rust

- Code whose job is to visit every field of a struct — manual `Debug`/serialise impls, mappers, `From`/conversion fns — opens with exhaustive destructuring (`let Self { a, b, c } = self;`, no `..` rest pattern), so a new field becomes a compile error (E0027) at every site that must decide about it. Same-crate types only: foreign `#[non_exhaustive]` structs force `..`, surrendering the guard. Not for ordinary field access — noise.
