"""Helpers the task scorers share: tool lookup, Docker, CMake scoring, workspace copies, test-file rules and the diff."""

import json
import re
import shutil
import subprocess
import tempfile
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from score import BENCH_DIR, BUILD_TIMEOUT_SECONDS, COMMAND_TIMEOUT_SECONDS, Metrics, run, run_tool

ESLINT_PACKAGES: tuple[str, ...] = ("eslint@10.14.0", "@eslint/js@10.0.1", "globals@17.13.0")
PRETTIER_PACKAGE: str = "prettier@3.9.10"
BENCH_ESLINT_CONFIG: str = "bench.eslint.config.mjs"
JS_TEST_CALL_PATTERN: re.Pattern[str] = re.compile(r"^\s*(?:it|test)(?:\.(?:only|skip|todo))?\s*\(", re.MULTILINE)

# GCC 14.2, CMake 3.31, cppcheck 2.17 from Debian trixie. The base is pinned by digest, the apt packages are not:
# apt-get installs trixie's current versions when the image is built, so a rebuild can bring newer point releases.
GCC_TOOLCHAIN_IMAGE: str = "bench-gcc-toolchain:trixie-20261027"
GCC_TOOLCHAIN_DOCKERFILE: str = (
    "FROM debian:trixie-20261027-slim@sha256:f6b08b09a05725f9431502d3b5714f5c4576e82c1a84fa1debe0c24a7e0c3ec4\n"
    "RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake cppcheck"
    " && rm -rf /var/lib/apt/lists/*\n"
)
# docker run itself failed (125), or the container's command could not run (126) or was not found (127).
DOCKER_FAILURE_CODES: frozenset[int] = frozenset({125, 126, 127})
ERROR_TAIL_CHARS: int = 500
CMAKE_BUILD_DIR: str = "build-bench"
CMAKE_IGNORED: tuple[str, ...] = (".git", "build", "build-*")
CTEST_TOTAL: re.Pattern[str] = re.compile(r"^Total Tests: (\d+)$", re.MULTILINE)
CPPCHECK_MARKER: str = "cppcheck-finding:"
HIDDEN_TARGET: str = "bench_hidden"
SANITIZER_FLAGS: str = "-fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer -g"
# Included after every project() call: directory options reach the agent's targets even if it overwrites CMAKE_<LANG>_FLAGS.
SANITIZER_INCLUDE: str = "sanitizers.cmake"
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
    """`docker run --rm` under a unique name, removed on timeout: killing the client leaves the container running.

    A command's own exit code is a result; Docker failing to run it raises.
    """
    name: str = f"bench-{uuid.uuid4().hex}"
    try:
        outcome: subprocess.CompletedProcess[str] = run(
            ["docker", "run", "--rm", "--name", name, *arguments], cwd, stdin, timeout
        )
    except subprocess.TimeoutExpired:
        run(["docker", "rm", "-f", name], cwd)
        raise
    if outcome.returncode in DOCKER_FAILURE_CODES:
        failure: str = (outcome.stderr or outcome.stdout).strip()[-ERROR_TAIL_CHARS:]
        raise RuntimeError(f"docker run failed with exit code {outcome.returncode} in {cwd}: {failure}")
    return outcome


def gcc_toolchain_image() -> str:
    """Build the C and C++ scoring image once; later runs reuse it. Change the tag with the Dockerfile."""
    if run(["docker", "image", "inspect", GCC_TOOLCHAIN_IMAGE], BENCH_DIR).returncode != 0:
        built: subprocess.CompletedProcess[str] = run(
            ["docker", "build", "-q", "-t", GCC_TOOLCHAIN_IMAGE, "-"], BENCH_DIR, GCC_TOOLCHAIN_DOCKERFILE, BUILD_TIMEOUT_SECONDS
        )
        if built.returncode != 0:
            raise RuntimeError(f"cannot build {GCC_TOOLCHAIN_IMAGE}: {built.stderr.strip()[-ERROR_TAIL_CHARS:]}")
    return GCC_TOOLCHAIN_IMAGE


@dataclass(frozen=True)
class CmakeTask:
    """A CMake library task: the hidden test is appended to the agent's top-level CMakeLists.txt and linked to `target`."""

    standard: str  # a compile feature such as c_std_17
    target: str
    hidden_test: Path


