# Erlang/OTP

Verified against Erlang/OTP 29 (29.0 released May 2026), rebar3 3.28.0, erlfmt 1.9.0, elvis_core / rebar3_lint 6.0.0, ELP 2026-11-16, PropEr 1.5.0 (Nov 2026). Current versions: https://www.erlang.org/downloads, hex.pm for packages. Pin OTP in `.tool-versions` (asdf/mise) and in CI.

## Lint and format: compiler + erlfmt + Elvis + Dialyzer + eqWAlizer

`rebar.config`:

```erlang
{erl_opts, [debug_info, warnings_as_errors, warn_missing_spec_all]}.
{project_plugins, [erlfmt, rebar3_lint]}.
{erlfmt, [write]}.
{dialyzer, [{warnings, [unmatched_returns, error_handling, underspecs, extra_return, missing_return]}]}.
{xref_checks, [undefined_function_calls, undefined_functions, locals_not_used, deprecated_function_calls]}.
{cover_enabled, true}.
{cover_opts, [verbose, {min_coverage, 90}]}.
```

- `warn_missing_spec_all` makes a missing `-spec` on any function, exported or not, a build error.
- OTP 29 warns by default on old-style `catch Expr`, `and`/`or`, and `{a,B} = {X,Y}` matches. Fix the code; never add the `nowarn_*` options.
- Format: `rebar3 fmt`; CI runs `rebar3 fmt --check`.
- Lint: `rebar3 lint` (Elvis). With no `elvis` config it uses the default rulesets, which include `no_catch_expressions`, `no_throw`, `no_import` and `no_receive_without_timeout`. None of the default `erl_files` rules contradict a house rule.
- Types: `rebar3 dialyzer` always. eqWAlizer (a stricter type checker, now shipped inside ELP) adds `elp eqwalize-all`; it needs the `eqwalizer_support` dependency.
- `rebar3 xref` for undefined and unused calls.

## Code

- Explicit types (see SKILL.md): `-spec` on every function, `-type` for every domain value, `-opaque` to hide representation. Erlang cannot type a variable, so the spec is the nearest place.
  ```erlang
  -type amount() :: non_neg_integer().
  -spec withdraw(amount(), amount()) -> {ok, amount()} | {error, insufficient_funds}.
  withdraw(Balance, Amount) when Amount > Balance -> {error, insufficient_funds};
  withdraw(Balance, Amount) -> {ok, Balance - Amount}.
  ```
- Return `{ok, Value}` / `{error, Reason}` for expected failures. Let unexpected ones crash; the supervisor restarts the process. `try ... catch Class:Reason` only around a call you cannot check first.
- Every process under a supervisor (`gen_server`, `gen_statem`, `supervisor`). No bare `spawn`. Every `receive` has an `after` timeout.
- Pass time and I/O in (as arguments or a behaviour module) so tests can replace them.
- Name constants with macros (`-define(MAX_RETRIES, 3).`), not literals in logic.
- `-moduledoc` / `-doc` only on a library's public API (see SKILL.md).

## Tests

- EUnit for units; a test is a function ending in `_test`, named for the behavior:
  ```erlang
  withdraw_with_insufficient_funds_returns_error_test() ->
      ?assertEqual({error, insufficient_funds}, withdraw(?SMALL_BALANCE, ?LARGE_AMOUNT)).
  ```
- Common Test (`rebar3 ct`) for integration, against real services in containers.
- Property tests with PropEr (`rebar3_proper` plugin) for pure logic and codecs.
- Coverage: `rebar3 eunit --cover` and `rebar3 ct --cover`, then `rebar3 cover` fails under `min_coverage`. Erlang `cover` measures lines only, no branches: test every clause.
- No maintained mutation testing tool known for Erlang (unverified).

Order before done: `rebar3 fmt` then `rebar3 compile` then `rebar3 lint` then `rebar3 xref` then `rebar3 dialyzer` then `rebar3 do eunit --cover, ct --cover, cover`.
