"""Score the sql task: the agent's migrations on PostgreSQL 18 with hidden data and checks, and sqlfluff findings.

The seed's 001 migration (not the workspace's copy) builds the schema, hidden rows stand for production data,
then every other migration runs in name order and hidden_test.sql raises on any failed check.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import scorer_lib
from score import Metrics

TASK_DIR: Path = Path(__file__).resolve().parent
INITIAL_MIGRATION: str = "001_initial.sql"
POSTGRES_IMAGE: str = "postgres:18.1-alpine3.22@sha256:270579ee277a572fa8cfdbaec0e1ff588bb7247da92d25165c7237c483e565d9"
SQLFLUFF_IMAGE: str = "sqlfluff/sqlfluff:3.4.2@sha256:631e960f9ba8f68beb0cd01f5a788de5eeee340e54fa725faab736345c7a38ed"
# The prompt names the column `month`, a keyword, so RF04 would flag every answer.
SQLFLUFF_EXCLUDED_RULES: str = "RF04"
SQLFLUFF_OK_CODES: frozenset[int] = frozenset({0, 1})
POSTGRES_SCRIPT: str = (
    "set -e; initdb -D /tmp/pg -A trust -U postgres >/dev/null 2>&1;"
    ' pg_ctl -D /tmp/pg -o "-c listen_addresses=" -w -l /tmp/pg.log start >/dev/null;'
    ' for file in "$@"; do psql -X -q -v ON_ERROR_STOP=1 -U postgres -f "$file"; done'
)


def new_migrations(workspace: Path) -> list[str]:
    return sorted(path.name for path in (workspace / "migrations").glob("*.sql") if path.name != INITIAL_MIGRATION)


def hidden_test_passes(copy: Path, migrations: list[str]) -> bool:
    files: list[str] = [
        f"/bench/seed/migrations/{INITIAL_MIGRATION}",
        "/bench/hidden_data.sql",
        *(f"/work/migrations/{name}" for name in migrations),
        "/bench/hidden_test.sql",
    ]
    # The session time zone is not UTC, so a view that truncates in the session's zone gives other months.
    outcome: subprocess.CompletedProcess[str] = scorer_lib.docker_run(
        [
            *("-v", f"{copy}:/work:ro", "-v", f"{TASK_DIR}:/bench:ro", "-e", "PGTZ=America/Los_Angeles"),
            *("--user", "postgres", "--entrypoint", "sh", POSTGRES_IMAGE, "-c", POSTGRES_SCRIPT, "postgres-script"),
            *files,
        ],
        copy,
    )
    return outcome.returncode == 0


def count_sqlfluff_violations(copy: Path, migrations: list[str]) -> int:
    outcome: subprocess.CompletedProcess[str] = scorer_lib.docker_run(
        [
            *("-v", f"{copy}:/work:ro", "-w", "/work", SQLFLUFF_IMAGE, "lint", "--dialect", "postgres"),
            *("--exclude-rules", SQLFLUFF_EXCLUDED_RULES, "--format", "json"),
            *(f"migrations/{name}" for name in migrations),
        ],
        copy,
    )
    if outcome.returncode not in SQLFLUFF_OK_CODES or not outcome.stdout.strip():
        raise RuntimeError(f"sqlfluff failed: {(outcome.stderr or outcome.stdout).strip()[-scorer_lib.ERROR_TAIL_CHARS :]}")
    report: list[dict[str, Any]] = json.loads(outcome.stdout)
    return sum(len(entry["violations"]) for entry in report)


def score(workspace: Path) -> Metrics:
    migrations: list[str] = new_migrations(workspace)
    if not migrations:
        return {"hidden_test_passes": False, "sqlfluff_violations": 0}
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = scorer_lib.copy_workspace(workspace, Path(scratch))
        return {
            "hidden_test_passes": hidden_test_passes(copy, migrations),
            "sqlfluff_violations": count_sqlfluff_violations(copy, migrations),
        }
