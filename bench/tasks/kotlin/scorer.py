"""Score the kotlin task: hidden JUnit 5 test, Kotlin compiler warnings, the agent's own tests.

Gradle and the JDK run in Docker; the Gradle user home lives in a named volume, so after the first run
(about 2 minutes of plugin and dependency downloads) the build needs no new download.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from xml.etree import ElementTree

from score import Metrics
from scorer_lib import ERROR_TAIL_CHARS, copy_workspace, docker_run, source_files

TASK_DIR: Path = Path(__file__).resolve().parent
HIDDEN_TEST: Path = TASK_DIR / "BenchHiddenTest.kt"
HIDDEN_TEST_PACKAGE_DIR: Path = Path("src") / "test" / "kotlin" / "com" / "example" / "csv"
HIDDEN_TEST_REPORT: Path = Path("build") / "test-results" / "test" / "TEST-com.example.csv.BenchHiddenTest.xml"
BUILD_FILE: str = "build.gradle.kts"
GRADLE_IMAGE: str = "gradle:9.9.1-jdk21-noble@sha256:f498eaf1a4824b42d0b7bb2d14c18dd1d9f01f5a56dcd73e6acc7ce4fb89ead9"
GRADLE_HOME_VOLUME: str = "bench-gradle-home"
GRADLE: tuple[str, ...] = ("gradle", "--no-daemon", "--console=plain")
NETWORK_FAILURES: tuple[str, ...] = ("Could not GET", "Could not HEAD", "UnknownHostException")
# Appended when the agent's build declares no JUnit: the hidden test needs Jupiter on the JUnit Platform.
JUNIT_SNIPPET: str = """
dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter:6.0.3")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher:6.0.3")
}

tasks.withType<Test>().configureEach {
    useJUnitPlatform()
}
"""
JUNIT_MARKERS: tuple[str, ...] = ("junit", 'kotlin("test")')
IGNORED_PARTS: tuple[str, ...] = (".git", "build", ".gradle", ".kotlin")
TEST_ANNOTATION: re.Pattern[str] = re.compile(r"@(?:Test|ParameterizedTest|RepeatedTest|TestFactory|TestTemplate)\b")
WARNING_LINE: re.Pattern[str] = re.compile(r"^w: ", re.MULTILINE)


def count_tests_written(workspace: Path) -> int:
    sources: list[Path] = source_files(workspace, (".kt",), IGNORED_PARTS)
    return sum(len(TEST_ANNOTATION.findall((workspace / path).read_text(encoding="utf-8", errors="replace"))) for path in sources)


def in_container(copy: Path, command: list[str]) -> subprocess.CompletedProcess[str]:
    """Run Gradle in its image; a build error is a result, Docker or the network failing means the tool did not run."""
    mounts: list[str] = ["-v", f"{copy}:/work", "-v", f"{GRADLE_HOME_VOLUME}:/cache", "-e", "GRADLE_USER_HOME=/cache"]
    outcome: subprocess.CompletedProcess[str] = docker_run([*mounts, "-w", "/work", GRADLE_IMAGE, *command], copy)
    output: str = outcome.stdout + outcome.stderr
    if any(marker in output for marker in NETWORK_FAILURES):
        raise RuntimeError(f"{command[:4]} did not run in {copy}: {output.strip()[-ERROR_TAIL_CHARS:]}")
    return outcome


def add_junit_dependency(build_file: Path) -> None:
    text: str = build_file.read_text(encoding="utf-8")
    if not any(marker in text for marker in JUNIT_MARKERS):
        build_file.write_text(text + JUNIT_SNIPPET, encoding="utf-8")


def hidden_report_is_green(report: Path) -> bool:
    if not report.is_file():
        return False
    suite: ElementTree.Element = ElementTree.parse(report).getroot()
    counts: dict[str, int] = {key: int(suite.get(key, "0")) for key in ("tests", "failures", "errors")}
    return counts["tests"] > 0 and counts["failures"] == 0 and counts["errors"] == 0


def hidden_test_passes(copy: Path) -> bool:
    agent_tests: Path = copy / "src" / "test"
    if agent_tests.is_dir():
        shutil.rmtree(agent_tests)
    (copy / HIDDEN_TEST_PACKAGE_DIR).mkdir(parents=True)
    shutil.copy(HIDDEN_TEST, copy / HIDDEN_TEST_PACKAGE_DIR / HIDDEN_TEST.name)
    add_junit_dependency(copy / BUILD_FILE)
    tested: subprocess.CompletedProcess[str] = in_container(copy, [*GRADLE, "test"])
    return tested.returncode == 0 and hidden_report_is_green(copy / HIDDEN_TEST_REPORT)


def score(workspace: Path) -> Metrics:
    metrics: Metrics = {
        "hidden_test_passes": False,
        "tests_written": count_tests_written(workspace),
        "compiles": False,
        "warnings": 0,
    }
    if not (workspace / BUILD_FILE).is_file():
        return metrics
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch), IGNORED_PARTS)
        compiled: subprocess.CompletedProcess[str] = in_container(copy, [*GRADLE, "compileKotlin"])
        metrics["compiles"] = compiled.returncode == 0
        metrics["warnings"] = len(WARNING_LINE.findall(compiled.stdout + compiled.stderr))
        if metrics["compiles"]:
            metrics["hidden_test_passes"] = hidden_test_passes(copy)
    return metrics
