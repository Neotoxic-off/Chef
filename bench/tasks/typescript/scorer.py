"""Score the typescript task: tsc without and with --strict on the agent's code, its own tests counted, the hidden suite run by tsx."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from score import Metrics, run

HIDDEN_TEST: Path = Path(__file__).resolve().parent / "hidden_test.ts"
HIDDEN_TEST_NAME: str = "bench_hidden.test.ts"
TYPESCRIPT_PACKAGE: str = "typescript@7.0.2"
TSX_PACKAGE: str = "tsx@4.23.15"
TSC_OPTIONS: tuple[str, ...] = (
    "--noEmit",
    "--ignoreConfig",
    "--skipLibCheck",
    "--target",
    "es2022",
    "--module",
    "nodenext",
    "--allowImportingTsExtensions",
    "--types",
    "*",
)
TYPE_ERROR_MARKER: str = "error TS"
IGNORED_DIRS: tuple[str, ...] = (".git", "node_modules", "dist")
TEST_FILE_PATTERN: re.Pattern[str] = re.compile(r"(\.test|\.spec|_test)\.tsx?$")
TEST_DIR_NAMES: frozenset[str] = frozenset({"test", "tests", "__tests__"})
TEST_CALL_PATTERN: re.Pattern[str] = re.compile(r"^\s*(?:it|test)(?:\.(?:only|skip|todo))?\s*\(", re.MULTILINE)
TAP_FAIL_PATTERN: re.Pattern[str] = re.compile(r"^# fail (\d+)$", re.MULTILINE)
TAP_PASS_PATTERN: re.Pattern[str] = re.compile(r"^# pass (\d+)$", re.MULTILINE)


def npx() -> str:
    path: str | None = shutil.which("npx")
    if path is None:
        raise RuntimeError("npx is not on PATH")
    return path


def typescript_files(workspace: Path) -> list[Path]:
    return [
        path.relative_to(workspace)
        for path in workspace.rglob("*")
        if path.suffix in {".ts", ".tsx"} and not set(IGNORED_DIRS) & set(path.relative_to(workspace).parts)
    ]


def is_test_file(path: Path) -> bool:
    return bool(TEST_FILE_PATTERN.search(path.name)) or bool(TEST_DIR_NAMES & set(path.parts))


def count_written_tests(workspace: Path, files: list[Path]) -> int:
    return sum(
        len(TEST_CALL_PATTERN.findall((workspace / path).read_text(encoding="utf-8"))) for path in files if is_test_file(path)
    )


def type_checks(workspace: Path, files: list[Path], strict: bool) -> bool:
    """True when tsc reports no error; raise when tsc failed without reporting any type error."""
    if not files:
        return False
    strict_flag: str = "true" if strict else "false"
    outcome: subprocess.CompletedProcess[str] = run(
        [npx(), "--yes", "-p", TYPESCRIPT_PACKAGE, "tsc", *TSC_OPTIONS, "--strict", strict_flag, *map(str, files)], workspace
    )
    if outcome.returncode == 0:
        return True
    if TYPE_ERROR_MARKER in outcome.stdout:
        return False
    raise RuntimeError(f"tsc failed in {workspace}: {(outcome.stderr or outcome.stdout).strip()[:500]}")


def hidden_test_passes(workspace: Path) -> bool:
    shutil.copy(HIDDEN_TEST, workspace / HIDDEN_TEST_NAME)
    outcome: subprocess.CompletedProcess[str] = run(
        [npx(), "--yes", TSX_PACKAGE, "--test", "--test-reporter=tap", HIDDEN_TEST_NAME], workspace
    )
    failed: re.Match[str] | None = TAP_FAIL_PATTERN.search(outcome.stdout)
    passed: re.Match[str] | None = TAP_PASS_PATTERN.search(outcome.stdout)
    if failed is None or passed is None:
        raise RuntimeError(f"tsx --test did not run in {workspace}: {outcome.stderr.strip()[:500]}")
    return outcome.returncode == 0 and int(failed.group(1)) == 0 and int(passed.group(1)) > 0


def score(workspace: Path) -> Metrics:
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = Path(scratch) / "workspace"
        shutil.copytree(workspace, copy, ignore=shutil.ignore_patterns(".git"))
        files: list[Path] = typescript_files(copy)
        return {
            "hidden_test_passes": hidden_test_passes(copy) if files else False,
            "tests_written": count_written_tests(copy, files),
            "compiles": type_checks(copy, files, strict=False),
            "lint_clean": type_checks(copy, files, strict=True),
        }
