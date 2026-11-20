# R

Packages follow the standard layout (`DESCRIPTION`, `R/`, `tests/testthat/`). Pin dependencies with `renv` (`renv.lock` committed). Written in Nov 2026 (not benchmarked): lintr 3.4.0, Air 0.13.0; check current ones with `packageVersion("lintr")` and `air --version`.

## Lint and format: lintr, Air

Air (Posit) formats; `usethis::use_air()` sets it up. `air.toml`:

```toml
[format]
line-width = 100
indent-width = 2
```

lintr checks. `.lintr` (DCF format):

```
linters: linters_with_defaults(
    line_length_linter(100L),
    cyclocomp_linter(10L)
  )
error_on_lint: TRUE
```

`cyclocomp_linter()` needs the `cyclocomp` package installed (it is no longer a hard dependency of lintr). CI: `air format . --check`, then `Rscript -e 'lintr::lint_package()'`. If a lintr formatting linter disagrees with Air's output, disable that linter in `.lintr` with the reason (Air owns layout); never use `# nolint`.

## Code

- R has no type annotations. Check argument types at function entry instead: `stopifnot(is.numeric(amount), length(amount) == 1L)`, or `checkmate::assert_number(amount, lower = 0)` if the project already uses checkmate.
- Integer literals carry the `L` suffix: `count <- 0L`. Name constants at the top of the file: `MAX_RETRIES <- 3L`.
- `<-` for assignment, `snake_case` names (lintr defaults).
- Pure functions; pass I/O and time (`Sys.time`) in as arguments so tests can replace them.
- No `<<-`, no `attach()`, no `setwd()` in package code. Use `withr::local_*` to change global state temporarily.
- Signal errors with classed conditions (`rlang::abort(class = "insufficient_funds")`). Prevent errors with checks first; use `tryCatch` only around calls that can fail outside your control (files, network), catching the specific class.
- Roxygen docs only on exported functions of a package other projects use.

## Tests

- testthat 3rd edition (`Config/testthat/edition: 3` in `DESCRIPTION`).
- Test names state the behavior in plain words:
  ```r
  test_that("withdraw with insufficient funds errors", {
    account <- new_account(balance = 10L)
    expect_error(withdraw(account, 20L), class = "insufficient_funds")
  })
  ```
- Snapshot tests (`expect_snapshot()`) for printed output and error messages.
- Coverage with covr, gated in CI:
  ```r
  MIN_COVERAGE_PERCENT <- 90
  coverage <- covr::package_coverage()
  stopifnot(covr::percent_coverage(coverage) >= MIN_COVERAGE_PERCENT)
  ```
  covr measures line (expression) coverage, not branch coverage: cover each branch with its own test.
- Mock with `testthat::local_mocked_bindings()` at boundaries only.

Order before done: `air format .` then lintr then `devtools::test()` then covr.
