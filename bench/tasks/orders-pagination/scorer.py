"""Score the orders-pagination task: add cursor pagination to a Go HTTP API that stays correct while orders keep coming in."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from score import Metrics, run, run_tool

TASK_DIR: Path = Path(__file__).resolve().parent
SEED_DIR: Path = TASK_DIR / "seed"
HIDDEN_TEST: Path = TASK_DIR / "hidden_test.go"
HIDDEN_TEST_PATH: Path = Path("internal") / "api" / "bench_hidden_test.go"
HIDDEN_TEST_FILTER: str = "^TestBenchHidden"
GO_TEST_SUFFIX: str = "_test.go"
LOCKFILE_NAMES: frozenset[str] = frozenset({"go.sum"})
IGNORED_DIR_NAMES: frozenset[str] = frozenset({".git", "vendor"})
LISTED_TEST_PATTERN: re.Pattern[str] = re.compile(r"^(?:Test|Fuzz|Example)\w*$", re.MULTILINE)


def executable(name: str) -> str:
    path: str | None = shutil.which(name)
    if path is None:
        raise RuntimeError(f"{name} is not on PATH")
    return path


def is_test_file(path: Path) -> bool:
    return path.name.endswith(GO_TEST_SUFFIX)


def test_files_of(root: Path) -> list[Path]:
    return [path.relative_to(root) for path in root.rglob(f"*{GO_TEST_SUFFIX}") if not IGNORED_DIR_NAMES & set(path.parts)]


def copy_workspace(workspace: Path, destination: Path) -> Path:
    copy: Path = destination / "workspace"
    shutil.copytree(workspace, copy, ignore=shutil.ignore_patterns(".git"))
    return copy


def go_tests_pass(copy: Path, *arguments: str) -> bool:
    return run([executable("go"), "test", "-count=1", *arguments], copy).returncode == 0


def hidden_test_passes(workspace: Path) -> bool:
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch))
        (copy / HIDDEN_TEST_PATH).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(HIDDEN_TEST, copy / HIDDEN_TEST_PATH)
        return go_tests_pass(copy, "-run", HIDDEN_TEST_FILTER, f"./{HIDDEN_TEST_PATH.parent.as_posix()}")


def existing_tests_pass(workspace: Path) -> bool:
    """Only the seed's tests, unchanged, against the agent's code: the agent's own test files are removed."""
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch))
        for test_file in test_files_of(copy):
            (copy / test_file).unlink()
        for test_file in test_files_of(SEED_DIR):
            (copy / test_file).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(SEED_DIR / test_file, copy / test_file)
        return go_tests_pass(copy, "./...")


def count_listed_tests(module: Path) -> int:
    listed: subprocess.CompletedProcess[str] = run([executable("go"), "test", "-list", ".", "./..."], module)
    return len(LISTED_TEST_PATTERN.findall(listed.stdout))


def tests_written(workspace: Path) -> int:
    """Tests go lists in the agent's module beyond the seed's own, counted on copies."""
    with tempfile.TemporaryDirectory() as scratch:
        seed_count: int = count_listed_tests(copy_workspace(SEED_DIR, Path(scratch) / "seed"))
        agent_count: int = count_listed_tests(copy_workspace(workspace, Path(scratch) / "agent"))
    return max(0, agent_count - seed_count)


def lint_clean(workspace: Path) -> bool:
    """go vet, then gofmt only once vet passed, so a syntax error cannot be taken for a gofmt failure."""
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch))
        if run([executable("go"), "vet", "./..."], copy).returncode != 0:
            return False
        return run_tool([executable("gofmt"), "-l", "."], copy).stdout.strip() == ""


def git_output(workspace: Path, *arguments: str) -> str:
    outcome: subprocess.CompletedProcess[str] = run(["git", "-C", str(workspace), *arguments], workspace)
    if outcome.returncode != 0:
        raise RuntimeError(f"git {arguments[0]} failed in {workspace}: {outcome.stderr.strip()[:500]}")
    return outcome.stdout


def tracked_changes(workspace: Path, seed_commit: str) -> dict[Path, int]:
    changes: dict[Path, int] = {}
    for record in git_output(workspace, "diff", "--numstat", "--no-renames", "-z", seed_commit).split("\0"):
        if record:
            added, deleted, name = record.split("\t", 2)
            changes[Path(name)] = sum(int(count) for count in (added, deleted) if count != "-")
    return changes


def untracked_changes(workspace: Path) -> dict[Path, int]:
    names: list[str] = git_output(workspace, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    return {Path(name): len((workspace / name).read_bytes().splitlines()) for name in names if name}


def counts_as_source_change(path: Path) -> bool:
    return not is_test_file(path) and path.name not in LOCKFILE_NAMES and not IGNORED_DIR_NAMES & set(path.parts)


def lines_changed(workspace: Path) -> int | None:
    """Lines changed since the seed commit, tests and go.sum excluded; None without a git history."""
    if not (workspace / ".git").exists():
        return None
    seed_commit: str = git_output(workspace, "rev-list", "--max-parents=0", "HEAD").split()[-1]
    changes: dict[Path, int] = tracked_changes(workspace, seed_commit) | untracked_changes(workspace)
    return sum(lines for path, lines in changes.items() if counts_as_source_change(path))


def score(workspace: Path) -> Metrics:
    changed: int | None = lines_changed(workspace)
    if not (workspace / "go.mod").is_file():
        return {
            "hidden_test_passes": False,
            "existing_tests_pass": False,
            "tests_written": 0,
            "lines_changed": changed,
            "lint_clean": False,
        }
    return {
        "hidden_test_passes": hidden_test_passes(workspace),
        "existing_tests_pass": existing_tests_pass(workspace),
        "tests_written": tests_written(workspace),
        "lines_changed": changed,
        "lint_clean": lint_clean(workspace),
    }
