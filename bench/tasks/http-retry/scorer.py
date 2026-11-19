"""Score the http-retry task: add configurable retry with backoff to a TypeScript API client without retrying unsafe requests."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from score import Metrics, run

TASK_DIR: Path = Path(__file__).resolve().parent
SEED_DIR: Path = TASK_DIR / "seed"
HIDDEN_TEST: Path = TASK_DIR / "hidden.test.ts"
HIDDEN_TEST_PATH: Path = Path("test") / "bench_hidden.test.ts"
TSCONFIG_NAME: str = "tsconfig.json"
TYPESCRIPT_PACKAGE: str = "typescript@6.0.3"
TYPESCRIPT_SUFFIXES: frozenset[str] = frozenset({".ts", ".tsx", ".mts", ".cts"})
TEST_NAME_MARKERS: tuple[str, ...] = (".test.", ".spec.")
TEST_DIR_NAMES: frozenset[str] = frozenset({"test", "tests", "__tests__"})
LOCKFILE_NAMES: frozenset[str] = frozenset(
    {"package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lock", "bun.lockb"}
)
IGNORED_DIR_NAMES: frozenset[str] = frozenset({".git", "node_modules"})
TAP_TEST_COUNT: re.Pattern[str] = re.compile(r"^# tests (\d+)$", re.MULTILINE)
TSC_ERROR_MARKER: str = "error TS"


def executable(name: str) -> str:
    """Resolve npx to its full path: on Windows it is a .cmd file that CreateProcess cannot find by name."""
    path: str | None = shutil.which(name)
    if path is None:
        raise RuntimeError(f"{name} is not on PATH")
    return path


def is_test_file(path: Path) -> bool:
    return any(marker in path.name for marker in TEST_NAME_MARKERS) or bool(TEST_DIR_NAMES & set(path.parts[:-1]))


def files_of(root: Path) -> list[Path]:
    return [
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and not IGNORED_DIR_NAMES & set(path.relative_to(root).parts)
    ]


def typescript_sources(root: Path) -> list[Path]:
    return [path for path in files_of(root) if path.suffix in TYPESCRIPT_SUFFIXES and not is_test_file(path)]


def copy_workspace(workspace: Path, destination: Path) -> Path:
    copy: Path = destination / "workspace"
    shutil.copytree(workspace, copy, ignore=shutil.ignore_patterns(*IGNORED_DIR_NAMES))
    return copy


def node_tests_pass(workspace: Path, test_files: dict[Path, Path]) -> bool:
    """Copy each source test file to its path in a copy of the workspace, then run only those files."""
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch))
        for destination, source in test_files.items():
            (copy / destination).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source, copy / destination)
        test_names: list[str] = [path.as_posix() for path in test_files if path.name.endswith(".test.ts")]
        outcome: subprocess.CompletedProcess[str] = run(["node", "--test", *test_names], copy)
    return outcome.returncode == 0


def existing_tests_pass(workspace: Path) -> bool:
    """The seed's tests and their helpers, unchanged, against the agent's sources."""
    return node_tests_pass(workspace, {path: SEED_DIR / path for path in files_of(SEED_DIR) if is_test_file(path)})


def count_node_tests(workspace: Path) -> int:
    listed: subprocess.CompletedProcess[str] = run(["node", "--test", "--test-reporter=tap"], workspace)
    counts: list[str] = TAP_TEST_COUNT.findall(listed.stdout)
    return int(counts[-1]) if counts else 0


def tests_written(workspace: Path) -> int:
    """Tests node runs in the agent's workspace beyond the seed's own."""
    with tempfile.TemporaryDirectory() as scratch:
        seed_count: int = count_node_tests(copy_workspace(SEED_DIR, Path(scratch)))
        agent_count: int = count_node_tests(copy_workspace(workspace, Path(scratch) / "agent"))
    return max(0, agent_count - seed_count)


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
    """Lines changed since the seed commit, tests and lockfiles excluded; None without a git history."""
    if not (workspace / ".git").exists():
        return None
    seed_commit: str = git_output(workspace, "rev-list", "--max-parents=0", "HEAD").split()[-1]
    changes: dict[Path, int] = tracked_changes(workspace, seed_commit) | untracked_changes(workspace)
    return sum(lines for path, lines in changes.items() if counts_as_source_change(path))


def type_errors(workspace: Path) -> int | None:
    """tsc with the seed's own strict tsconfig.json on the agent's sources; None when there are none."""
    if not typescript_sources(workspace):
        return None
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch))
        shutil.copy(SEED_DIR / TSCONFIG_NAME, copy / TSCONFIG_NAME)
        checked: subprocess.CompletedProcess[str] = run(
            [executable("npx"), "--yes", "-p", TYPESCRIPT_PACKAGE, "tsc", "-p", TSCONFIG_NAME, "--pretty", "false"], copy
        )
    errors: int = checked.stdout.count(TSC_ERROR_MARKER)
    if checked.returncode != 0 and errors == 0:
        raise RuntimeError(f"tsc failed in {workspace}: {(checked.stderr or checked.stdout).strip()[:500]}")
    return errors


def score(workspace: Path) -> Metrics:
    return {
        "hidden_test_passes": node_tests_pass(workspace, {HIDDEN_TEST_PATH: HIDDEN_TEST}),
        "existing_tests_pass": existing_tests_pass(workspace),
        "tests_written": tests_written(workspace),
        "lines_changed": lines_changed(workspace),
        "type_errors": type_errors(workspace),
    }
