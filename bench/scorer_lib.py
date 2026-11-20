"""Helpers the task scorers share: tool lookup, workspace copies, test-file rules and the agent's diff against the seed."""

import shutil
import subprocess
import uuid
from collections.abc import Iterable
from pathlib import Path

from score import COMMAND_TIMEOUT_SECONDS, run

NODE_TEST_NAME_MARKERS: tuple[str, ...] = (".test.", ".spec.")
NODE_TEST_DIR_NAMES: frozenset[str] = frozenset({"test", "tests", "__tests__"})
PYTHON_TEST_FILE_PREFIXES: tuple[str, ...] = ("test_", "conftest")
PYTHON_TEST_DIR_NAMES: frozenset[str] = frozenset({"tests", "test"})


def executable(name: str) -> str:
    """Resolve a tool to its full path: on Windows npm and npx are .cmd files that CreateProcess cannot find by name."""
    path: str | None = shutil.which(name)
    if path is None:
        raise RuntimeError(f"{name} is not on PATH")
    return path


def docker_run(
    arguments: list[str], cwd: Path, stdin: str | None = None, timeout: int = COMMAND_TIMEOUT_SECONDS
) -> subprocess.CompletedProcess[str]:
    """`docker run --rm` under a unique name, removed on timeout: killing the client leaves the container running."""
    name: str = f"bench-{uuid.uuid4().hex}"
    try:
        return run(["docker", "run", "--rm", "--name", name, *arguments], cwd, stdin, timeout)
    except subprocess.TimeoutExpired:
        run(["docker", "rm", "-f", name], cwd)
        raise


def copy_workspace(workspace: Path, destination: Path, ignored: Iterable[str] = (".git",)) -> Path:
    copy: Path = destination / "workspace"
    shutil.copytree(workspace, copy, ignore=shutil.ignore_patterns(*ignored))
    return copy


def is_node_test_file(path: Path) -> bool:
    return any(marker in path.name for marker in NODE_TEST_NAME_MARKERS) or bool(NODE_TEST_DIR_NAMES & set(path.parts[:-1]))


def is_python_test_file(path: Path) -> bool:
    return (
        path.name.startswith(PYTHON_TEST_FILE_PREFIXES)
        or path.stem.endswith("_test")
        or bool(PYTHON_TEST_DIR_NAMES & set(path.parts[:-1]))
    )


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


def changes_since_seed(workspace: Path) -> dict[Path, int] | None:
    """Lines changed per file since the seed commit, untracked files included; None without a git history."""
    if not (workspace / ".git").exists():
        return None
    seed_commit: str = git_output(workspace, "rev-list", "--max-parents=0", "HEAD").split()[-1]
    return tracked_changes(workspace, seed_commit) | untracked_changes(workspace)
