# Python

Verified against uv 0.13, Ruff 0.17, mypy 2.4, pytest 9.2, pytest-cov 7.1, Hypothesis 6.170, mutmut 3.8 (Nov 2026).

All tool configuration lives in `pyproject.toml`. Use `uv` for environments and dependencies (`uv.lock` committed); run tools with `uv run`.

## Lint and format: Ruff

```toml
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "UP", "N", "SIM", "C4", "RET", "PTH", "ANN", "S", "PL", "RUF"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]  # assert is how pytest checks
```

`ANN` enforces type annotations on every function.

## Types

- mypy `--strict` in CI; Pyright strict in the editor.
  ```toml
  [tool.mypy]
  strict = true
  ```
- Annotate every parameter, return and attribute; annotate a local only when mypy cannot infer it. No `Any`; use `object` and narrow, or a `Protocol`.
- Data: `@dataclass(frozen=True, slots=True)`, or pydantic models at I/O boundaries to validate input.

## Code

- `pathlib` over `os.path`. f-strings. Context managers for resources.
- No mutable default arguments. No bare `except:`.
- Inject I/O and time through parameters so logic stays pure.

## Tests

- pytest with fixtures; `pytest-cov` with branch coverage and a hard gate:
  ```toml
  [tool.pytest.ini_options]
  addopts = "--cov --cov-branch --cov-report=term-missing:skip-covered --cov-fail-under=90"
  ```
- `--cov` in `addopts` needs `pytest-cov` in the dev dependencies, or every `pytest` run fails where it is missing.
- Mark slow tests: `@pytest.mark.integration`; integration with `testcontainers`.
- Property-based tests with Hypothesis for parsers and pure logic.
- Mutation testing: mutmut.

Check before done, in one call so every failure shows at once and any failure fails the call: `rc=0; uv run ruff check --fix --output-format concise . || rc=1; uv run ruff format . || rc=1; uv run mypy . || rc=1; uv run pytest -q || rc=1; [ "$rc" -eq 0 ]`.