def in_gcc_toolchain(copy: Path, script: str) -> subprocess.CompletedProcess[str]:
    """Run a shell script on the copy in the toolchain image; a build error is a result, Docker failing is not."""
    return docker_run(["-v", f"{copy}:/work", "-w", "/work", gcc_toolchain_image(), "sh", "-c", script], copy)


def cmake_tests_written(copy: Path) -> int:
    listed: subprocess.CompletedProcess[str] = in_gcc_toolchain(copy, f"ctest --test-dir {CMAKE_BUILD_DIR} -N")
    total: re.Match[str] | None = CTEST_TOTAL.search(listed.stdout)
    return int(total.group(1)) if total else 0


def cppcheck_findings(copy: Path) -> int:
    """0 when nothing was compiled: a header-only library or tests behind an option leave no compile commands."""
    commands: Path = copy / CMAKE_BUILD_DIR / "compile_commands.json"
    if not commands.is_file() or not json.loads(commands.read_text(encoding="utf-8")):
        return 0
    checked: subprocess.CompletedProcess[str] = in_gcc_toolchain(
        copy,
        f"cppcheck --project={CMAKE_BUILD_DIR}/compile_commands.json --enable=warning,style,performance"
        f" --quiet --template='{CPPCHECK_MARKER}{{file}}:{{line}}:{{id}}' -i{CMAKE_BUILD_DIR}",
    )
    if checked.returncode != 0:
        raise RuntimeError(f"cppcheck failed in {copy}: {checked.stderr.strip()[-ERROR_TAIL_CHARS:]}")
    return sum(1 for line in checked.stderr.splitlines() if line.startswith(CPPCHECK_MARKER))


def add_hidden_test(copy: Path, task: CmakeTask) -> None:
    hidden_dir: Path = copy / HIDDEN_TARGET
    hidden_dir.mkdir()
    shutil.copy(task.hidden_test, hidden_dir / task.hidden_test.name)
    snippet: str = (
        f"\nadd_executable({HIDDEN_TARGET} {HIDDEN_TARGET}/{task.hidden_test.name})\n"
        f"target_link_libraries({HIDDEN_TARGET} PRIVATE {task.target})\n"
        f"target_compile_features({HIDDEN_TARGET} PRIVATE {task.standard})\n"
        f"set_target_properties({HIDDEN_TARGET} PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${{CMAKE_BINARY_DIR}}/{HIDDEN_TARGET})\n"
    )
    with (copy / "CMakeLists.txt").open("a", encoding="utf-8") as lists:
        lists.write(snippet)
    (hidden_dir / SANITIZER_INCLUDE).write_text(
        f"add_compile_options({SANITIZER_FLAGS})\nadd_link_options({SANITIZER_FLAGS})\n", encoding="utf-8"
    )


def hidden_test_runs(copy: Path, build_dir: str, options: str) -> bool:
    built: subprocess.CompletedProcess[str] = in_gcc_toolchain(
        copy,
        f"cmake -S . -B {build_dir} {options} && cmake --build {build_dir} --target {HIDDEN_TARGET}"
        f" && ./{build_dir}/{HIDDEN_TARGET}/{HIDDEN_TARGET}",
    )
    return built.returncode == 0


def score_cmake_library(workspace: Path, task: CmakeTask) -> Metrics:
    """Build, CTest count and cppcheck on the agent's project, then the hidden test plain and under ASan and UBSan."""
    metrics: Metrics = {
        "hidden_test_passes": False,
        "sanitizers_clean": False,
        "compiles": False,
        "tests_written": 0,
        "cppcheck_findings": 0,
    }
    if not (workspace / "CMakeLists.txt").is_file():
        return metrics
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch), CMAKE_IGNORED)
        configure: str = f"cmake -S . -B {CMAKE_BUILD_DIR} -DCMAKE_EXPORT_COMPILE_COMMANDS=ON"
        metrics["compiles"] = in_gcc_toolchain(copy, f"{configure} && cmake --build {CMAKE_BUILD_DIR}").returncode == 0
        if not metrics["compiles"]:
            return metrics
        metrics["tests_written"] = cmake_tests_written(copy)
        metrics["cppcheck_findings"] = cppcheck_findings(copy)
        add_hidden_test(copy, task)
        plain: bool = hidden_test_runs(copy, "build-hidden", "-DCMAKE_BUILD_TYPE=Release")
        sanitized_options: str = f"-DCMAKE_BUILD_TYPE=Debug -DCMAKE_PROJECT_INCLUDE=/work/{HIDDEN_TARGET}/{SANITIZER_INCLUDE}"
        metrics["sanitizers_clean"] = hidden_test_runs(copy, "build-sanitized", sanitized_options)
        metrics["hidden_test_passes"] = plain and bool(metrics["sanitizers_clean"])
    return metrics


