"""Score the java task: hidden JUnit 5 test, javac -Xlint:all warnings, the agent's own tests and build settings.

Maven and the JDK run in Docker; the local repository lives in a named volume so later runs reuse downloads.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from xml.etree import ElementTree

from score import Metrics, run

TASK_DIR: Path = Path(__file__).resolve().parent
HIDDEN_TEST: Path = TASK_DIR / "BenchHiddenTest.java"
HIDDEN_TEST_PACKAGE_DIR: Path = Path("src") / "test" / "java" / "com" / "example" / "durations"
HIDDEN_TEST_REPORT: Path = Path("target") / "surefire-reports" / "TEST-com.example.durations.BenchHiddenTest.xml"
MAIN_SOURCES: Path = Path("src") / "main" / "java"
MAVEN_IMAGE: str = "maven:3.9-eclipse-temurin-21"
MAVEN_CACHE_VOLUME: str = "bench-maven-repository"
MAVEN: tuple[str, ...] = ("mvn", "-q", "-B")
DOCKER_FAILURE_CODES: frozenset[int] = frozenset({125, 126, 127})
NETWORK_FAILURE: str = "Could not transfer artifact"
POM_NAMESPACE: str = "http://maven.apache.org/POM/4.0.0"
JUNIT_GROUP: str = "org.junit.jupiter"
JUNIT_ARTIFACT: str = "junit-jupiter"
JUNIT_VERSION: str = "5.11.4"
IGNORED_PARTS: frozenset[str] = frozenset({".git", "target"})
TEST_ANNOTATION: re.Pattern[str] = re.compile(r"@(?:Test|ParameterizedTest|RepeatedTest|TestFactory|TestTemplate)\b")
WARNING_LINE: re.Pattern[str] = re.compile(r": warning:")
LINT_SCRIPT: str = (
    "mvn -q -B dependency:build-classpath -Dmdep.outputFile=/tmp/classpath.txt"
    ' && javac -Xlint:all -Xmaxwarns 10000 -d /tmp/lint -cp "$(cat /tmp/classpath.txt)"'
    f" $(find {MAIN_SOURCES.as_posix()} -name '*.java')"
)


def workspace_files(workspace: Path, pattern: str) -> list[Path]:
    return [path for path in workspace.rglob(pattern) if not IGNORED_PARTS & set(path.relative_to(workspace).parts)]


def count_tests_written(workspace: Path) -> int:
    sources: list[Path] = workspace_files(workspace, "*.java")
    return sum(len(TEST_ANNOTATION.findall(path.read_text(encoding="utf-8", errors="replace"))) for path in sources)


def in_container(copy: Path, command: list[str]) -> subprocess.CompletedProcess[str]:
    """Run in the Maven image; a build error is a result, Docker or the network failing means the tool did not run."""
    mounts: list[str] = ["-v", f"{copy}:/work", "-v", f"{MAVEN_CACHE_VOLUME}:/root/.m2", "-w", "/work"]
    outcome: subprocess.CompletedProcess[str] = run(["docker", "run", "--rm", *mounts, MAVEN_IMAGE, *command], copy)
    if outcome.returncode in DOCKER_FAILURE_CODES or NETWORK_FAILURE in outcome.stdout:
        raise RuntimeError(f"{command[:3]} did not run in {copy}: {(outcome.stderr or outcome.stdout).strip()[-500:]}")
    return outcome


def count_lint_warnings(copy: Path) -> int:
    if not any((copy / MAIN_SOURCES).rglob("*.java")):
        return 0
    linted: subprocess.CompletedProcess[str] = in_container(copy, ["sh", "-c", LINT_SCRIPT])
    if linted.returncode != 0:
        raise RuntimeError(f"javac -Xlint:all failed in {copy} after mvn compile passed: {linted.stderr.strip()[-500:]}")
    return sum(1 for line in linted.stderr.splitlines() if WARNING_LINE.search(line))


def add_junit_dependency(pom: Path) -> None:
    """Give the copy JUnit Jupiter (with params) when the agent's pom does not declare the aggregate artifact."""
    if f"<artifactId>{JUNIT_ARTIFACT}</artifactId>" in pom.read_text(encoding="utf-8"):
        return
    ElementTree.register_namespace("", POM_NAMESPACE)
    tree: ElementTree.ElementTree[ElementTree.Element] = ElementTree.parse(pom)
    project: ElementTree.Element = tree.getroot()
    prefix: str = project.tag[: project.tag.index("}") + 1] if project.tag.startswith("{") else ""
    dependencies: ElementTree.Element | None = project.find(f"{prefix}dependencies")
    if dependencies is None:
        dependencies = ElementTree.SubElement(project, f"{prefix}dependencies")
    dependency: ElementTree.Element = ElementTree.SubElement(dependencies, f"{prefix}dependency")
    coordinates: dict[str, str] = {
        "groupId": JUNIT_GROUP,
        "artifactId": JUNIT_ARTIFACT,
        "version": JUNIT_VERSION,
        "scope": "test",
    }
    for name, value in coordinates.items():
        ElementTree.SubElement(dependency, f"{prefix}{name}").text = value
    tree.write(pom, encoding="utf-8", xml_declaration=True)


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
    add_junit_dependency(copy / "pom.xml")
    tested: subprocess.CompletedProcess[str] = in_container(
        copy, [*MAVEN, "test", "-DskipTests=false", "-Dmaven.test.skip=false"]
    )
    return tested.returncode == 0 and hidden_report_is_green(copy / HIDDEN_TEST_REPORT)


def score(workspace: Path) -> Metrics:
    pom_text: str = (workspace / "pom.xml").read_text(encoding="utf-8") if (workspace / "pom.xml").is_file() else ""
    metrics: Metrics = {
        "hidden_test_passes": False,
        "tests_written": count_tests_written(workspace),
        "compiles": False,
        "warnings": 0,
        "compiler_lint_enabled": "-Xlint" in pom_text,
        "warnings_as_errors": "-Werror" in pom_text or "<failOnWarning>true</failOnWarning>" in pom_text,
    }
    if not pom_text:
        return metrics
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = Path(scratch) / "workspace"
        shutil.copytree(workspace, copy, ignore=shutil.ignore_patterns(*IGNORED_PARTS))
        compiles: bool = in_container(copy, [*MAVEN, "compile"]).returncode == 0
        metrics["compiles"] = compiles
        if compiles:
            metrics["warnings"] = count_lint_warnings(copy)
            metrics["hidden_test_passes"] = hidden_test_passes(copy)
    return metrics
