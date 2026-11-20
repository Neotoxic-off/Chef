"""Score the stream-import task: make a Python CSV importer stream its input and write in batches, all or nothing."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from score import PYTEST_ISOLATED, Metrics, count_collected_tests, run, run_tool
from scorer_lib import changes_since_seed, copy_workspace, is_python_test_file

TASK_DIR: Path = Path(__file__).resolve().parent
SEED_DIR: Path = TASK_DIR / "seed"
SEED_CONFIG: Path = SEED_DIR / "pyproject.toml"
HIDDEN_TEST: Path = TASK_DIR / "hidden_test.py"
PACKAGE_NAME: str = "ledger_import"
IGNORED_DIR_NAMES: frozenset[str] = frozenset({".git", ".venv", "venv", "__pycache__", ".mypy_cache", ".ruff_cache"})
LOCKFILE_NAMES: frozenset[str] = frozenset({"uv.lock", "poetry.lock", "pdm.lock", "requirements.lock"})


def python_files(root: Path) -> list[Path]:
    return [path.relative_to(root) for path in root.rglob("*.py") if not IGNORED_DIR_NAMES & set(path.relative_to(root).parts)]


def pytest_passes(workspace: Path, test_files: list[Path]) -> bool:
    """Run test files, renamed with a bench_ prefix so they never replace the agent's own, against a copy."""
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch), IGNORED_DIR_NAMES)
        names: list[str] = []
        for test_file in test_files:
            name: str = f"bench_{test_file.name}"
            shutil.copy(test_file, copy / name)
            names.append(name)
        outcome: subprocess.CompletedProcess[str] = run([*PYTEST_ISOLATED, "-p", "no:cov", *names], copy)
    return outcome.returncode == 0


def tests_written(workspace: Path) -> int:
    """Tests collected in the agent's workspace beyond the seed's own, counted on a copy so the seed stays clean."""
    with tempfile.TemporaryDirectory() as scratch:
        seed_count: int = count_collected_tests(copy_workspace(SEED_DIR, Path(scratch), IGNORED_DIR_NAMES))
    return max(0, count_collected_tests(workspace) - seed_count)


def counts_as_source_change(path: Path) -> bool:
    return not is_python_test_file(path) and path.name not in LOCKFILE_NAMES


def lines_changed(workspace: Path) -> int | None:
    """Lines changed since the seed commit, tests and lockfiles excluded; None without a git history."""
    changes: dict[Path, int] | None = changes_since_seed(workspace)
    return None if changes is None else sum(lines for path, lines in changes.items() if counts_as_source_change(path))


def ruff_findings(workspace: Path) -> int:
    """Ruff with the seed's own configuration, so a loosened config does not hide findings."""
    checked: subprocess.CompletedProcess[str] = run_tool(
        [sys.executable, "-m", "ruff", "check", "--config", str(SEED_CONFIG), "--output-format", "json", "."], workspace
    )
    return len(json.loads(checked.stdout or "[]"))


def mypy_errors(workspace: Path) -> int | None:
    """mypy with the seed's own strict configuration; None when the package is gone."""
    if not (workspace / PACKAGE_NAME).is_dir():
        return None
    checked: subprocess.CompletedProcess[str] = run_tool(
        [sys.executable, "-m", "mypy", "--no-incremental", f"--config-file={SEED_CONFIG}"], workspace
    )
    return sum(1 for line in checked.stdout.splitlines() if ": error:" in line)


def score(workspace: Path) -> Metrics:
    seed_tests: list[Path] = [SEED_DIR / path for path in python_files(SEED_DIR) if is_python_test_file(path)]
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch), IGNORED_DIR_NAMES)
        return {
            "hidden_test_passes": pytest_passes(workspace, [HIDDEN_TEST]),
            "existing_tests_pass": pytest_passes(workspace, seed_tests),
            "tests_written": tests_written(copy),
            "lines_changed": lines_changed(workspace),
            "ruff_findings": ruff_findings(copy),
            "mypy_errors": mypy_errors(copy),
        }