def copy_workspace(workspace: Path, destination: Path, ignored: Iterable[str] = (".git",)) -> Path:
    copy: Path = destination / "workspace"
    shutil.copytree(workspace, copy, ignore=shutil.ignore_patterns(*ignored))
    return copy


def source_files(workspace: Path, suffixes: tuple[str, ...], ignored: Iterable[str]) -> list[Path]:
    """Files whose name ends with one of the suffixes, relative to the workspace, outside the ignored directories."""
    skipped: frozenset[str] = frozenset(ignored)
    return [
        path.relative_to(workspace)
        for path in workspace.rglob("*")
        if path.name.endswith(suffixes) and path.is_file() and not skipped & set(path.relative_to(workspace).parts)
    ]


def is_node_test_file(path: Path) -> bool:
    return any(marker in path.name for marker in NODE_TEST_NAME_MARKERS) or bool(NODE_TEST_DIR_NAMES & set(path.parts[:-1]))


def count_js_tests(workspace: Path, files: Iterable[Path]) -> int:
    """`test(` and `it(` calls in the agent's test files (paths relative to the workspace)."""
    return sum(
        len(JS_TEST_CALL_PATTERN.findall((workspace / path).read_text(encoding="utf-8")))
        for path in files
        if is_node_test_file(path)
    )


def npm_install(copy: Path, packages: Iterable[str]) -> None:
    """The workspace's dependencies plus the pinned bench tools, its package.json left as it is.

    --legacy-peer-deps: a bench tool replacing the agent's version (vitest 4 over its vitest 3, say) would otherwise
    clash with the agent's packages that peer on the old one (@vitest/coverage-v8 3) and fail with ERESOLVE.
    The tools share the workspace's node_modules because the hidden tests import the agent's react through them.
    """
    outcome: subprocess.CompletedProcess[str] = run(
        [
            executable("npm"),
            "install",
            "--no-save",
            "--no-audit",
            "--no-fund",
            "--ignore-scripts",
            "--legacy-peer-deps",
            *packages,
        ],
        copy,
    )
    if outcome.returncode != 0:
        raise RuntimeError(f"npm install failed in {copy}: {outcome.stderr.strip()[-ERROR_TAIL_CHARS:]}")


def prettier_clean(copy: Path, patterns: Iterable[str]) -> bool:
    """Prettier --check with the agent's own Prettier config, if any; a file it cannot parse is not clean."""
    outcome: subprocess.CompletedProcess[str] = run(
        [executable("node"), "node_modules/prettier/bin/prettier.cjs", "--check", "--no-error-on-unmatched-pattern", *patterns],
        copy,
    )
    if outcome.returncode in {0, 1}:
        return outcome.returncode == 0
    if "SyntaxError" in outcome.stderr:
        return False
    raise RuntimeError(f"prettier failed in {copy}: {outcome.stderr.strip()[:ERROR_TAIL_CHARS]}")


def eslint_findings(copy: Path, config: str) -> int:
    """ESLint problems under the bench's config, the agent's own config ignored so every run is held to the same rules."""
    (copy / BENCH_ESLINT_CONFIG).write_text(config, encoding="utf-8")
    outcome: subprocess.CompletedProcess[str] = run_tool(
        [executable("node"), "node_modules/eslint/bin/eslint.js", "--config", BENCH_ESLINT_CONFIG, "--format", "json", "."],
        copy,
    )
    reports: list[dict[str, list[object]]] = json.loads(outcome.stdout)
    return sum(len(report["messages"]) for report in reports)


def is_python_test_file(path: Path) -> bool:
    return (
        path.name.startswith(PYTHON_TEST_FILE_PREFIXES)
        or path.stem.endswith("_test")
        or bool(PYTHON_TEST_DIR_NAMES & set(path.parts[:-1]))
    )


def git_output(workspace: Path, *arguments: str) -> str:
    outcome: subprocess.CompletedProcess[str] = run(["git", "-C", str(workspace), *arguments], workspace)
    if outcome.returncode != 0:
        raise RuntimeError(f"git {arguments[0]} failed in {workspace}: {outcome.stderr.strip()[:ERROR_TAIL_CHARS]}")
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
