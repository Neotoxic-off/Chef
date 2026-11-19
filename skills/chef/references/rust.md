# Rust

Verified against Rust 1.100, cargo-nextest 0.9.152, cargo-llvm-cov 0.9.1, cargo-mutants 27.1, proptest 1.12, cargo-deny 0.21, cargo-audit 0.23 (Nov 2026).

## Cargo.toml

- `edition = "2024"` and `rust-version = "<MSRV>"` in `[package]` (or `[workspace.package]`). CI builds once with the MSRV toolchain.
- Commit `Cargo.lock` for binaries. Optional cooldown against fresh malicious releases (Rust 1.100+), in `.cargo/config.toml`: `[registry] global-min-publish-age = "3 days"`.

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

## Unsafe

- Default is `forbid`. Code that truly needs `unsafe` (FFI, a hand-written data structure) goes in its own small workspace crate, after asking the user. Only that crate's `[lints.rust]` drops `unsafe_code`, with the reason on the line above; every other crate keeps `forbid`.
- `deny` instead of `forbid` only helps if code opts out with `#[allow(unsafe_code)]`, which is a suppression attribute: do not use it.
- Every `unsafe` block has a `// SAFETY:` comment saying which invariant makes it sound. Enforce it in `[lints.clippy]`: `undocumented_unsafe_blocks = "warn"`, `multiple_unsafe_ops_per_block = "warn"`, `unnecessary_safety_comment = "warn"`.
- `unsafe fn` bodies still wrap each unsafe op in `unsafe {}` (`unsafe_op_in_unsafe_fn`, warn by default in edition 2024). Run its tests under Miri (`cargo +nightly miri test`).

## Supply chain

- `cargo deny check` in CI (advisories, licenses, bans, sources); config in `deny.toml` from `cargo deny init`. GitHub: `EmbarkStudios/cargo-deny-action`.
- Without cargo-deny, `cargo audit` (RustSec advisories only). Both fail on a vulnerable dependency: upgrade it, never ignore the advisory on your own.

## Code

- Type every function signature and public field; let `let` bindings and closures infer when the type is obvious.
- Errors: `Result` with `thiserror` in libraries, `anyhow` in binaries. No `unwrap()`/`expect()` outside tests.
- Small modules, traits for seams that tests need to replace.
- Newtypes for domain values (`struct UserId(u64)`), not bare primitives.

## Tests

- Unit tests in `#[cfg(test)] mod tests` next to the code; integration tests in `tests/`.
- Runner: `cargo nextest run`. Nextest does not run doctests, so also run `cargo test --doc`.
- Coverage: `cargo llvm-cov nextest --lcov --output-path lcov.info` (needs the `llvm-tools-preview` component). Gate with `--fail-under-lines 90`.
- Property tests: `proptest`. Mutation testing: `cargo-mutants`.
