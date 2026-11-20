"""Score the terraform task: a reusable S3 log bucket module at the workspace root.

The module is planned through a wrapper root module with fake credentials, so no AWS account is needed;
the AWS provider is downloaded once into the Docker volume PLUGIN_CACHE_VOLUME.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import scorer_lib
from score import Metrics, docker_mount

TERRAFORM_IMAGE: str = "hashicorp/terraform:1.17.1"
TFLINT_IMAGE: str = "ghcr.io/terraform-linters/tflint:v0.53.0"
PLUGIN_CACHE_VOLUME: str = "bench-terraform-plugins"
DOCKER_FAILURE_CODES: frozenset[int] = frozenset({125, 126, 127})
TFLINT_OK_CODES: frozenset[int] = frozenset({0, 1})
ERROR_TAIL_CHARS: int = 500

BUCKET_NAME: str = "bench-app-logs"
TAGS: dict[str, str] = {"team": "bench"}
RETENTION_DAYS: int = 90
TRANSITION_DAYS: int = 30
TRANSITION_STORAGE_CLASS: str = "STANDARD_IA"
NONCURRENT_DAYS: int = 30

ROOT_CONFIG: str = f"""
provider "aws" {{
  region                      = "us-east-1"
  access_key                  = "bench"
  secret_key                  = "bench"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
}}

module "logs" {{
  source             = "../module"
  bucket_name        = "{BUCKET_NAME}"
  log_retention_days = {RETENTION_DAYS}
  tags               = {{ team = "{TAGS["team"]}" }}
}}

output "bucket_id" {{
  value = module.logs.bucket_id
}}

