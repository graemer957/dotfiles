---
paths:
  - "**/*.rs"
  - "**/Cargo.toml"
---

# Rust

- Code whose job is to visit every field of a struct — manual `Debug`/serialise impls, mappers, `From`/conversion fns — opens with exhaustive destructuring (`let Self { a, b, c } = self;`, no `..` rest pattern), so a new field becomes a compile error (E0027) at every site that must decide about it. Same-crate types only: foreign `#[non_exhaustive]` structs force `..`, surrendering the guard. Not for ordinary field access — noise.
- Refer to traits and types by `use`-imported short name (`T: Debug`, not `T: std::fmt::Debug`) — a fully-qualified path in a signature or bound usually signals a missing import. Qualify only to break a real name collision (e.g. a crate's own `Result` beside `std`'s) or in one-off macro/generated contexts. The prelude ships the `#[derive(Debug)]` *macro*, not the `Debug` *trait* — deriving never needs an import; naming the trait always does.
- I'm continuously learning Rust, with focus on: idiomatic patterns, type-system depth (lifetimes, generics, trait bounds), async (futures, tokio, cancellation safety), and performance (allocations, layout, async overhead).
- Highlight idiomatic Rust and expert-level patterns I may not have seen; point out idioms I'm using wrongly.
- Correct my terminology when I'm wrong, even on small points.
- Optimise for **maintainability** — simple, readable solutions; choose imperative vs functional on clarity; avoid over-engineering.
- Keep an eye on allocations. Feel free to point out where they could be reduced.
  - Use references when possible
- Check the project is using the 2024 edition, has a sensible MSRV and configured `rustfmt` correctly for same edition.
- Make a point of calling out code that panics.
- When reviewing be comprehensive and allow me time to fix the points you raise iteratively or ask more questions.

## Commands

These are the bare-`cargo` equivalents. Where a project provides `just` recipes, prefer those.

### Checking

```bash
# Check a local package and all of its dependencies for errors
cargo c
```

### Building

```bash
# Compile a local package and all of its dependencies
cargo b
```

### Testing

```bash
# Execute all unit and integration tests and build examples of a local package
cargo nextest run

# Check code coverage
cargo llvm-cov nextest --html
```

### Linting

```bash
# Checks a package to catch common mistakes and improve your Rust code.
cargo clippy
```
