"""Score the rust task: cargo build, cargo clippy with warnings denied, the agent's tests listed by cargo, the hidden test in tests/."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from score import Metrics, run

HIDDEN_TEST: Path = Path(__file__).resolve().parent / "hidden_test.rs"
HIDDEN_TEST_TARGET: str = "bench_hidden"
CLIPPY_MISSING_MARKER: str = "no such command"
LISTED_TEST_PATTERN: re.Pattern[str] = re.compile(r": test$", re.MULTILINE)


def cargo() -> str:
    path: str | None = shutil.which("cargo")
    if path is None:
        raise RuntimeError("cargo is not on PATH")
    return path


def compiles(workspace: Path) -> bool:
    return run([cargo(), "build", "--quiet"], workspace).returncode == 0


def lint_clean(workspace: Path) -> bool:
    linted: subprocess.CompletedProcess[str] = run(
        [cargo(), "clippy", "--quiet", "--all-targets", "--", "-D", "warnings"], workspace
    )
    if CLIPPY_MISSING_MARKER in linted.stderr:
        raise RuntimeError(f"cargo clippy is not installed: {linted.stderr.strip()[:500]}")
    return linted.returncode == 0


def count_written_tests(workspace: Path) -> int:
    listed: subprocess.CompletedProcess[str] = run([cargo(), "test", "--quiet", "--", "--list"], workspace)
    return len(LISTED_TEST_PATTERN.findall(listed.stdout))


def hidden_test_passes(workspace: Path) -> bool:
    tests_dir: Path = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    shutil.copy(HIDDEN_TEST, tests_dir / f"{HIDDEN_TEST_TARGET}.rs")
    return run([cargo(), "test", "--quiet", "--test", HIDDEN_TEST_TARGET], workspace).returncode == 0


def score(workspace: Path) -> Metrics:
    if not (workspace / "Cargo.toml").is_file():
        return {"hidden_test_passes": False, "tests_written": 0, "compiles": False, "lint_clean": False}
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = Path(scratch) / "workspace"
        shutil.copytree(workspace, copy, ignore=shutil.ignore_patterns(".git", "target"))
        builds: bool = compiles(copy)
        metrics: Metrics = {
            "tests_written": count_written_tests(copy),
            "compiles": builds,
            "lint_clean": builds and lint_clean(copy),
        }
        return {"hidden_test_passes": hidden_test_passes(copy), **metrics}
