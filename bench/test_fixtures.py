"""Each fixture task's scorer, on a known-correct solution and a known-flawed one, without running Claude.

The correct solutions in tasks/<task>/golden are first answers of the 1.2 benchmark that passed every check.
"""

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from score import Metrics, task_scorer

TASKS_DIR: Path = Path(__file__).resolve().parent / "tasks"
FIXTURE_TASKS: tuple[str, ...] = ("python", "refactor", "stream-import", "http-retry", "orders-pagination", "bugfix")
SEEDED_FIXTURE_TASKS: tuple[str, ...] = ("stream-import", "http-retry", "orders-pagination", "bugfix")
REFACTOR_SLIP: tuple[str, str] = ("total - total * 0.08", "total - total * 0.07")


def score(task: str, workspace: Path) -> Metrics:
    scorer: Callable[[Path], Metrics] | None = task_scorer(task)
    assert scorer is not None
    return scorer(workspace)


def score_copy(task: str, source: Path, workspace: Path) -> Metrics:
    """Score a copy, since some scorers write reports into the workspace they score."""
    shutil.copytree(source, workspace)
    return score(task, workspace)


@pytest.mark.parametrize("task", FIXTURE_TASKS)
def test_golden_solution_passes_the_hidden_and_the_existing_tests(task: str, tmp_path: Path) -> None:
    metrics: Metrics = score_copy(task, TASKS_DIR / task / "golden", tmp_path / "workspace")

    assert metrics["hidden_test_passes"] is True
    assert metrics.get("existing_tests_pass", True) is True


@pytest.mark.parametrize("task", SEEDED_FIXTURE_TASKS)
def test_untouched_seed_fails_the_hidden_test(task: str, tmp_path: Path) -> None:
    metrics: Metrics = score_copy(task, TASKS_DIR / task / "seed", tmp_path / "workspace")

    assert metrics["hidden_test_passes"] is False


def test_python_task_without_code_fails_the_hidden_test(tmp_path: Path) -> None:
    metrics: Metrics = score("python", tmp_path)

    assert metrics["hidden_test_passes"] is False


def test_refactor_that_changes_a_discount_fails_the_hidden_test(tmp_path: Path) -> None:
    workspace: Path = tmp_path / "workspace"
    shutil.copytree(TASKS_DIR / "refactor" / "seed", workspace)
    invoice: Path = workspace / "invoice.py"
    invoice.write_text(invoice.read_text(encoding="utf-8").replace(*REFACTOR_SLIP), encoding="utf-8")

    metrics: Metrics = score("refactor", workspace)

    assert metrics["hidden_test_passes"] is False
