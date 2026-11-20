# WebAssembly

Read with the source language file (`rust.md`, `c.md`, `cpp.md`); all its rules apply. Written in Nov 2026 (not benchmarked): wasm-bindgen 0.2.130 and wasm-pack 0.15 (both now under the `wasm-bindgen` GitHub org, after the rustwasm org was archived in 2025), Wasmtime 50, wasi-sdk 34, Binaryen 133. Check with `wasm-bindgen --version`, `wasmtime --version`, and the GitHub releases.

## Targets

| Runs in | Rust target | C/C++ toolchain |
|---|---|---|
| Browser / JS host | `wasm32-unknown-unknown` + wasm-bindgen | Emscripten (`emcc`) |
| WASI runtime, core module | `wasm32-wasip1` | wasi-sdk (`clang --target=wasm32-wasip1`) |
| WASI 0.2 component | `wasm32-wasip2` (tier 2) | wasi-sdk (`--target=wasm32-wasip2`) |

Pick the target from where the module runs; do not mix wasm-bindgen into a WASI module.

## Lint and format

- Same linters as the source language, run for the wasm target too: `cargo clippy --target wasm32-unknown-unknown --all-targets -- -D warnings`.
- Not verified: whether `#[wasm_bindgen]` expansion trips `unsafe_code = "forbid"` from `rust.md` with your wasm-bindgen version. If it does, tell the user; do not add `#[allow]`.
- Validate output: `wasm-tools validate pkg/*.wasm` (Bytecode Alliance wasm-tools).

## Size

`Cargo.toml`:

```toml
[profile.release]
opt-level = "z"
lto = true
codegen-units = 1
panic = "abort"
strip = true
```

- Then `wasm-opt -Oz` (Binaryen); wasm-pack runs it by default in release builds.
- Measure before and after; track the `.wasm` size in CI and fail on a set budget.
- Avoid `format!` and panicking paths in hot exports; each pulls in formatting code. Prefer small dependencies with `default-features = false`.
- C: `-Oz`, `-flto`, and no `printf` family in the module unless needed.

## Code

- Keep the boundary thin: plain functions taking and returning numbers, strings or typed structs. Business logic stays in a normal crate/library tested natively.
- Every value from JS or the host is untrusted: validate lengths and ranges at the export.
- Return `Result<T, JsError>` from wasm-bindgen exports instead of panicking; JS sees a thrown `Error`.
- Install `console_error_panic_hook` only in debug builds.
- Explicit types on the exported signatures and in the generated `.d.ts` consumers (see `typescript.md`).
- WASI: request only the capabilities you need (preopened dirs, env vars) when you run the module.

## Tests

- Logic: native `cargo test` / `ctest` on the host, with the usual coverage gate.
- Browser bindings: `wasm-bindgen-test` with the runner in `.cargo/config.toml`:
  ```toml
  [target.wasm32-unknown-unknown]
  runner = "wasm-bindgen-test-runner"
  ```
  Run `cargo test --target wasm32-unknown-unknown`, or `wasm-pack test --headless --chrome --firefox`.
- WASI: set `runner = "wasmtime"` for `wasm32-wasip1`/`wasip2` and run `cargo test --target wasm32-wasip1`.
- One end-to-end test loads the built package from JS (Vitest or Node's test runner) and calls each export.

Order before done: format, clippy for native and wasm targets, native tests, wasm tests, release build, size check.
