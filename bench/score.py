"""Score the runs written by bench/run.sh and print one JSON summary per arm and task.

Usage: python bench/score.py <out-dir>
Needs pytest, pytest-cov, mypy, ruff and PyYAML in the running interpreter, and Docker for
hadolint, promtool and the container health check.
"""

import json
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections.abc import Callable
from http import HTTPStatus
from pathlib import Path
from typing import Any

import yaml

BENCH_DIR: Path = Path(__file__).resolve().parent
HADOLINT_IMAGE: str = "hadolint/hadolint:v2.12.0"
PROMETHEUS_IMAGE: str = "prom/prometheus:v3.9.1"
HOST_PORT: int = 18000
SERVICE_PORT: int = 8000
HEALTH_URL: str = f"http://127.0.0.1:{HOST_PORT}/health"
HTTP_TIMEOUT_SECONDS: int = 2
LINT_OK_CODES: frozenset[int] = frozenset({0, 1})
HEALTH_TIMEOUT_SECONDS: int = 60
TEST_FILE_PREFIXES: tuple[str, ...] = ("test_", "conftest")
TEST_DIR_NAMES: frozenset[str] = frozenset({"tests", "test"})
EMPTY_CONFIG: Path = BENCH_DIR / "empty.toml"
PYTEST_ISOLATED: tuple[str, ...] = (sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=")
DOCKER_KEYS: tuple[str, ...] = (
    "container_healthy",
    "base_pinned_by_digest",
    "non_root_user",
    "healthcheck",
    "dockerignore",
    "compose_valid",
    "compose_hardened",
    "compose_resource_limits",
)
COMPOSE_FILE_NAMES: tuple[str, ...] = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")

Metrics = dict[str, float | int | bool | None]
USAGE_KEYS: tuple[str, ...] = ("cost_usd", "seconds", "input_tokens", "output_tokens", "turns")


def run(command: list[str], cwd: Path, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, input=stdin, capture_output=True, text=True, check=False)


def run_tool(command: list[str], cwd: Path, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    """Run a checker whose exit code is 0 (clean) or 1 (findings); anything else means it did not run."""
    outcome: subprocess.CompletedProcess[str] = run(command, cwd, stdin)
    if outcome.returncode not in LINT_OK_CODES:
        raise RuntimeError(f"{command[:4]} failed in {cwd}: {outcome.stderr.strip()[:500]}")
    return outcome


def is_test_file(path: Path) -> bool:
    return path.name.startswith(TEST_FILE_PREFIXES) or path.stem.endswith("_test") or bool(TEST_DIR_NAMES & set(path.parts))


def python_files(workspace: Path) -> list[Path]:
    return [path.relative_to(workspace) for path in workspace.rglob("*.py") if ".venv" not in path.parts]


def usage_metrics(result_path: Path) -> Metrics:
    empty: Metrics = {key: None for key in USAGE_KEYS} | {"completed": False}
    text: str = result_path.read_text(encoding="utf-8") if result_path.is_file() else ""
    try:
        result: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError:
        return empty
    models: dict[str, dict[str, int]] = result.get("modelUsage", {})
    input_tokens: int = sum(
        usage.get("inputTokens", 0) + usage.get("cacheReadInputTokens", 0) + usage.get("cacheCreationInputTokens", 0)
        for usage in models.values()
    )
    output_tokens: int = sum(usage.get("outputTokens", 0) for usage in models.values())
    return {
        "cost_usd": result.get("total_cost_usd"),
        "seconds": result["duration_ms"] / 1000 if "duration_ms" in result else None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "turns": result.get("num_turns"),
        "completed": result.get("subtype") == "success" and not result.get("is_error", False),
    }


def count_collected_tests(workspace: Path) -> int:
    collected: subprocess.CompletedProcess[str] = run([*PYTEST_ISOLATED, "--collect-only"], workspace)
    return sum(1 for line in collected.stdout.splitlines() if "::" in line)


def line_coverage(workspace: Path, sources: list[Path]) -> float:
    if not sources:
        return 0.0
    report_path: Path = workspace / ".bench-coverage.json"
    run(
        [*PYTEST_ISOLATED, "--cov=.", f"--cov-config={EMPTY_CONFIG}", f"--cov-report=json:{report_path}"],
        workspace,
    )
    if not report_path.is_file():
        return 0.0
    report: dict[str, Any] = json.loads(report_path.read_text(encoding="utf-8"))
    source_names: set[str] = {path.as_posix() for path in sources}
    files: dict[str, Any] = {
        name.replace("\\", "/"): entry for name, entry in report["files"].items() if name.replace("\\", "/") in source_names
    }
    statements: int = sum(entry["summary"]["num_statements"] for entry in files.values())
    covered: int = sum(entry["summary"]["covered_lines"] for entry in files.values())
    return round(100 * covered / statements, 1) if statements else 0.0


def hidden_test_passes(workspace: Path, hidden_test: Path) -> bool:
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = Path(scratch) / "workspace"
        shutil.copytree(workspace, copy, ignore=shutil.ignore_patterns(".git", ".venv"))
        shutil.copy(hidden_test, copy / "bench_hidden_test.py")
        outcome: subprocess.CompletedProcess[str] = run([*PYTEST_ISOLATED, "-p", "no:cov", "bench_hidden_test.py"], copy)
    return outcome.returncode == 0


def count_mypy_strict_errors(workspace: Path, sources: list[Path]) -> int:
    if not sources:
        return 0
    checked: subprocess.CompletedProcess[str] = run_tool(
        [sys.executable, "-m", "mypy", "--strict", "--no-incremental", f"--config-file={EMPTY_CONFIG}", *map(str, sources)],
        workspace,
    )
    return sum(1 for line in checked.stdout.splitlines() if ": error:" in line)


def count_ruff_findings(workspace: Path) -> int:
    checked: subprocess.CompletedProcess[str] = run_tool(
        [sys.executable, "-m", "ruff", "check", "--isolated", "--output-format", "json", "--exclude", ".venv", "."], workspace
    )
    return len(json.loads(checked.stdout or "[]"))


def has_strict_tool_config(workspace: Path) -> bool:
    pyproject: Path = workspace / "pyproject.toml"
    text: str = pyproject.read_text(encoding="utf-8") if pyproject.is_file() else ""
    has_ruff: bool = "[tool.ruff" in text or (workspace / "ruff.toml").is_file()
    has_strict_types: bool = "strict = true" in text or (workspace / "mypy.ini").is_file() or "typeCheckingMode" in text
    return has_ruff and has_strict_types


def score_python(workspace: Path) -> Metrics:
    files: list[Path] = python_files(workspace)
    sources: list[Path] = [path for path in files if not is_test_file(path)]
    return {
        "hidden_test_passes": hidden_test_passes(workspace, BENCH_DIR / "tasks" / "python" / "hidden_test.py"),
        "tests_written": count_collected_tests(workspace),
        "line_coverage": line_coverage(workspace, sources),
        "mypy_strict_errors": count_mypy_strict_errors(workspace, sources),
        "ruff_findings": count_ruff_findings(workspace),
        "strict_tool_config": has_strict_tool_config(workspace),
    }


def docker_mount(workspace: Path) -> list[str]:
    return ["-v", f"{workspace}:/work", "-w", "/work"]


def compose_file(workspace: Path) -> Path | None:
    return next((workspace / name for name in COMPOSE_FILE_NAMES if (workspace / name).is_file()), None)


def compose_document(workspace: Path) -> dict[str, Any]:
    path: Path | None = compose_file(workspace)
    if path is None:
        return {}
    loaded: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def compose_services(workspace: Path) -> list[dict[str, Any]]:
    services: Any = compose_document(workspace).get("services", {})
    return [service for service in services.values() if isinstance(service, dict)] if isinstance(services, dict) else []


def compose_is_valid(workspace: Path) -> bool:
    path: Path | None = compose_file(workspace)
    return path is not None and run(["docker", "compose", "-f", path.name, "config", "-q"], workspace).returncode == 0


def count_hadolint_findings(dockerfile: Path) -> int:
    linted: subprocess.CompletedProcess[str] = run_tool(
        ["docker", "run", "--rm", "-i", HADOLINT_IMAGE, "hadolint", "-f", "json", "-"],
        dockerfile.parent,
        dockerfile.read_text(encoding="utf-8"),
    )
    return len(json.loads(linted.stdout or "[]"))


def wait_for_health() -> bool:
    deadline: float = time.monotonic() + HEALTH_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=HTTP_TIMEOUT_SECONDS) as response:
                status: int = response.status
                return status == HTTPStatus.OK
        except OSError:
            time.sleep(1)
    return False


def container_serves_health(workspace: Path, tag: str) -> bool:
    if run(["docker", "build", "-q", "-t", tag, "."], workspace).returncode != 0:
        return False
    started: subprocess.CompletedProcess[str] = run(
        ["docker", "run", "-d", "--rm", "-p", f"{HOST_PORT}:{SERVICE_PORT}", tag], workspace
    )
    if started.returncode != 0:
        return False
    healthy: bool = wait_for_health()
    run(["docker", "rm", "-f", started.stdout.strip()], workspace)
    return healthy


def dockerfile_lines(dockerfile: Path) -> list[str]:
    return [line.strip() for line in dockerfile.read_text(encoding="utf-8").splitlines()]


def last_user_is_not_root(lines: list[str]) -> bool:
    users: list[str] = [line.split()[1] for line in lines if line.upper().startswith("USER ") and len(line.split()) > 1]
    return bool(users) and users[-1] not in {"root", "0", "0:0"}


def service_is_hardened(service: dict[str, Any]) -> bool:
    security: list[str] = [str(option) for option in service.get("security_opt", [])]
    dropped: list[str] = [str(capability) for capability in service.get("cap_drop", [])]
    no_new_privileges: bool = any("no-new-privileges" in option for option in security)
    return service.get("read_only") is True and (no_new_privileges or "ALL" in dropped)


def service_has_limits(service: dict[str, Any]) -> bool:
    deploy: dict[str, Any] = service.get("deploy") or {}
    return "mem_limit" in service or "resources" in deploy


def score_docker(workspace: Path) -> Metrics:
    dockerfile: Path = workspace / "Dockerfile"
    if not dockerfile.is_file():
        return dict.fromkeys(DOCKER_KEYS, False) | {"hadolint_findings": None}
    lines: list[str] = dockerfile_lines(dockerfile)
    services: list[dict[str, Any]] = compose_services(workspace)
    return {
        "container_healthy": container_serves_health(
            workspace, f"bench-{workspace.parents[2].name}-{workspace.parents[1].name}-{workspace.parent.name}"
        ),
        "hadolint_findings": count_hadolint_findings(dockerfile),
        "base_pinned_by_digest": any(line.upper().startswith("FROM ") and "@sha256:" in line for line in lines),
        "non_root_user": last_user_is_not_root(lines),
        "healthcheck": any(line.upper().startswith("HEALTHCHECK ") for line in lines)
        or any("healthcheck" in service for service in services),
        "dockerignore": (workspace / ".dockerignore").is_file(),
        "compose_valid": compose_is_valid(workspace),
        "compose_hardened": any(map(service_is_hardened, services)),
        "compose_resource_limits": any(map(service_has_limits, services)),
    }


def promtool(workspace: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return run(
        ["docker", "run", "--rm", *docker_mount(workspace), "--entrypoint", "promtool", PROMETHEUS_IMAGE, *arguments], workspace
    )


def yaml_documents(workspace: Path) -> list[tuple[Path, dict[str, Any]]]:
    documents: list[tuple[Path, dict[str, Any]]] = []
    for path in [*workspace.rglob("*.yml"), *workspace.rglob("*.yaml")]:
        if ".git" in path.parts:
            continue
        try:
            loaded: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            print(f"score: {path} is not valid YAML, skipped: {error}", file=sys.stderr)
            continue
        if isinstance(loaded, dict):
            documents.append((path, loaded))
    return documents


def alert_rules(documents: list[tuple[Path, dict[str, Any]]]) -> list[dict[str, Any]]:
    return [
        rule
        for _, document in documents
        if "tests" not in document
        for group in document.get("groups", []) or []
        if isinstance(group, dict)
        for rule in group.get("rules", []) or []
        if isinstance(rule, dict) and "alert" in rule
    ]


def share(rules: list[dict[str, Any]], has: Callable[[dict[str, Any]], bool]) -> float:
    return round(sum(map(has, rules)) / len(rules), 2) if rules else 0.0


def rule_tests_pass(workspace: Path, test_files: list[Path]) -> bool | None:
    if not test_files:
        return None
    names: list[str] = [path.relative_to(workspace).as_posix() for path in test_files]
    return promtool(workspace, "test", "rules", *names).returncode == 0


def rules_valid(workspace: Path, rule_files: list[Path]) -> bool:
    names: list[str] = [path.relative_to(workspace).as_posix() for path in rule_files]
    return bool(names) and promtool(workspace, "check", "rules", *names).returncode == 0


def prometheus_image_pinned(services: list[dict[str, Any]]) -> bool:
    images: list[str] = [str(service.get("image", "")) for service in services if "prometheus" in str(service.get("image", ""))]
    return bool(images) and all("@sha256:" in image or (":" in image and not image.endswith(":latest")) for image in images)


def score_prometheus(workspace: Path) -> Metrics:
    documents: list[tuple[Path, dict[str, Any]]] = yaml_documents(workspace)
    rules: list[dict[str, Any]] = alert_rules(documents)
    expressions: str = " ".join(str(rule.get("expr", "")) for rule in rules)
    test_files: list[Path] = [path for path, document in documents if "tests" in document and "rule_files" in document]
    rule_files: list[Path] = [path for path, document in documents if "groups" in document and "tests" not in document]
    return {
        # --syntax-only: rule_files often name the path inside the container (/etc/prometheus/...).
        "config_valid": (workspace / "prometheus.yml").is_file()
        and promtool(workspace, "check", "config", "--syntax-only", "prometheus.yml").returncode == 0,
        "rules_valid": rules_valid(workspace, rule_files),
        "alerts": len(rules),
        "uses_histogram_quantile": "histogram_quantile" in expressions and "_bucket" in expressions,
        "alerts_with_for": share(rules, lambda rule: "for" in rule),
        "alerts_with_severity": share(rules, lambda rule: "severity" in (rule.get("labels") or {})),
        "alerts_with_summary": share(rules, lambda rule: "summary" in (rule.get("annotations") or {})),
        "alerts_with_runbook": share(rules, lambda rule: "runbook_url" in (rule.get("annotations") or {})),
        "rule_test_files": len(test_files),
        "rule_tests_pass": rule_tests_pass(workspace, test_files),
        "compose_valid": compose_is_valid(workspace),
        "prometheus_image_pinned": prometheus_image_pinned(compose_services(workspace)),
    }


SCORERS: dict[str, Callable[[Path], Metrics]] = {
    "python": score_python,
    "docker": score_docker,
    "prometheus": score_prometheus,
}


def score_run(run_dir: Path, task: str) -> Metrics:
    return {**usage_metrics(run_dir / "result.json"), **SCORERS[task](run_dir / "workspace")}


def summarize(runs: list[Metrics]) -> Metrics:
    summary: Metrics = {}
    keys: list[str] = list(dict.fromkeys(key for run_metrics in runs for key in run_metrics))
    for key in keys:
        values: list[float | int | bool] = [value for run_metrics in runs if (value := run_metrics.get(key)) is not None]
        summary[key] = round(statistics.fmean(values), 3) if values else None
    return summary


def require_docker() -> None:
    """docker exits 1 when the daemon is down, the same code as a lint finding, so check it once up front."""
    if run(["docker", "info", "--format", "{{.ServerVersion}}"], BENCH_DIR).returncode != 0:
        raise RuntimeError("Docker daemon is not reachable: start it before scoring")


def main(out_dir: Path) -> None:
    require_docker()
    report: dict[str, dict[str, dict[str, Any]]] = {}
    for arm_dir in sorted(path for path in out_dir.iterdir() if path.is_dir()):
        for task_dir in sorted(path for path in arm_dir.iterdir() if path.name in SCORERS):
            runs: list[Metrics] = [score_run(run_dir, task_dir.name) for run_dir in sorted(task_dir.iterdir())]
            report.setdefault(arm_dir.name, {})[task_dir.name] = {"runs": runs, "mean": summarize(runs)}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
