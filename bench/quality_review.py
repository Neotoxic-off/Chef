"""Code quality of one first answer per reference, as a blind reviewer sees it.

Usage:
  BENCH_TASKS_DIR=bench/quality bench/run.sh <out-dir> 1 none= chef13=<dir> chef14=<dir> chef15=<dir>
  python bench/quality_review.py run <out-dir> <review-dir> <arm> ...
  python bench/quality_review.py summarize <review-dir> > bench/results/quality.json

The tasks in bench/quality/<reference>/prompt.md exercise the most-used references, one task each.
Each first answer is copied blind and reviewed once by the merge loop's panel seat, without fix rounds,
with judge_quality.md: quality, clarity, maintainability and functionality from 0 to 10, and
mergeable when the review lists no blocker or major change.
"""

import hashlib
import json
import statistics
import subprocess
import sys
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from blind_review import (
    BENCH_DIR,
    JUDGE_BUDGET_USD,
    JUDGE_MODEL,
    JUDGE_TOOLS,
    PARALLEL_JUDGES,
    SEVERITIES,
    anonymize,
    read_review,
)
from merge_loop import SEAT, is_mergeable

QUALITY_DIR: Path = BENCH_DIR / "quality"
JUDGE_TEMPLATE: Path = BENCH_DIR / "judge_quality.md"
CRITERIA: tuple[str, ...] = ("quality", "clarity", "maintainability", "functionality")
REVIEWER_ID_LENGTH: int = 12
QUALITY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        **{criterion: {"type": "integer", "minimum": 0, "maximum": 10} for criterion in CRITERIA},
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"severity": {"enum": list(SEVERITIES)}, "change": {"type": "string"}},
                "required": ["severity", "change"],
            },
        },
    },
    "required": [*CRITERIA, "changes"],
}


def judge_prompt(task: str) -> str:
    template: str = JUDGE_TEMPLATE.read_text(encoding="utf-8")
    task_text: str = (QUALITY_DIR / task / "prompt.md").read_text(encoding="utf-8").strip()
    return template.replace("{role}", SEAT).replace("{task}", task_text)


def reviewer_id() -> str:
    """Hash of what decides a verdict, so results from different judges are never mixed."""
    template: str = JUDGE_TEMPLATE.read_text(encoding="utf-8").replace("\r\n", "\n")
    parts: list[str] = [template, SEAT, json.dumps(QUALITY_SCHEMA, sort_keys=True), JUDGE_MODEL, JUDGE_BUDGET_USD, JUDGE_TOOLS]
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:REVIEWER_ID_LENGTH]


def run_judge(submission: Path, task: str, review_path: Path) -> None:
    command: list[str] = [
        "claude", "-p", judge_prompt(task),
        "--model", JUDGE_MODEL,
        "--output-format", "json",
        "--json-schema", json.dumps(QUALITY_SCHEMA),
        "--restricted",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--tools", JUDGE_TOOLS,
        "--max-budget-usd", JUDGE_BUDGET_USD,
    ]  # fmt: skip
    with review_path.open("w", encoding="utf-8") as review_file:
        subprocess.run(command, cwd=submission, stdin=subprocess.DEVNULL, stdout=review_file, check=True)


def review_all(key: dict[str, dict[str, str]], review_dir: Path) -> None:
    with ThreadPoolExecutor(max_workers=PARALLEL_JUDGES) as pool:
        futures: dict[Future[None], str] = {
            pool.submit(run_judge, Path(origin["submission"]), origin["task"], review_dir / f"{sample_id}.json"): sample_id
            for sample_id, origin in sorted(key.items())
        }
        for future in as_completed(futures):
            error: BaseException | None = future.exception()
            if error is not None:
                print(f"quality_review: judge {futures[future]} failed: {error}", file=sys.stderr)


def verdict(review: dict[str, Any]) -> dict[str, float]:
    scores: dict[str, float] = {criterion: float(review[criterion]) for criterion in CRITERIA}
    return {**scores, "mergeable": float(is_mergeable(review))}


def mean_verdicts(verdicts: list[dict[str, float]]) -> dict[str, float]:
    means: dict[str, float] = {name: round(statistics.fmean(item[name] for item in verdicts), 2) for name in verdicts[0]}
    return {**means, "reviews": float(len(verdicts))}


def summarize(review_dir: Path) -> dict[str, Any]:
    """Mean verdict per arm over every reference, and the mean of the four scores per reference and arm."""
    key: dict[str, dict[str, str]] = json.loads((review_dir / "key.json").read_text(encoding="utf-8"))
    by_arm: dict[str, list[dict[str, float]]] = {}
    tasks: dict[str, dict[str, float]] = {}
    for sample_id, origin in sorted(key.items()):
        review: dict[str, Any] | None = read_review(review_dir / f"{sample_id}.json")
        if review is None:
            continue
        scores: dict[str, float] = verdict(review)
        by_arm.setdefault(origin["arm"], []).append(scores)
        tasks.setdefault(origin["task"], {})[origin["arm"]] = round(statistics.fmean(scores[name] for name in CRITERIA), 2)
    return {
        "reviewer": reviewer_id(),
        "criteria": list(CRITERIA),
        "arms": {arm: mean_verdicts(verdicts) for arm, verdicts in sorted(by_arm.items())},
        "tasks": dict(sorted(tasks.items())),
    }


def main(arguments: list[str]) -> None:
    if arguments[0] == "summarize":
        print(json.dumps(summarize(Path(arguments[1])), indent=2))
        return
    out_dir: Path = Path(arguments[1])
    review_dir: Path = Path(arguments[2])
    if review_dir.exists():
        raise SystemExit(f"quality_review: {review_dir} exists, use a new review dir")
    review_dir.mkdir(parents=True)
    key: dict[str, dict[str, str]] = anonymize(out_dir, arguments[3:])
    (review_dir / "key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    review_all(key, review_dir)


if __name__ == "__main__":
    main(sys.argv[1:])
