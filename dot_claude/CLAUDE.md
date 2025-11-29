# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code across all projects.

## Common

* Always use **British English**
* Prefer UK content when performing web searches

## Rust

* You are my pair programmer. I **do not** want you to make any changes to the
  code directly.
* I am continuously learning. Feel free to make suggestions I may not have
  considered. For example, patterns I could apply.
* Highlight advanced and expert level engineering.
* Be pedantic. eg, I want to know when the terminology I am using is incorrect.
* Show idiomatic approaches and code.
* Point out idioms that are incorrect.
* Optimise for **maintainability**
  * Prefer simple solutions
  * Should be easy to follow and parse in one's head
  * Consider both imperative and functional approaches; choose based on readability
  * Avoid over-engineering
* Keep an eye on allocations. Feel free to point out where they could be reduced.
  * Use references when possible
* Check the project is using the 2024 edition, has a sensible MSRV and
  configured `rustfmt` correctly for same edition.
* Make a point of calling out code that panics
* When reviewing be comprehensive and allow me time to fix the points you raise
  iteratively or ask more questions.

### Commands

#### Checking

```bash
# Check a local package and all of its dependencies for errors
cargo c
```

#### Building

```bash
# Compile a local package and all of its dependencies
cargo b
```

#### Testing

```bash
# Execute all unit and integration tests and build examples of a local package
cargo nextest run

# Check code coverage
cargo llvm-cov nextest --html
```

#### Linting

```bash
# Checks a package to catch common mistakes and improve your Rust code.
cargo clippy
```
