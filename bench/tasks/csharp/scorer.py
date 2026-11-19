"""Score the csharp task: hidden xUnit test, compiler warnings, the agent's own tests and project settings."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from score import Metrics, run

TASK_DIR: Path = Path(__file__).resolve().parent
HIDDEN_TEST_DIR: Path = TASK_DIR / "hidden_test"
LIBRARY_PROJECT: Path = Path("src") / "Billing" / "Billing.csproj"
IGNORED_PARTS: frozenset[str] = frozenset({".git", "bin", "obj"})
# Warnings stay warnings so they can be counted, even when the agent turned them into errors.
WARNINGS_NOT_ERRORS: tuple[str, ...] = ("-p:TreatWarningsAsErrors=false", "-p:WarningsAsErrors=")
DOTNET_QUIET: tuple[str, ...] = ("-nologo", "-clp:NoSummary")
WARNING_LINE: re.Pattern[str] = re.compile(r": warning [A-Z]+\d+:")
# shortcut: counts test methods by attribute, so an NUnit [TestCase] without [Test] is missed; run the tests if that matters.
TEST_ATTRIBUTE: re.Pattern[str] = re.compile(r"\[\s*(?:Fact|Theory|Test|TestMethod|DataTestMethod)\b")
NULLABLE_ENABLED: re.Pattern[str] = re.compile(r"<Nullable>\s*enable\s*</Nullable>", re.IGNORECASE)
WARNINGS_AS_ERRORS: re.Pattern[str] = re.compile(r"<TreatWarningsAsErrors>\s*true\s*</TreatWarningsAsErrors>", re.IGNORECASE)
NUGET_UNREACHABLE: str = "error NU1301"


def workspace_files(workspace: Path, pattern: str) -> list[Path]:
    return [path for path in workspace.rglob(pattern) if not IGNORED_PARTS & set(path.relative_to(workspace).parts)]


def project_settings_text(workspace: Path) -> str:
    settings: list[Path] = [*workspace_files(workspace, "*.csproj"), *workspace_files(workspace, "Directory.Build.props")]
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in settings)


def count_tests_written(workspace: Path) -> int:
    sources: list[Path] = workspace_files(workspace, "*.cs")
    return sum(len(TEST_ATTRIBUTE.findall(path.read_text(encoding="utf-8", errors="replace"))) for path in sources)


def dotnet(arguments: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run dotnet; a compile error is a result, an unreachable package source means the tool did not run."""
    outcome: subprocess.CompletedProcess[str] = run(["dotnet", *arguments, *DOTNET_QUIET, *WARNINGS_NOT_ERRORS], cwd)
    if NUGET_UNREACHABLE in outcome.stdout:
        raise RuntimeError(f"dotnet {arguments[0]} could not reach NuGet in {cwd}: {outcome.stdout.strip()[-500:]}")
    return outcome


def build(copy: Path) -> tuple[bool, int]:
    built: subprocess.CompletedProcess[str] = dotnet(["build", str(LIBRARY_PROJECT)], copy)
    warnings: set[str] = {line.strip() for line in built.stdout.splitlines() if WARNING_LINE.search(line)}
    return built.returncode == 0, len(warnings)


def hidden_test_passes(copy: Path, scratch: Path) -> bool:
    test_project: Path = scratch / "hidden_test"
    shutil.copytree(HIDDEN_TEST_DIR, test_project)
    library: Path = copy / LIBRARY_PROJECT
    tested: subprocess.CompletedProcess[str] = dotnet(["test", f"-p:BenchLibraryProject={library}"], test_project)
    return tested.returncode == 0


def score(workspace: Path) -> Metrics:
    settings: str = project_settings_text(workspace)
    metrics: Metrics = {
        "hidden_test_passes": False,
        "tests_written": count_tests_written(workspace),
        "compiles": False,
        "warnings": 0,
        "nullable_enabled": bool(NULLABLE_ENABLED.search(settings)),
        "warnings_as_errors": bool(WARNINGS_AS_ERRORS.search(settings)),
    }
    if not (workspace / LIBRARY_PROJECT).is_file():
        return metrics
    with tempfile.TemporaryDirectory() as scratch_name:
        scratch: Path = Path(scratch_name)
        copy: Path = scratch / "workspace"
        shutil.copytree(workspace, copy, ignore=shutil.ignore_patterns(*IGNORED_PARTS))
        compiles, warnings = build(copy)
        metrics["compiles"] = compiles
        metrics["warnings"] = warnings
        metrics["hidden_test_passes"] = compiles and hidden_test_passes(copy, scratch)
    return metrics
