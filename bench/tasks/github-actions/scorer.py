"""Score the github-actions task: a workflow that runs the pytest suite on push and pull_request.

zizmor runs offline from the scoring interpreter's environment (`pip install zizmor`), or from PATH.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from score import Metrics, docker_mount, run

ACTIONLINT_IMAGE: str = "rhysd/actionlint:1.7.7"
ACTIONLINT_OK_CODES: frozenset[int] = frozenset({0, 1})
ERROR_TAIL_CHARS: int = 500
WORKFLOW_DIR: str = ".github/workflows"
WORKFLOW_PATTERNS: tuple[str, ...] = ("*.yml", "*.yaml")
REQUIRED_EVENTS: frozenset[str] = frozenset({"push", "pull_request"})
PYTHON_VERSIONS: tuple[str, ...] = ("3.12", "3.13")
TEST_COMMAND: str = "pytest"
FULL_SHA_REF: re.Pattern[str] = re.compile(r"@[0-9a-f]{40}$")
UNPINNABLE_PREFIXES: tuple[str, ...] = ("./", "docker://")
EMPTY_METRICS: Metrics = {
    "hidden_test_passes": False,
    "actions_pinned_by_sha": False,
    "top_level_permissions": False,
    "zizmor_findings": 0,
}


def workflow_files(workspace: Path) -> list[Path]:
    return sorted(path for pattern in WORKFLOW_PATTERNS for path in (workspace / WORKFLOW_DIR).glob(pattern))


def load_workflow(path: Path) -> dict[str, Any]:
    try:
        loaded: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        print(f"score: {path} is not valid YAML: {error}", file=sys.stderr)
        return {}
    if not isinstance(loaded, dict):
        return {}
    # YAML 1.1 reads the bare key `on` as the boolean True.
    return {"on" if key is True else str(key): value for key, value in loaded.items()}


def actionlint_passes(workspace: Path, paths: list[Path]) -> bool:
    """Files are named explicitly: without them actionlint needs a .git folder to find the project."""
    names: list[str] = [path.relative_to(workspace).as_posix() for path in paths]
    outcome: subprocess.CompletedProcess[str] = run(
        ["docker", "run", "--rm", *docker_mount(workspace), ACTIONLINT_IMAGE, *names], workspace
    )
    if outcome.returncode not in ACTIONLINT_OK_CODES:
        raise RuntimeError(f"actionlint failed: {outcome.stderr.strip()[-ERROR_TAIL_CHARS:]}")
    return outcome.returncode == 0


def trigger_events(workflow: dict[str, Any]) -> set[str]:
    triggers: Any = workflow.get("on")
    if isinstance(triggers, str):
        return {triggers}
    return {str(event) for event in triggers} if isinstance(triggers, list | dict) else set()


def jobs(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    found: Any = workflow.get("jobs")
    return [job for job in found.values() if isinstance(job, dict)] if isinstance(found, dict) else []


def steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    return [step for job in jobs(workflow) for step in job.get("steps") or [] if isinstance(step, dict)]


def runs_tests_on_versions(workflow: dict[str, Any]) -> bool:
    runs_tests: bool = any(TEST_COMMAND in str(step.get("run", "")) for step in steps(workflow))
    job_text: str = str(jobs(workflow))
    return runs_tests and all(version in job_text for version in PYTHON_VERSIONS)


def requirements_hold(workflows: list[dict[str, Any]]) -> bool:
    return any(REQUIRED_EVENTS <= trigger_events(workflow) and runs_tests_on_versions(workflow) for workflow in workflows)


def action_references(workflow: dict[str, Any]) -> list[str]:
    job_uses: list[str] = [str(job["uses"]) for job in jobs(workflow) if "uses" in job]
    step_uses: list[str] = [str(step["uses"]) for step in steps(workflow) if "uses" in step]
    return [reference for reference in job_uses + step_uses if not reference.startswith(UNPINNABLE_PREFIXES)]


def actions_pinned_by_sha(workflows: list[dict[str, Any]]) -> bool:
    references: list[str] = [reference for workflow in workflows for reference in action_references(workflow)]
    return all(FULL_SHA_REF.search(reference) for reference in references)


def zizmor_command() -> str:
    found: str | None = shutil.which("zizmor", path=str(Path(sys.executable).parent)) or shutil.which("zizmor")
    if found is None:
        raise RuntimeError("zizmor not found: pip install zizmor into the scoring interpreter")
    return found


def count_zizmor_findings(workspace: Path) -> int:
    outcome: subprocess.CompletedProcess[str] = run(
        [zizmor_command(), "--offline", "--no-config", "--no-ignores", "--no-exit-codes", "--format", "json", WORKFLOW_DIR],
        workspace,
    )
    if outcome.returncode != 0:
        raise RuntimeError(f"zizmor failed in {workspace}: {outcome.stderr.strip()[-ERROR_TAIL_CHARS:]}")
    findings: list[Any] = json.loads(outcome.stdout or "[]")
    return len(findings)


def score(workspace: Path) -> Metrics:
    paths: list[Path] = workflow_files(workspace)
    if not paths:
        return dict(EMPTY_METRICS)
    workflows: list[dict[str, Any]] = [load_workflow(path) for path in paths]
    return {
        "hidden_test_passes": actionlint_passes(workspace, paths) and requirements_hold(workflows),
        "actions_pinned_by_sha": actions_pinned_by_sha(workflows),
        "top_level_permissions": all("permissions" in workflow for workflow in workflows),
        "zizmor_findings": count_zizmor_findings(workspace),
    }
