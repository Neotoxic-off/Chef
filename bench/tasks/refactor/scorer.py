"""Score the refactor task: a messy but working Python invoicing module to clean up without changing its behaviour."""

import ast
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from score import PYTEST_ISOLATED, Metrics, count_collected_tests, count_mypy_strict_errors, count_ruff_findings, run

TASK_DIR: Path = Path(__file__).resolve().parent
SEED_DIR: Path = TASK_DIR / "seed"
HIDDEN_TEST: Path = TASK_DIR / "hidden_test.py"
IGNORED_DIR_NAMES: frozenset[str] = frozenset({".git", ".venv", "venv", "__pycache__"})
TEST_FILE_PREFIXES: tuple[str, ...] = ("test_", "conftest")
TEST_DIR_NAMES: frozenset[str] = frozenset({"tests", "test"})


def is_test_file(path: Path) -> bool:
    return path.name.startswith(TEST_FILE_PREFIXES) or path.stem.endswith("_test") or bool(TEST_DIR_NAMES & set(path.parts))


def python_files(root: Path) -> list[Path]:
    return [path.relative_to(root) for path in root.rglob("*.py") if not IGNORED_DIR_NAMES & set(path.relative_to(root).parts)]


def python_sources(root: Path) -> list[Path]:
    return [path for path in python_files(root) if not is_test_file(path)]


def copy_workspace(workspace: Path, destination: Path) -> Path:
    copy: Path = destination / "workspace"
    shutil.copytree(workspace, copy, ignore=shutil.ignore_patterns(*IGNORED_DIR_NAMES))
    return copy


def pytest_passes(workspace: Path, test_files: list[Path]) -> bool:
    """Run test files, renamed with a bench_ prefix so they never replace the agent's own, against a copy."""
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch))
        names: list[str] = []
        for test_file in test_files:
            name: str = f"bench_{test_file.name}"
            shutil.copy(test_file, copy / name)
            names.append(name)
        outcome: subprocess.CompletedProcess[str] = run([*PYTEST_ISOLATED, "-p", "no:cov", *names], copy)
    return outcome.returncode == 0


def function_lengths(source: Path) -> list[int]:
    tree: ast.Module = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    return [
        (node.end_lineno or node.lineno) - node.lineno + 1
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]


def max_function_lines(workspace: Path, sources: list[Path]) -> int | None:
    """Longest function or method in the non-test sources, decorators excluded; None when there is nothing to measure."""
    lengths: list[int] = []
    for source in sources:
        try:
            lengths.extend(function_lengths(workspace / source))
        except SyntaxError as error:
            print(f"score: {workspace / source} does not parse, not measured: {error}", file=sys.stderr)
    return max(lengths, default=None)


def score(workspace: Path) -> Metrics:
    seed_tests: list[Path] = [SEED_DIR / path for path in python_files(SEED_DIR) if is_test_file(path)]
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch))
        sources: list[Path] = python_sources(copy)
        return {
            "hidden_test_passes": pytest_passes(workspace, [HIDDEN_TEST]),
            "existing_tests_pass": pytest_passes(workspace, seed_tests),
            "max_function_lines": max_function_lines(copy, sources),
            "mypy_strict_errors": count_mypy_strict_errors(copy, sources),
            "ruff_findings": count_ruff_findings(copy),
            "tests_written": count_collected_tests(copy),
        }
