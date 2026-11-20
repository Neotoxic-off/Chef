"""Score the bash task: a CSV statistics script, its hidden bats suite and shellcheck, both run in pinned images."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from score import LINT_OK_CODES, Metrics
from scorer_lib import ERROR_TAIL_CHARS, copy_workspace, docker_run, source_files

HIDDEN_TEST: Path = Path(__file__).resolve().parent / "hidden.bats"
HIDDEN_TEST_NAME: str = "bench_hidden.bats"
BATS_IMAGE: str = "bats/bats:1.11.1@sha256:e56e7c49087cb766b1ba9c5732b8f5402d289252d52f64e1eefb88269f74125c"
SHELLCHECK_IMAGE: str = "koalaman/shellcheck:v0.10.0@sha256:2097951f02e735b613f4a34de20c40f937a6c8f18ecb170612c88c34517221fb"
SCRIPT_SUFFIXES: tuple[str, ...] = (".sh", ".bash")
IGNORED_DIRS: tuple[str, ...] = (".git", "node_modules")
BATS_TEST_PATTERN: re.Pattern[str] = re.compile(r"^\s*@test\s", re.MULTILINE)
TAP_OK_PATTERN: re.Pattern[str] = re.compile(r"^ok \d+", re.MULTILINE)
TAP_NOT_OK_PATTERN: re.Pattern[str] = re.compile(r"^not ok \d+", re.MULTILINE)
GCC_FINDING_PATTERN: re.Pattern[str] = re.compile(r"^.+:\d+:\d+: ", re.MULTILINE)


def count_bats_tests(workspace: Path) -> int:
    return sum(
        len(BATS_TEST_PATTERN.findall((workspace / path).read_text(encoding="utf-8")))
        for path in source_files(workspace, (".bats",), IGNORED_DIRS)
    )


def hidden_test_passes(copy: Path) -> bool:
    shutil.copy(HIDDEN_TEST, copy / HIDDEN_TEST_NAME)
    outcome: subprocess.CompletedProcess[str] = docker_run(
        ["-v", f"{copy}:/code", BATS_IMAGE, "--tap", f"/code/{HIDDEN_TEST_NAME}"], copy
    )
    if outcome.returncode not in {0, 1}:
        raise RuntimeError(f"bats did not run in {copy}: {outcome.stderr.strip()[:ERROR_TAIL_CHARS]}")
    passed: int = len(TAP_OK_PATTERN.findall(outcome.stdout))
    return outcome.returncode == 0 and passed > 0 and not TAP_NOT_OK_PATTERN.search(outcome.stdout)


def shellcheck_findings(copy: Path, scripts: list[Path]) -> int:
    """Findings of every severity, always from the pinned image so every run uses the same shellcheck."""
    names: list[str] = [path.as_posix() for path in scripts]
    outcome: subprocess.CompletedProcess[str] = docker_run(
        ["-v", f"{copy}:/mnt", "-w", "/mnt", SHELLCHECK_IMAGE, "--format", "gcc", *names], copy
    )
    if outcome.returncode not in LINT_OK_CODES:
        raise RuntimeError(f"shellcheck failed in {copy}: {outcome.stderr.strip()[:ERROR_TAIL_CHARS]}")
    return len(GCC_FINDING_PATTERN.findall(outcome.stdout))


def score(workspace: Path) -> Metrics:
    scripts: list[Path] = source_files(workspace, SCRIPT_SUFFIXES, IGNORED_DIRS)
    metrics: Metrics = {
        "hidden_test_passes": False,
        "tests_written": count_bats_tests(workspace),
        "shellcheck_findings": None,
    }
    if not scripts:
        return metrics
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch), IGNORED_DIRS)
        metrics["shellcheck_findings"] = shellcheck_findings(copy, scripts)
        metrics["hidden_test_passes"] = hidden_test_passes(copy)
    return metrics
