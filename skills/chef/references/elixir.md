# Elixir

Verified against Elixir 1.20.5, Credo 1.7.19, Dialyxir 1.4.9, ExCoveralls 0.18.5, Mox 1.3.2, StreamData 1.4.0 (Nov 2026).

## Lint and format: mix format + Credo

`.formatter.exs`:

```elixir
[
  inputs: ["{mix,.formatter}.exs", "{config,lib,test}/**/*.{ex,exs}"],
  import_deps: [:ecto, :phoenix],
  line_length: 100
]
```

`mix.exs`:

```elixir
def project do
  [
    elixirc_options: [warnings_as_errors: true],
    test_coverage: [tool: ExCoveralls],
    dialyzer: [plt_add_apps: [:mix, :ex_unit], flags: [:error_handling, :extra_return, :missing_return, :underspecs]]
  ]
end
```

CI: `mix format --check-formatted`, `mix compile --warnings-as-errors`, `mix credo --strict`, `mix dialyzer`. Generate `.credo.exs` with `mix credo gen.config`.

## Types

- Explicit types: `@spec` on every public and private function, `@type t :: %__MODULE__{...}` on every struct. Dialyzer (via `dialyxir`) checks them.
  ```elixir
  @spec withdraw(Account.t(), pos_integer()) :: {:ok, Account.t()} | {:error, :insufficient_funds}
  ```
- Elixir's built-in type checker (1.17+, inference of all constructs in 1.20) runs at compile time; with `warnings_as_errors` its violations fail the build. It does not read `@spec` yet, so keep both.
- `@enforce_keys` on structs. No `any()` or `term()` in specs unless the value is truly unknown.

## Code

- Return `{:ok, value}` / `{:error, reason}`; chain with `with`. Raise only for bugs (`!` functions).
- Pattern match in function heads and guards instead of `if`/`cond` chains.
- Pure functions in the core; side effects (Repo, HTTP, time) at the edges, passed in or behind a behaviour.
- Mocks only through behaviours, with Mox. Never mock a module you do not own.
- Supervise every process. No bare `spawn`. Name GenServers by purpose.
- `@moduledoc` / `@doc` only on a library's public API. Internal modules: `@moduledoc false` (satisfies Credo's `ModuleDoc` check).

## Tests

- ExUnit with `async: true` where tests share no state. `describe` per function.
- Integration: Ecto SQL Sandbox against a real database in a container; `Bypass` or `Req.Test` for HTTP.
- Property tests with StreamData for parsers and pure logic.
- Coverage: excoveralls with a gate in `coveralls.json`:
  ```json
  { "coverage_options": { "minimum_coverage": 90 } }
  ```
  Run `mix coveralls` (exits non-zero under the minimum). Erlang `cover` measures lines only; there is no branch coverage, so test each clause.
- Run tests with `mix test --warnings-as-errors`.
- Mutation testing: muzak exists but is unmaintained (last release 2022); use it only on critical modules and only if the user agrees.

Order before done: `mix format` then `mix compile --warnings-as-errors` then `mix credo --strict` then `mix dialyzer` then `mix coveralls`.
