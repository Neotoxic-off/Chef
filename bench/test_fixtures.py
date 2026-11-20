"""Each fixture task's scorer, on a known-correct solution and a known-flawed one, without running Claude.

The correct solutions in tasks/<task>/golden are first answers of the 1.2 benchmark (python, refactor, stream-import,
http-retry, orders-pagination, bugfix) and of the 1.3 benchmark (the others) that passed every check.
"""

import os
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from score import BENCH_DIR, Metrics, run, task_scorer

TASKS_DIR: Path = Path(__file__).resolve().parent / "tasks"
# The metric that says whether the task was solved; the other metrics measure how well.
MAIN_METRIC: dict[str, str] = {
    "python": "hidden_test_passes",
    "refactor": "hidden_test_passes",
    "stream-import": "hidden_test_passes",
    "http-retry": "hidden_test_passes",
    "orders-pagination": "hidden_test_passes",
    "bugfix": "hidden_test_passes",
    "go": "hidden_test_passes",
    "rust": "hidden_test_passes",
    "java": "hidden_test_passes",
    "csharp": "hidden_test_passes",
    # Only the hidden test: the golden ships without node_modules, so tsc cannot resolve vitest and compiles is False.
    "typescript": "hidden_test_passes",
    "terraform": "hidden_test_passes",
    "helm": "hidden_test_passes",
    "github-actions": "hidden_test_passes",
    "docker": "container_healthy",
    "prometheus": "rules_valid",
}
SEEDED_FIXTURE_TASKS: tuple[str, ...] = (
    "stream-import",
    "http-retry",
    "orders-pagination",
    "bugfix",
    "helm",
    "github-actions",
    "docker",
    "prometheus",
)
REFACTOR_SLIP: tuple[str, str] = ("total - total * 0.08", "total - total * 0.07")
# One-line slips in a golden that its hidden test must catch, for the tasks that start from an empty workspace.
GOLDEN_SLIPS: dict[str, tuple[str, str, str]] = {
    "go": ("ports.go", "maxPort  = 65535", "maxPort  = 65536"),
    "rust": ("src/lib.rs", "minor: parse_part(minor, 1)?", "minor: parse_part(patch, 1)?"),
    "java": (
        "src/main/java/com/example/durations/DurationParser.java",
        "SECONDS_PER_MINUTE = BigInteger.valueOf(60)",
        "SECONDS_PER_MINUTE = BigInteger.valueOf(61)",
    ),
    "csharp": ("src/Billing/InvoiceCalculator.cs", "MidpointRounding.AwayFromZero", "MidpointRounding.ToEven"),
    "typescript": ("src/duration.ts", "MAX_DURATION_MS = 30 * MS_PER_DAY", "MAX_DURATION_MS = 31 * MS_PER_DAY"),
    "terraform": ("main.tf", "infrequent_access_after_days = 30", "infrequent_access_after_days = 60"),
}
TOOLS: dict[str, tuple[str, ...]] = {
    "http-retry": ("node", "npx"),
    "bugfix": ("node", "npm", "npx"),
    "typescript": ("npx",),
    "orders-pagination": ("go", "gofmt"),
    "go": ("go", "gofmt"),
    "rust": ("cargo",),
    "csharp": ("dotnet",),
}
DOCKER_TASKS: frozenset[str] = frozenset({"java", "terraform", "helm", "github-actions", "docker", "prometheus"})
# Push CI sets it to "off": image pulls and builds do not fit its time limit; fixtures.yml runs them weekly.
DOCKER_FIXTURES_OFF: bool = os.environ.get("BENCH_DOCKER_FIXTURES") == "off"
DOCKER_UP: bool = shutil.which("docker") is not None and run(["docker", "info"], BENCH_DIR).returncode == 0
# fixtures.yml sets it to "1": a missing tool or Docker daemon then fails the fixture instead of skipping it.
FIXTURES_STRICT: bool = os.environ.get("BENCH_FIXTURES_STRICT") == "1"


def needs_tools(task: str, strict: bool = FIXTURES_STRICT) -> pytest.MarkDecorator:
    if task in DOCKER_TASKS and DOCKER_FIXTURES_OFF:
        return pytest.mark.skip(reason=f"the {task} scorer needs Docker fixtures, off here (BENCH_DOCKER_FIXTURES=off)")
    missing: list[str] = [tool for tool in TOOLS.get(task, ()) if shutil.which(tool) is None]
    if task in DOCKER_TASKS and not DOCKER_UP:
        missing.append("a running Docker daemon")
    # Strict, the fixture runs and fails on the missing tool.
    return pytest.mark.skipif(bool(missing) and not strict, reason=f"the {task} scorer needs {', '.join(missing)}")


def with_tools(tasks: tuple[str, ...]) -> list[object]:
    return [pytest.param(task, marks=needs_tools(task)) for task in tasks]


def score(task: str, workspace: Path) -> Metrics:
    scorer: Callable[[Path], Metrics] | None = task_scorer(task)
    assert scorer is not None
    return scorer(workspace)


def score_copy(task: str, source: Path, workspace: Path) -> Metrics:
    """Score a copy, since some scorers write reports into the workspace they score."""
    shutil.copytree(source, workspace)
    return score(task, workspace)


@pytest.mark.parametrize("task", with_tools(tuple(MAIN_METRIC)))
def test_golden_solution_passes_the_hidden_and_the_existing_tests(task: str, tmp_path: Path) -> None:
    metrics: Metrics = score_copy(task, TASKS_DIR / task / "golden", tmp_path / "workspace")

    assert metrics[MAIN_METRIC[task]] is True
    assert metrics.get("existing_tests_pass", True) is True


@pytest.mark.parametrize("task", with_tools(SEEDED_FIXTURE_TASKS))
def test_untouched_seed_fails_the_hidden_test(task: str, tmp_path: Path) -> None:
    metrics: Metrics = score_copy(task, TASKS_DIR / task / "seed", tmp_path / "workspace")

    assert metrics[MAIN_METRIC[task]] is False


@pytest.mark.parametrize("task", with_tools(tuple(GOLDEN_SLIPS)))
def test_golden_with_a_one_line_slip_fails_the_hidden_test(task: str, tmp_path: Path) -> None:
    workspace: Path = tmp_path / "workspace"
    shutil.copytree(TASKS_DIR / task / "golden", workspace)
    relative, correct, slipped = GOLDEN_SLIPS[task]
    source: Path = workspace / relative
    text: str = source.read_text(encoding="utf-8")
    assert text.count(correct) == 1
    source.write_text(text.replace(correct, slipped), encoding="utf-8", newline="")

    metrics: Metrics = score(task, workspace)

    assert metrics[MAIN_METRIC[task]] is False


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


def test_needs_tools_skips_a_missing_tool_unless_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    assert needs_tools("rust", strict=False).args[0] is True
    assert needs_tools("rust", strict=True).args[0] is False
