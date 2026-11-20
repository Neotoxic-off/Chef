# Python minor-version upgrade

Builds on `python.md`. Written for Python 3.15.2 and 3.14.10 (python.org), the "What's New" pages for 3.12-3.15, pyupgrade 3.22.0, Ruff 0.17.5, uv CLI reference (Nov 2026), not benchmarked.

## When it applies

- `requires-python`, `.python-version`, the CI matrix or the Docker base image moves to a newer Python 3.x (e.g. 3.9 to 3.14 or 3.15).
- Check the target's status on `devguide.python.org/versions` and pick a version every dependency supports.

## Tools

- Ruff `UP` (pyupgrade) rules, already in `python.md`. Ruff reads the minimum version from `requires-python` (or `target-version`, values up to `py315`).
- `pyupgrade --py314-plus` (flags up to `--py315-plus`) only if the project uses it instead of Ruff. Do not run both.
- `uv tree --outdated` lists dependencies with newer releases; `uv lock --upgrade-package <name>` upgrades one.

## Steps, one batch per commit

1. Baseline on the current Python: `uv run pytest` run, failures and coverage recorded. Then run the tests with deprecation warnings as errors to see what the new version removes: `uv run pytest -W error::DeprecationWarning`. Fix only warnings from your own code.
2. Dependencies: on the new Python (`uv run --python 3.14 pytest`), find packages with no wheel or no support; upgrade them one per batch with `uv lock --upgrade-package <name>`, still on the old Python where possible.
3. Bump the version: `requires-python`, `.python-version` (`uv python pin 3.14`), CI matrix, Docker image, `uv lock`. Run the full check.
4. Syntax: `uv run ruff check --select UP --fix`, then review the diff. Split by package if it is large. Behavior must not change.
5. Replace removed stdlib modules and APIs (below), one module per batch.

Validation per batch: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy .`, `uv run pytest` (with the coverage gate), on the new Python.

## Removed from the stdlib

- 3.12: `distutils` (PEP 632; use setuptools or packaging), `asynchat` and `asyncore` (use `asyncio`), `imp` (use `importlib`).
- 3.13 (PEP 594 "dead batteries"): `aifc`, `audioop`, `cgi`, `cgitb`, `chunk`, `crypt`, `imghdr`, `mailcap`, `msilib`, `nis`, `nntplib`, `ossaudiodev`, `pipes`, `sndhdr`, `spwd`, `sunau`, `telnetlib`, `uu`, `xdrlib`; also `2to3` / `lib2to3`, `tkinter.tix`, `locale.resetlocale()`, `typing.io` and `typing.re`.
- 3.14 and 3.15: smaller API removals (e.g. 3.15 removes `http.server.CGIHTTPRequestHandler`, `glob.glob0()` / `glob1()`). Read the "Removed" section of each "What's New" crossed.

## Pitfalls

- A package with C extensions may have no wheel for the new Python yet: that blocks the upgrade; report it.
- `UP` fixes on a library still supporting old Pythons break those users: `requires-python` must change first.
- `typing` rewrites (`List` to `list`, `Optional[X]` to `X | None`) are the migration; reformatting unrelated code is not.
- If both `target-version` and `requires-python` are set, Ruff uses `target-version`: bump both, or drop `target-version`.
- Recreate the virtual environment for the new Python (`uv sync`); never copy the old one.

## Leave for the user

- The target version and the dropped versions (a library's users).
- Replacements for removed modules with no stdlib successor (e.g. `cgi`, `telnetlib`, `crypt`): new dependencies need the user's yes.
