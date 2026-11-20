"""Score the bugfix task: a TypeScript cart module with one bug reported by a user."""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from score import Metrics, run
from scorer_lib import changes_since_seed, copy_workspace, executable, is_node_test_file

TASK_DIR: Path = Path(__file__).resolve().parent
SEED_DIR: Path = TASK_DIR / "seed"
HIDDEN_TEST: Path = TASK_DIR / "hidden.test.ts"
TYPESCRIPT_PACKAGE: str = "typescript@6.0.3"
BENCH_TSCONFIG: str = "bench.tsconfig.json"
TYPESCRIPT_SUFFIXES: frozenset[str] = frozenset({".ts", ".tsx", ".mts", ".cts"})
LOCKFILE_NAMES: frozenset[str] = frozenset(
    {"package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lock", "bun.lockb"}
)
IGNORED_DIR_NAMES: frozenset[str] = frozenset({".git", "node_modules"})
DEFAULT_COMPILER_OPTIONS: dict[str, str | bool] = {"target": "es2022", "module": "nodenext"}
FORCED_COMPILER_OPTIONS: dict[str, str | bool] = {
    "strict": True,
    "noEmit": True,
    "allowImportingTsExtensions": True,
    "skipLibCheck": True,
    "composite": False,
}


def counts_as_source_change(path: Path) -> bool:
    return not is_node_test_file(path) and path.name not in LOCKFILE_NAMES and not IGNORED_DIR_NAMES & set(path.parts)


def files_of(root: Path) -> list[Path]:
    return [
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and not IGNORED_DIR_NAMES & set(path.relative_to(root).parts)
    ]


def typescript_sources(root: Path) -> list[Path]:
    return [path for path in files_of(root) if path.suffix in TYPESCRIPT_SUFFIXES and not is_node_test_file(path)]


def node_test_passes(copy: Path, test_file: Path) -> bool:
    """Run one test file with the seed's own runner (node strips the types), next to the seed's tests."""
    target: Path = copy / "test" / f"bench_{test_file.name}"
    target.parent.mkdir(exist_ok=True)
    shutil.copy(test_file, target)
    outcome: subprocess.CompletedProcess[str] = run(["node", "--test", target.relative_to(copy).as_posix()], copy)
    return outcome.returncode == 0


def passes_with(workspace: Path, test_files: list[Path]) -> bool:
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch))
        return all(node_test_passes(copy, test_file) for test_file in test_files)


def existing_tests_pass(workspace: Path) -> bool:
    """The seed's tests, unchanged, against the agent's sources."""
    return passes_with(workspace, [SEED_DIR / path for path in files_of(SEED_DIR) if is_node_test_file(path)])


def npm_test_passes(workspace: Path, restore_seed_sources: bool) -> bool:
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch))
        if restore_seed_sources:
            for relative in typescript_sources(SEED_DIR):
                (copy / relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(SEED_DIR / relative, copy / relative)
        return run([executable("npm"), "test", "--silent"], copy).returncode == 0


def regression_test_added(workspace: Path) -> bool:
    """The agent's test suite passes on its fix and fails on the seed's buggy sources."""
    if not (workspace / "package.json").is_file():
        return False
    return npm_test_passes(workspace, restore_seed_sources=False) and not npm_test_passes(workspace, restore_seed_sources=True)


def diff_size(workspace: Path) -> tuple[int, int] | None:
    """Files and lines changed since the seed commit, tests and lockfiles excluded."""
    changes: dict[Path, int] | None = changes_since_seed(workspace)
    if changes is None:
        return None
    counted: dict[Path, int] = {path: lines for path, lines in changes.items() if counts_as_source_change(path)}
    return len(counted), sum(counted.values())


def write_bench_tsconfig(copy: Path, sources: list[Path]) -> None:
    has_own_config: bool = (copy / "tsconfig.json").is_file()
    options: dict[str, str | bool] = (
        FORCED_COMPILER_OPTIONS if has_own_config else DEFAULT_COMPILER_OPTIONS | FORCED_COMPILER_OPTIONS
    )
    config: dict[str, object] = {"compilerOptions": options, "files": [path.as_posix() for path in sources], "include": []}
    if has_own_config:
        config["extends"] = "./tsconfig.json"
    (copy / BENCH_TSCONFIG).write_text(json.dumps(config, indent=2), encoding="utf-8")


def typecheck_clean(workspace: Path) -> bool | None:
    """tsc in strict mode on the agent's non-test sources, on top of its tsconfig.json when it has one."""
    sources: list[Path] = typescript_sources(workspace)
    if not sources:
        return None
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch))
        write_bench_tsconfig(copy, sources)
        checked: subprocess.CompletedProcess[str] = run(
            [executable("npx"), "--yes", "-p", TYPESCRIPT_PACKAGE, "tsc", "-p", BENCH_TSCONFIG, "--pretty", "false"], copy
        )
    errors: int = checked.stdout.count("error TS")
    if checked.returncode != 0 and errors == 0:
        raise RuntimeError(f"tsc failed in {workspace}: {(checked.stderr or checked.stdout).strip()[:500]}")
    return errors == 0


def score(workspace: Path) -> Metrics:
    size: tuple[int, int] | None = diff_size(workspace)
    return {
        "hidden_test_passes": passes_with(workspace, [HIDDEN_TEST]),
        "existing_tests_pass": existing_tests_pass(workspace),
        "regression_test_added": regression_test_added(workspace),
        "files_changed": None if size is None else size[0],
        "lines_changed": None if size is None else size[1],
        "typecheck_clean": typecheck_clean(workspace),
    }