output "bucket_arn" {{
  value = module.logs.bucket_arn
}}
"""
TFLINT_CONFIG: str = """
plugin "terraform" {
  enabled = true
  preset  = "recommended"
}
"""
INIT: str = "terraform init -backend=false -input=false"
VALIDATE_SCRIPT: str = f"{INIT} && terraform validate"
PROVIDERS_SCRIPT: str = f"{INIT} >&2 && terraform providers"
PLAN_SCRIPT: str = f"{INIT} >&2 && terraform plan -input=false -out=/tmp/plan >&2 && terraform show -json /tmp/plan"
TFLINT_CONFIG_PATH: str = "/work/bench-tflint.hcl"
MODULE_DIR: str = "/work/module"
ROOT_DIR: str = "/work/root"
EMPTY_METRICS: Metrics = {"hidden_test_passes": False, "tflint_findings": 0, "providers_pinned": False}


def docker_run(arguments: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    outcome: subprocess.CompletedProcess[str] = scorer_lib.docker_run(arguments, cwd)
    if outcome.returncode in DOCKER_FAILURE_CODES:
        raise RuntimeError(f"docker run {arguments[-3:]} failed: {outcome.stderr.strip()[-ERROR_TAIL_CHARS:]}")
    return outcome


def terraform(scratch: Path, workdir: str, script: str) -> subprocess.CompletedProcess[str]:
    return docker_run(
        [
            *docker_mount(scratch),
            "-v",
            f"{PLUGIN_CACHE_VOLUME}:/plugins",
            "-e",
            "TF_PLUGIN_CACHE_DIR=/plugins",
            "-e",
            "TF_DATA_DIR=/tmp/terraform",
            "-e",
            "TF_CLI_ARGS=-no-color",
            "-w",
            workdir,
            "--entrypoint",
            "sh",
            TERRAFORM_IMAGE,
            "-c",
            script,
        ],
        scratch,
    )


def report_failure(step: str, outcome: subprocess.CompletedProcess[str]) -> None:
    print(f"score: terraform {step} failed: {outcome.stderr.strip()[-ERROR_TAIL_CHARS:]}", file=sys.stderr)


def prepare(workspace: Path, scratch: Path) -> None:
    shutil.copytree(workspace, scratch / "module", ignore=shutil.ignore_patterns(".git", ".terraform"))
    (scratch / "root").mkdir()
    (scratch / "root" / "main.tf").write_text(ROOT_CONFIG, encoding="utf-8")
    (scratch / "bench-tflint.hcl").write_text(TFLINT_CONFIG, encoding="utf-8")


def module_validates(scratch: Path) -> bool:
    outcome: subprocess.CompletedProcess[str] = terraform(scratch, MODULE_DIR, VALIDATE_SCRIPT)
    if outcome.returncode != 0:
        report_failure("validate", outcome)
    return outcome.returncode == 0


def planned_resources(scratch: Path) -> list[dict[str, Any]]:
    outcome: subprocess.CompletedProcess[str] = terraform(scratch, ROOT_DIR, PLAN_SCRIPT)
    if outcome.returncode != 0:
        report_failure("plan", outcome)
        return []
    plan: dict[str, Any] = json.loads(outcome.stdout)
    changes: list[dict[str, Any]] = plan.get("resource_changes", [])
    return changes


def planned_values(resources: list[dict[str, Any]], resource_type: str) -> list[dict[str, Any]]:
    return [resource["change"]["after"] or {} for resource in resources if resource["type"] == resource_type]


def bucket_is_named_and_tagged(resources: list[dict[str, Any]]) -> bool:
    return any(
        bucket.get("bucket") == BUCKET_NAME and TAGS.items() <= (bucket.get("tags") or {}).items()
        for bucket in planned_values(resources, "aws_s3_bucket")
    )


def versioning_is_enabled(resources: list[dict[str, Any]]) -> bool:
    return any(
        configuration.get("status") == "Enabled"
        for versioning in planned_values(resources, "aws_s3_bucket_versioning")
        for configuration in versioning.get("versioning_configuration") or []
    )


def enabled_lifecycle_rules(resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        rule
        for lifecycle in planned_values(resources, "aws_s3_bucket_lifecycle_configuration")
        for rule in lifecycle.get("rule") or []
        if rule.get("status") == "Enabled"
    ]


def lifecycle_blocks(rules: list[dict[str, Any]], block: str) -> list[dict[str, Any]]:
    return [entry for rule in rules for entry in rule.get(block) or []]


def lifecycle_is_complete(resources: list[dict[str, Any]]) -> bool:
    rules: list[dict[str, Any]] = enabled_lifecycle_rules(resources)
    transitions: bool = any(
        transition.get("days") == TRANSITION_DAYS and transition.get("storage_class") == TRANSITION_STORAGE_CLASS
        for transition in lifecycle_blocks(rules, "transition")
    )
    expires: bool = any(expiration.get("days") == RETENTION_DAYS for expiration in lifecycle_blocks(rules, "expiration"))
    noncurrent_expires: bool = any(
        expiration.get("noncurrent_days") == NONCURRENT_DAYS
        for expiration in lifecycle_blocks(rules, "noncurrent_version_expiration")
    )
    return transitions and expires and noncurrent_expires


def requirements_hold(resources: list[dict[str, Any]]) -> bool:
    """Outputs are checked by the plan itself: the wrapper root module references both."""
    return bucket_is_named_and_tagged(resources) and versioning_is_enabled(resources) and lifecycle_is_complete(resources)


def count_tflint_findings(scratch: Path) -> int:
    outcome: subprocess.CompletedProcess[str] = docker_run(
        [*docker_mount(scratch), "-w", MODULE_DIR, TFLINT_IMAGE, f"--config={TFLINT_CONFIG_PATH}", "--force", "--format=json"],
        scratch,
    )
    if outcome.returncode not in TFLINT_OK_CODES or not outcome.stdout.strip():
        raise RuntimeError(f"tflint failed: {outcome.stderr.strip()[-ERROR_TAIL_CHARS:]}")
    report: dict[str, list[Any]] = json.loads(outcome.stdout)
    return len(report["issues"]) + len(report["errors"])


def has_upper_bound(constraint: str) -> bool:
    """`~> 5.0`, `< 6.0` or an exact version pin the provider; a bare `>= 5.0` does not."""
    parts: list[str] = [part.strip() for part in constraint.split(",")]
    return any(part.startswith(("~>", "<", "=")) or part[:1].isdigit() for part in parts)


def providers_pinned(scratch: Path) -> bool:
    outcome: subprocess.CompletedProcess[str] = terraform(scratch, MODULE_DIR, PROVIDERS_SCRIPT)
    if outcome.returncode != 0:
        report_failure("providers", outcome)
        return False
    constraints: list[str] = [line.split("]", 1)[1] for line in outcome.stdout.splitlines() if "provider[" in line]
    return bool(constraints) and all(map(has_upper_bound, constraints))


def score(workspace: Path) -> Metrics:
    if not any(workspace.glob("*.tf")):
        return dict(EMPTY_METRICS)
    with tempfile.TemporaryDirectory() as scratch_name:
        scratch: Path = Path(scratch_name)
        prepare(workspace, scratch)
        return {
            "hidden_test_passes": module_validates(scratch) and requirements_hold(planned_resources(scratch)),
            "tflint_findings": count_tflint_findings(scratch),
            "providers_pinned": providers_pinned(scratch),
        }
