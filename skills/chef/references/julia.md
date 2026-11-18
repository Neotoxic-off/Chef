# Julia

One package per project (`Project.toml`, `Manifest.toml` committed for applications). Verified Nov 2026: Runic.jl 1.13, JET.jl 0.13, Aqua.jl 0.8; check current ones with `Pkg.status()` or the package's GitHub releases. JET supports a narrow range of Julia versions: match it to yours.

## Lint and format: Runic, JET, Aqua

- Format with Runic (no configuration, like gofmt). Install it as an app: `julia -e 'using Pkg; Pkg.Apps.add("Runic")'`. CI: `runic --check --diff src/ test/`.
- JuliaFormatter is the configurable alternative; keep whichever the project already uses.
- Static checks run as tests, so a finding fails CI:
  ```julia
  using Aqua: Aqua
  using JET: JET
  using MyPackage: MyPackage

  @testset "package quality" begin
      Aqua.test_all(MyPackage)
      JET.test_package(MyPackage; target_modules = (MyPackage,))
  end
  ```
  Aqua finds ambiguities, unbound type parameters, stale dependencies and piracy. JET finds type errors and missing methods; `target_modules` keeps reports to your own code.

## Code

- Type every declaration (see SKILL.md): arguments, returns, fields, and locals.
  ```julia
  struct Account
      balance::Int
  end

  function withdraw(account::Account, amount::Int)::Account
      remaining::Int = account.balance - amount
      remaining < 0 && throw(InsufficientFunds(amount))
      return Account(remaining)
  end
  ```
- Concrete field types in structs; abstract field types make code slow.
- Prevent errors instead of catching them: `tryparse`, `get(dict, key, default)`, `haskey`, `isnothing`. `try`/`catch` only around I/O, catching a specific exception type and rethrowing the rest.
- Define your own exception types (`struct InsufficientFunds <: Exception`); never `error("...")` for conditions callers must handle.
- `using Module: name` with explicit names; no bare `using` in package code.
- No mutable globals; name constants with `const`. Whether `const` accepts a type annotation depends on the Julia version (not verified): if it does not, write the type in the value (`const MAX_RETRIES = Int32(3)`). Pass I/O, clock and RNG (`rng::AbstractRNG`) as arguments.
- Docstrings only on the exported API of a package other projects use.

## Tests

- `Test` stdlib, run with `Pkg.test()`. Test set names state the behavior:
  ```julia
  @testset "withdraw with insufficient funds throws" begin
      account::Account = Account(10)
      @test_throws InsufficientFunds withdraw(account, 20)
  end
  ```
- Coverage: `Pkg.test(coverage = true)`, then process with Coverage.jl or LocalCoverage.jl and gate at 90% in CI. Julia reports line coverage only: cover each branch with its own test.
- `@inferred` to assert a hot function is type-stable.
- Pass a seeded `StableRNG` (StableRNGs.jl) to code that uses randomness, so results do not change across Julia versions.

Order before done: `runic --inplace src/ test/` then `Pkg.test(coverage = true)` (includes Aqua and JET).
