# Rust

## Lint and format

- `cargo fmt --check` in CI.
- Clippy with pedantic lints, warnings as errors. In `Cargo.toml`:
  ```toml
  [lints.rust]
  unsafe_code = "forbid"

  [lints.clippy]
  pedantic = { level = "warn", priority = -1 }
  unwrap_used = "warn"
  expect_used = "warn"
  ```
  CI: `cargo clippy --all-targets --all-features -- -D warnings`.

## Code

- Explicit types on every `let` and closure (see SKILL.md).
- Errors: `Result` with `thiserror` in libraries, `anyhow` in binaries. No `unwrap()`/`expect()` outside tests.
- Small modules, traits for seams that tests need to replace.
- Newtypes for domain values (`struct UserId(u64)`), not bare primitives.

## Tests

- Unit tests in `#[cfg(test)] mod tests` next to the code; integration tests in `tests/`.
- Runner: `cargo nextest run`. Nextest does not run doctests, so also run `cargo test --doc`.
- Coverage: `cargo llvm-cov nextest --lcov --output-path lcov.info` (needs the `llvm-tools-preview` component). Gate with `--fail-under-lines 90`.
- Property tests: `proptest`. Mutation testing: `cargo-mutants`.
