# Zig

Verified against Zig 0.17.1 (Nov 2026). Zig is pre-1.0: the standard library and build API break between minor versions. Pin the version in `build.zig.zon` (`.minimum_zig_version`) and check the current one at https://ziglang.org/download/ (or `index.json` there). Read the release notes before an upgrade.

## Lint and format: zig fmt + the compiler

- Format with `zig fmt`; CI runs `zig fmt --check .`.
- There is no official linter. The compiler is strict: unused locals, unused parameters and ignored error unions are compile errors. Fix them; do not silence an unused value with `_ = x;` unless the value is really meant to be discarded.
- `zig ast-check file.zig` catches syntax and AstGen errors without a full build.
- ZLint (community, `zlint.json`) exists. It allows inline `// zlint-disable` comments: never use them (see SKILL.md). Rule set not verified here; ask the user before adding it.
- Build in CI with every mode you ship: `zig build -Doptimize=Debug` and `-Doptimize=ReleaseSafe` (safety checks on).

## Code

- Explicit types (see SKILL.md): `const max_retries: u8 = 3;`, `var total: u64 = 0;`, `fn parse(input: []const u8) ParseError!Header`. Struct literals take the type from the declaration: `const origin: Point = .{ .x = 0, .y = 0 };`.
- Errors are values. Return an explicit error set (`error{ InsufficientFunds, AccountClosed }!Balance`), not `anyerror`.
- `try` propagates an error; it is not an exception handler. Use `catch` only where you can act on the error, never `catch unreachable` on input you do not control.
- Pass an `std.mem.Allocator` to every function that allocates. Free with `defer` / `errdefer` right after the allocation.
- Since 0.16, all I/O goes through an `std.Io` instance. Pass `io: std.Io` as a parameter, like the allocator, so tests can inject it. `main` can take `std.process.Init` to get one.
- No globals with mutable state. Use `comptime` for constants and generics, not for clever metaprogramming.
- Doc comments (`///`, `//!`) only on a library's public API (see SKILL.md).

```zig
const InsufficientFunds = error{InsufficientFunds};

pub fn withdraw(balance: u64, amount: u64) InsufficientFunds!u64 {
    if (amount > balance) return error.InsufficientFunds;
    return balance - amount;
}
```

## Tests

- Test blocks next to the code; the name is a sentence that states the behavior:
  ```zig
  test "withdraw with insufficient funds returns InsufficientFunds" {
      const balance: u64 = 10;
      const amount: u64 = 20;
      try std.testing.expectError(error.InsufficientFunds, withdraw(balance, amount));
  }
  ```
- Allocate with `std.testing.allocator`: the test runner fails a test that leaks.
- Wire tests in `build.zig` with `b.addTest` and a `test` step; run `zig build test`. Put integration tests in a separate step (e.g. `integration-test`) that runs against real services in containers.
- Fuzz parsers with the integrated fuzzer: `std.testing.fuzz` and `zig build test --fuzz`. It is still young.
- Coverage: Zig has no built-in coverage tool. kcov on the test binary is the common choice (unverified as official; check kcov's docs for Zig/DWARF support). Gate at 90% in CI.
- No mutation testing tool known for Zig (unverified).

Order before done: `zig fmt .` then `zig build` then `zig build test`.
