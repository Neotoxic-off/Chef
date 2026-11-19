"""Score the helm task: a chart in chart/ that deploys the stdlib HTTP service."""

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from score import Metrics, docker_mount, run

HELM_IMAGE: str = "alpine/helm:3.16.2"
KUBECONFORM_IMAGE: str = "ghcr.io/yannh/kubeconform:v0.6.7"
KUBERNETES_VERSION: str = "1.31.0"
SCHEMA_CACHE_VOLUME: str = "bench-kubeconform-schemas"
DOCKER_FAILURE_CODES: frozenset[int] = frozenset({125, 126, 127})
ERROR_TAIL_CHARS: int = 500

CHART_DIR: str = "/work/chart"
IMAGE_REPOSITORY: str = "bench/app"
IMAGE_TAG: str = "1.2.3"
REPLICAS: int = 3
CONTAINER_PORT: int = 8000
SERVICE_PORT: int = 80
TEST_VALUES: tuple[str, ...] = (
    f"image.repository={IMAGE_REPOSITORY}",
    f"image.tag={IMAGE_TAG}",
    f"replicaCount={REPLICAS}",
)
EMPTY_METRICS: Metrics = {
    "hidden_test_passes": False,
    "run_as_non_root": False,
    "resource_limits": False,
    "probes": False,
}


def docker_run(arguments: list[str], cwd: Path, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    outcome: subprocess.CompletedProcess[str] = run(["docker", "run", "--rm", "-i", *arguments], cwd, stdin)
    if outcome.returncode in DOCKER_FAILURE_CODES:
        raise RuntimeError(f"docker run {arguments[-3:]} failed: {outcome.stderr.strip()[-ERROR_TAIL_CHARS:]}")
    return outcome


def helm(workspace: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return docker_run([*docker_mount(workspace), HELM_IMAGE, *arguments], workspace)


def render(workspace: Path) -> str | None:
    set_flags: list[str] = [flag for value in TEST_VALUES for flag in ("--set", value)]
    outcome: subprocess.CompletedProcess[str] = helm(workspace, "template", "bench", CHART_DIR, *set_flags)
    return outcome.stdout if outcome.returncode == 0 else None


def manifests_conform(workspace: Path, rendered: str) -> bool:
    outcome: subprocess.CompletedProcess[str] = docker_run(
        [
            "-v",
            f"{SCHEMA_CACHE_VOLUME}:/cache",
            KUBECONFORM_IMAGE,
            "-strict",
            "-summary",
            "-cache",
            "/cache",
            "-kubernetes-version",
            KUBERNETES_VERSION,
            "-",
        ],
        workspace,
        rendered,
    )
    return outcome.returncode == 0


def manifests(rendered: str) -> list[dict[str, Any]] | None:
    try:
        loaded: list[Any] = list(yaml.safe_load_all(rendered))
    except yaml.YAMLError as error:
        print(f"score: helm rendered invalid YAML: {error}", file=sys.stderr)
        return None
    return [document for document in loaded if isinstance(document, dict)]


def of_kind(documents: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [document for document in documents if document.get("kind") == kind]


def pod_spec(deployment: dict[str, Any]) -> dict[str, Any]:
    spec: dict[str, Any] = deployment.get("spec", {}).get("template", {}).get("spec", {})
    return spec


def containers(deployment: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = pod_spec(deployment).get("containers") or []
    return found


def serves_image(deployment: dict[str, Any]) -> bool:
    return deployment.get("spec", {}).get("replicas") == REPLICAS and any(
        container.get("image") == f"{IMAGE_REPOSITORY}:{IMAGE_TAG}"
        and any(port.get("containerPort") == CONTAINER_PORT for port in container.get("ports") or [])
        for container in containers(deployment)
    )


def container_port_targets(deployment: dict[str, Any]) -> set[int | str]:
    """targetPort may name the container port instead of repeating its number."""
    names: set[int | str] = {
        port["name"]
        for container in containers(deployment)
        for port in container.get("ports") or []
        if port.get("containerPort") == CONTAINER_PORT and "name" in port
    }
    return names | {CONTAINER_PORT}


def service_routes_to(service: dict[str, Any], deployment: dict[str, Any]) -> bool:
    spec: dict[str, Any] = service.get("spec", {})
    selector: dict[str, str] = spec.get("selector") or {}
    pod_labels: dict[str, str] = deployment.get("spec", {}).get("template", {}).get("metadata", {}).get("labels") or {}
    targets: set[int | str] = container_port_targets(deployment)
    return (
        spec.get("type", "ClusterIP") == "ClusterIP"
        and bool(selector)
        and selector.items() <= pod_labels.items()
        and any(
            port.get("port") == SERVICE_PORT and port.get("targetPort", SERVICE_PORT) in targets
            for port in spec.get("ports") or []
        )
    )


def requirements_hold(documents: list[dict[str, Any]]) -> bool:
    deployments: list[dict[str, Any]] = [
        deployment for deployment in of_kind(documents, "Deployment") if serves_image(deployment)
    ]
    services: list[dict[str, Any]] = of_kind(documents, "Service")
    return any(service_routes_to(service, deployment) for service in services for deployment in deployments)


def runs_as_non_root(deployment: dict[str, Any]) -> bool:
    pod_level: bool = (pod_spec(deployment).get("securityContext") or {}).get("runAsNonRoot") is True
    return pod_level or all(
        (container.get("securityContext") or {}).get("runAsNonRoot") is True for container in containers(deployment)
    )


def has_limits(deployment: dict[str, Any]) -> bool:
    return all(bool((container.get("resources") or {}).get("limits")) for container in containers(deployment))


def has_probes(deployment: dict[str, Any]) -> bool:
    return all("livenessProbe" in container and "readinessProbe" in container for container in containers(deployment))


def every_deployment(deployments: list[dict[str, Any]], check: Callable[[dict[str, Any]], bool]) -> bool:
    return bool(deployments) and all(check(deployment) for deployment in deployments)


def score(workspace: Path) -> Metrics:
    if not (workspace / "chart" / "Chart.yaml").is_file():
        return dict(EMPTY_METRICS)
    lint_passes: bool = helm(workspace, "lint", CHART_DIR).returncode == 0
    rendered: str | None = render(workspace)
    if rendered is None:
        return dict(EMPTY_METRICS)
    documents: list[dict[str, Any]] | None = manifests(rendered)
    if documents is None:
        return dict(EMPTY_METRICS)
    deployments: list[dict[str, Any]] = of_kind(documents, "Deployment")
    return {
        "hidden_test_passes": lint_passes and manifests_conform(workspace, rendered) and requirements_hold(documents),
        "run_as_non_root": every_deployment(deployments, runs_as_non_root),
        "resource_limits": every_deployment(deployments, has_limits),
        "probes": every_deployment(deployments, has_probes),
    }
