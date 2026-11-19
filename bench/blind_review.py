"""Blind review of benchmark outputs by independent judges.

Usage: python bench/blind_review.py <out-dir> <review-dir> <arm> [<arm> ...]

Each workspace is copied under a random id into its own temp folder, without git history, caches
or scoring files, so a judge cannot tell which arm produced it. A panel of seats (ROLES) reviews
each sample; every sample and seat gets its own fresh `claude -p --restricted` session: no plugin,
no settings, read-only tools confined to that folder. No judge sees another sample, another review
or the id-to-arm key kept in the review dir. `blind_review.py summarize <review-dir>` aggregates.
"""

import json
import secrets
import shutil
import statistics
import subprocess
import sys
import tempfile
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

BENCH_DIR: Path = Path(__file__).resolve().parent
JUDGE_MODEL: str = "claude-opus-5-5"
JUDGE_BUDGET_USD: str = "2"
EXCLUDED: tuple[str, ...] = (
    ".git",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".coverage",
    ".bench-coverage.json",
    "htmlcov",
    "uv.lock",
    # Files that name the tool or carry its rules would tell the judge which arm wrote the code.
    ".chef.md",
    "CLAUDE.md",
    "AGENTS.md",
    "TRANSFORM.md",
)
PARALLEL_JUDGES: int = 4
ROLES: dict[str, str] = {
    "senior": "senior engineer on the team, reviewing design and correctness.",
    "security": "security reviewer, looking for anything an attacker or a mistake could exploit.",
    "operations": "SRE who will deploy and run this in production and get paged when it breaks.",
    "maintainer": "engineer who will own and change this code for the next two years.",
}
SEVERITIES: tuple[str, ...] = ("blocker", "major", "minor")
REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "correctness": {"type": "integer", "minimum": 0, "maximum": 10},
        "quality": {"type": "integer", "minimum": 0, "maximum": 10},
        "merge_as_is": {"type": "boolean"},
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"severity": {"enum": list(SEVERITIES)}, "change": {"type": "string"}},
                "required": ["severity", "change"],
            },
        },
    },
    "required": ["correctness", "quality", "merge_as_is", "changes"],
}


def anonymize(out_dir: Path, arms: list[str]) -> dict[str, dict[str, str]]:
    key: dict[str, dict[str, str]] = {}
    for arm in arms:
        for workspace in sorted(out_dir.glob(f"{arm}/*/*/workspace")):
            submission: Path = Path(tempfile.mkdtemp(prefix="review-")) / "submission"
            shutil.copytree(workspace, submission, ignore=shutil.ignore_patterns(*EXCLUDED))
            key[secrets.token_hex(4)] = {
                "arm": arm,
                "task": workspace.parents[1].name,
                "run": workspace.parent.name,
                "submission": str(submission),
            }
    return key


def judge_prompt(task: str, role: str) -> str:
    template: str = (BENCH_DIR / "judge.md").read_text(encoding="utf-8")
    task_text: str = (BENCH_DIR / "tasks" / task / "prompt.md").read_text(encoding="utf-8").strip()
    return template.replace("{role}", ROLES[role]).replace("{task}", task_text)


def run_judge(submission: Path, task: str, role: str, review_path: Path) -> None:
    command: list[str] = [
        "claude", "-p", judge_prompt(task, role),
        "--model", JUDGE_MODEL,
        "--output-format", "json",
        "--json-schema", json.dumps(REVIEW_SCHEMA),
        "--restricted",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--tools", "Read,Glob,Grep",
        "--max-budget-usd", JUDGE_BUDGET_USD,
    ]  # fmt: skip
    with review_path.open("w", encoding="utf-8") as review_file:
        subprocess.run(command, cwd=submission, stdin=subprocess.DEVNULL, stdout=review_file, check=True)


def read_review(review_path: Path) -> dict[str, Any] | None:
    if not review_path.is_file():
        print(f"blind_review: {review_path} is missing, skipped", file=sys.stderr)
        return None
    try:
        result: Any = json.loads(review_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"blind_review: {review_path} is not JSON (judge crashed?), skipped", file=sys.stderr)
        return None
    structured: Any = result.get("structured_output") if isinstance(result, dict) else None
    if isinstance(structured, dict):
        return structured
    print(f"blind_review: {review_path} has no structured review, skipped", file=sys.stderr)
    return None


def review_metrics(review: dict[str, Any]) -> dict[str, float]:
    changes: list[dict[str, str]] = review["changes"]
    counts: dict[str, float] = {severity: sum(1 for item in changes if item["severity"] == severity) for severity in SEVERITIES}
    return {
        "correctness": review["correctness"],
        "quality": review["quality"],
        "merge_as_is": float(review["merge_as_is"]),
        **counts,
    }


def mean_metrics(reviews: list[dict[str, float]]) -> dict[str, float]:
    means: dict[str, float] = {name: round(statistics.fmean(review[name] for review in reviews), 2) for name in reviews[0]}
    return {**means, "reviews": float(len(reviews))}


def summarize(review_dir: Path) -> dict[str, dict[str, dict[str, float]]]:
    """Mean per arm and task over every sample and seat, plus per arm and seat."""
    key: dict[str, dict[str, str]] = json.loads((review_dir / "key.json").read_text(encoding="utf-8"))
    grouped: dict[tuple[str, str], list[dict[str, float]]] = {}
    for sample_id, origin in key.items():
        for role in ROLES:
            review: dict[str, Any] | None = read_review(review_dir / f"{sample_id}-{role}.json")
            if review is None:
                continue
            metrics: dict[str, float] = review_metrics(review)
            grouped.setdefault((origin["arm"], origin["task"]), []).append(metrics)
            grouped.setdefault((origin["arm"], f"seat:{role}"), []).append(metrics)
    summary: dict[str, dict[str, dict[str, float]]] = {}
    for (arm, group), reviews in sorted(grouped.items()):
        summary.setdefault(arm, {})[group] = mean_metrics(reviews)
    return summary


def judge_all(key: dict[str, dict[str, str]], review_dir: Path) -> None:
    jobs: list[tuple[str, str]] = [(sample_id, role) for sample_id in sorted(key) for role in ROLES]
    with ThreadPoolExecutor(max_workers=PARALLEL_JUDGES) as pool:
        futures: dict[Future[None], str] = {
            pool.submit(
                run_judge,
                Path(key[sample_id]["submission"]),
                key[sample_id]["task"],
                role,
                review_dir / f"{sample_id}-{role}.json",
            ): f"{sample_id}-{role}"
            for sample_id, role in jobs
        }
        for future in as_completed(futures):
            error: BaseException | None = future.exception()
            if error is not None:
                print(f"blind_review: judge {futures[future]} failed: {error}", file=sys.stderr)


def main(arguments: list[str]) -> None:
    if arguments[0] == "summarize":
        print(json.dumps(summarize(Path(arguments[1])), indent=2))
        return
    out_dir: Path = Path(arguments[0])
    review_dir: Path = Path(arguments[1])
    if review_dir.exists():
        raise SystemExit(f"blind_review: {review_dir} exists, use a new review dir")
    review_dir.mkdir(parents=True)
    key: dict[str, dict[str, str]] = anonymize(out_dir, arguments[2:])
    (review_dir / "key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    judge_all(key, review_dir)


if __name__ == "__main__":
    main(sys.argv[1:])
