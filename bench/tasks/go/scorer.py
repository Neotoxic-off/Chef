"""Score the go task: go build, go vet plus gofmt, the agent's tests listed by go test, the hidden test run in the root package."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from score import Metrics, run, run_tool
from scorer_lib import executable

HIDDEN_TEST: Path = Path(__file__).resolve().parent / "hidden_test.go"
HIDDEN_TEST_NAME: str = "bench_hidden_test.go"
HIDDEN_TEST_FILTER: str = "^TestBenchHidden"
LISTED_TEST_PATTERN: re.Pattern[str] = re.compile(r"^(?:Test|Fuzz|Example)\w*$", re.MULTILINE)


def compiles(workspace: Path) -> bool:
    return run([executable("go"), "build", "./..."], workspace).returncode == 0


def lint_clean(workspace: Path) -> bool:
    """gofmt runs only after go vet passed, so a syntax error cannot be taken for a gofmt failure."""
    if run([executable("go"), "vet", "./..."], workspace).returncode != 0:
        return False
    return run_tool([executable("gofmt"), "-l", "."], workspace).stdout.strip() == ""


def count_written_tests(workspace: Path) -> int:
    listed: subprocess.CompletedProcess[str] = run([executable("go"), "test", "-list", ".", "./..."], workspace)
    return len(LISTED_TEST_PATTERN.findall(listed.stdout))


def hidden_test_passes(workspace: Path) -> bool:
    shutil.copy(HIDDEN_TEST, workspace / HIDDEN_TEST_NAME)
    return run([executable("go"), "test", "-count=1", "-run", HIDDEN_TEST_FILTER, "."], workspace).returncode == 0


def score(workspace: Path) -> Metrics:
    if not (workspace / "go.mod").is_file():
        return {"hidden_test_passes": False, "tests_written": 0, "compiles": False, "lint_clean": False}
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = Path(scratch) / "workspace"
        shutil.copytree(workspace, copy, ignore=shutil.ignore_patterns(".git"))
        builds: bool = compiles(copy)
        metrics: Metrics = {
            "tests_written": count_written_tests(copy),
            "compiles": builds,
            "lint_clean": builds and lint_clean(copy),
        }
        return {"hidden_test_passes": hidden_test_passes(copy), **metrics}
