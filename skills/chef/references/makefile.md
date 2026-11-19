# Make and task runners (just, Task)

Verified against GNU Make 4.4.1, just 1.59, Task 3.54, checkmake 0.3 (Nov 2026).

## Lint and validate

- Make: `checkmake Makefile` for style; `make -n <target>` shows commands without running them.
- just: `just --fmt --check` fails and prints a diff when the justfile is not formatted; `just --list` must show every public recipe.
- Task: add `# yaml-language-server: $schema=https://taskfile.dev/schema.json` to `Taskfile.yml`; validate in CI with `check-jsonschema --schemafile https://taskfile.dev/schema.json Taskfile.yml`.

## Practices

- Pick one runner per repo. Make for C/C++ and file-based builds; just or Task for a project command menu.
- The runner wraps the real tools (`npm`, `cargo`, `dotnet`, `go`); it holds no logic that CI cannot reproduce. CI calls the same targets developers use.
- Standard names: `build`, `test`, `lint`, `fmt`, `check` (all gates), `clean`. The default target prints help or runs `check`.
- Make: declare every non-file target `.PHONY`; use real file targets and prerequisites for incremental builds.
- Make: recipes run one shell per line; join dependent lines with `&&` or use `.ONESHELL`.
- Task: use `sources`/`generates` for incremental tasks, `deps` for parallel prerequisites.
- Long logic goes in a script under `scripts/` with its own lint and tests, not in a 30-line recipe.

```make
SHELL := bash
.SHELLFLAGS := -euo pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables --no-builtin-rules

.PHONY: check lint test
check: lint test
lint:
	ruff check .
test:
	pytest
```

```just
set shell := ["bash", "-euo", "pipefail", "-c"]

check: lint test
lint:
    ruff check .
test:
    pytest
```

## Security

- Never hide a failure: no `-` prefix on recipe lines, no `|| true`, no `2>/dev/null` on commands that can fail. Fix the cause.
- No secrets in Makefiles, justfiles or Taskfiles. Read them from the environment or a secret manager at run time; do not commit `.env` (`set dotenv-load` reads it, it must stay untracked).
- Quote variables passed to the shell; do not interpolate user input into recipes.
- Do not `curl | sh` installers in a recipe; pin tool versions and verify checksums.

## Tests

- CI runs `make check` / `just check` / `task check` on every PR, on each OS you support.
- CI checks the runner file itself: `just --fmt --check`, Taskfile schema check, `checkmake`.
- A clean clone must pass `check` with only the documented prerequisites installed.
