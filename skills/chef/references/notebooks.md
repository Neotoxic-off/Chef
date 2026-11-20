# Jupyter notebooks

Builds on `python.md`. Written in November 2026 (not benchmarked) on PyPI: nbqa 1.10, nbstripout 0.9, papermill 2.7, Jupytext 1.19. Check current versions on `https://pypi.org/project/<name>/`.

## What belongs in a notebook

- Exploration, one-off analysis and reports. Not reusable logic.
- Move code into the project package (`src/<package>/`) as soon as it is:
  - used by a second notebook or a script,
  - more than a few lines of logic, or needs a test,
  - run on a schedule or in production.
- The notebook then imports it. Tests cover the package, not the notebook.

```python
%load_ext autoreload
%autoreload 2

from sales_report.metrics import monthly_revenue
from sales_report.settings import ReportSettings

settings: ReportSettings = ReportSettings()
```

## Environment and reproducibility

- The kernel is the project's `uv` environment (`uv add --dev ipykernel`), never a global Python.
- First cell: imports, settings, seed. No hidden state: "Restart and Run All" must succeed before commit.
- Read inputs by pinned version (file hash, snapshot ID), never "latest".
- Paths relative to the project root via `pathlib`; no absolute user paths.

## Git hygiene: nbstripout

- Strip outputs and execution counts before commit; outputs leak data and make diffs unreadable.
- `nbstripout --install` sets a git filter for the repo; in CI or pre-commit use its hook:

```yaml
repos:
  - repo: https://github.com/kynan/nbstripout
    rev: 0.9.2
    hooks:
      - id: nbstripout
```

- Need reviewable diffs? Pair notebooks with Jupytext (`py:percent`) and review the `.py` file.

## Lint and types: Ruff and nbqa

- Ruff lints and formats `.ipynb` directly: the `python.md` commands already cover them.
- Type-check notebooks with nbqa: `uv run nbqa mypy notebooks/`.
- Same rules as any Python: typed signatures, no `warnings.filterwarnings("ignore")`, no `# noqa`.

## Parameterized runs: papermill

- Tag one cell `parameters` with typed defaults; papermill injects overrides after it.
- Scheduled and CI runs execute through papermill, writing the executed copy as a build artifact, never committed.

```bash
uv run papermill notebooks/monthly_report.ipynb "out/monthly_report_${RUN_ID}.ipynb" \
  -p report_month 2026-10 -p data_version "${DATA_VERSION}"
```

- Run each committed notebook in CI with papermill so a broken notebook fails the build.

## Secrets and personal data

- Never paste keys or tokens in a cell. Read them from the environment through the settings class.
- Do not display rows with personal data; show aggregates. Clear such outputs before sharing an executed notebook.
