# OCaml

Verified against OCaml 5.5.2, dune 3.25, ocamlformat 0.29.0, alcotest 1.10, qcheck-core 0.91, bisect_ppx 2.8.3 (Nov 2026). Current versions: `opam show <package>` or https://ocaml.org/p/<package>/latest. Lock dependencies (`opam lock` or dune package management).

## Lint and format: compiler warnings + ocamlformat

- dune's default `dev` profile turns most warnings into errors and adds `-strict-sequence`. CI builds with that profile (`dune build`, no `--profile release`: release keeps warnings non-fatal).
- Add warning 70 (missing `.mli`) as an error, so every module has a typed interface. In the root `dune` file:
  ```dune
  (env
   (dev
    (flags (:standard -w @70))))
  ```
- Never silence a warning with `[@warning "-..."]` or `[@@ocaml.warning]` attributes (see SKILL.md).
- Format with ocamlformat. Pin it in `.ocamlformat` so everyone gets the same output:
  ```
  version = 0.29.0
  profile = default
  ```
  Format with `dune fmt`; CI runs `dune build @fmt`.
- There is no standard linter beyond the compiler. Zanuda exists; rules not verified here, ask the user before adding it.

## Code

- An `.mli` for every module, and annotations on top-level function parameters and returns. Local `let` bindings and closures may rely on inference:
  ```ocaml
  let withdraw (balance : int) (amount : int) : (int, withdraw_error) result =
    if amount > balance then Error Insufficient_funds
    else
      let remaining : int = balance - amount in
      Ok remaining
  ```
- Errors as values: `result` and `option`. Use the `_opt` functions (`List.find_opt`, `int_of_string_opt`, `Hashtbl.find_opt`) instead of catching `Not_found` or `Failure`.
- Exceptions only where the stdlib leaves no choice (I/O). Use `In_channel.with_open_text` / `Fun.protect ~finally` for resources.
- Abstract types in `.mli` to hide representation; smart constructors validate input.
- Exhaustive `match`, no `_ ->` catch-all on your own variants: a new constructor must break the build.
- Doc comments (`(** ... *)`) only in the `.mli` of a library's public API (see SKILL.md).

## Tests

- Alcotest for unit tests; the test name states the behavior:
  ```ocaml
  let test_withdraw_insufficient_funds () : unit =
    Alcotest.(check (result int withdraw_error_testable))
      "same result" (Error Insufficient_funds) (withdraw small_balance large_amount)

  let tests : unit Alcotest.test_case list =
    [ Alcotest.test_case "withdraw with insufficient funds returns Error" `Quick
        test_withdraw_insufficient_funds ]
  ```
- `ppx_expect` for output snapshots. QCheck (via `qcheck-alcotest`) for properties and round-trips.
- Integration tests in their own `test/integration` directory, against real services in containers.
- Coverage with bisect_ppx: add `(instrumentation (backend bisect_ppx))` to each library, then `dune runtest --instrument-with bisect_ppx --force` and `bisect-ppx-report summary`. No built-in threshold: gate in CI by parsing the summary (fail under 90%).
- No maintained mutation testing tool known for OCaml (unverified).

Order before done: `dune fmt` then `dune build` then `dune runtest`.
