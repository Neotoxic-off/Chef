"""Score the http-retry task: add configurable retry with backoff to a TypeScript API client without retrying unsafe requests."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from score import Metrics, run
from scorer_lib import changes_since_seed, copy_workspace, executable, is_node_test_file

TASK_DIR: Path = Path(__file__).resolve().parent
SEED_DIR: Path = TASK_DIR / "seed"
HIDDEN_TEST: Path = TASK_DIR / "hidden.test.ts"
HIDDEN_TEST_PATH: Path = Path("test") / "bench_hidden.test.ts"
TSCONFIG_NAME: str = "tsconfig.json"
TYPESCRIPT_PACKAGE: str = "typescript@6.0.3"
TYPESCRIPT_SUFFIXES: frozenset[str] = frozenset({".ts", ".tsx", ".mts", ".cts"})
LOCKFILE_NAMES: frozenset[str] = frozenset(
    {"package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lock", "bun.lockb"}
)
IGNORED_DIR_NAMES: frozenset[str] = frozenset({".git", "node_modules"})
TAP_TEST_COUNT: re.Pattern[str] = re.compile(r"^# tests (\d+)$", re.MULTILINE)
TSC_ERROR_MARKER: str = "error TS"


def files_of(root: Path) -> list[Path]:
    return [
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and not IGNORED_DIR_NAMES & set(path.relative_to(root).parts)
    ]


def typescript_sources(root: Path) -> list[Path]:
    return [path for path in files_of(root) if path.suffix in TYPESCRIPT_SUFFIXES and not is_node_test_file(path)]


def node_tests_pass(workspace: Path, test_files: dict[Path, Path]) -> bool:
    """Copy each source test file to its path in a copy of the workspace, then run only those files."""
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch), IGNORED_DIR_NAMES)
        for destination, source in test_files.items():
            (copy / destination).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source, copy / destination)
        test_names: list[str] = [path.as_posix() for path in test_files if path.name.endswith(".test.ts")]
        outcome: subprocess.CompletedProcess[str] = run(["node", "--test", *test_names], copy)
    return outcome.returncode == 0


def existing_tests_pass(workspace: Path) -> bool:
    """The seed's tests and their helpers, unchanged, against the agent's sources."""
    return node_tests_pass(workspace, {path: SEED_DIR / path for path in files_of(SEED_DIR) if is_node_test_file(path)})


def count_node_tests(workspace: Path) -> int:
    listed: subprocess.CompletedProcess[str] = run(["node", "--test", "--test-reporter=tap"], workspace)
    counts: list[str] = TAP_TEST_COUNT.findall(listed.stdout)
    return int(counts[-1]) if counts else 0


def tests_written(workspace: Path) -> int:
    """Tests node runs in the agent's workspace beyond the seed's own."""
    with tempfile.TemporaryDirectory() as scratch:
        seed_count: int = count_node_tests(copy_workspace(SEED_DIR, Path(scratch), IGNORED_DIR_NAMES))
        agent_count: int = count_node_tests(copy_workspace(workspace, Path(scratch) / "agent", IGNORED_DIR_NAMES))
    return max(0, agent_count - seed_count)


def counts_as_source_change(path: Path) -> bool:
    return not is_node_test_file(path) and path.name not in LOCKFILE_NAMES and not IGNORED_DIR_NAMES & set(path.parts)


def lines_changed(workspace: Path) -> int | None:
    """Lines changed since the seed commit, tests and lockfiles excluded; None without a git history."""
    changes: dict[Path, int] | None = changes_since_seed(workspace)
    return None if changes is None else sum(lines for path, lines in changes.items() if counts_as_source_change(path))


def type_errors(workspace: Path) -> int | None:
    """tsc with the seed's own strict tsconfig.json on the agent's sources; None when there are none."""
    if not typescript_sources(workspace):
        return None
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch), IGNORED_DIR_NAMES)
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
