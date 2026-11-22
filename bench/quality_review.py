"""Code quality of one first answer per reference, as a blind reviewer sees it.

Usage:
  BENCH_TASKS_DIR=bench/quality bench/run.sh <out-dir> 1 none= chef13=<dir> chef14=<dir> chef15=<dir>
  python bench/quality_review.py run <out-dir> <review-dir> <arm> ...
  python bench/quality_review.py summarize <review-dir> > bench/results/quality.json

The tasks in bench/quality/<reference>/prompt.md exercise the most-used references, one task each.
Each first answer is copied blind and reviewed once by the merge loop's panel seat, without fix rounds:
quality and correctness from 0 to 10, and mergeable when the review lists no blocker or major change.
"""

import json
import statistics
import sys
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from blind_review import BENCH_DIR, PARALLEL_JUDGES, anonymize, read_review, reviewer_id, run_judge
from merge_loop import SEAT, is_mergeable

QUALITY_DIR: Path = BENCH_DIR / "quality"
# Hashed into the reviewer id: these verdicts come from a single review, with no fix round after it.
QUALITY_RULE: str = "quality of the first answer, one review, mergeable when no blocker/major change is listed"


def review_all(key: dict[str, dict[str, str]], review_dir: Path) -> None:
    with ThreadPoolExecutor(max_workers=PARALLEL_JUDGES) as pool:
        futures: dict[Future[None], str] = {
            pool.submit(
                run_judge, Path(origin["submission"]), origin["task"], SEAT, review_dir / f"{sample_id}.json", QUALITY_DIR
            ): sample_id
            for sample_id, origin in sorted(key.items())
        }
        for future in as_completed(futures):
            error: BaseException | None = future.exception()
            if error is not None:
                print(f"quality_review: judge {futures[future]} failed: {error}", file=sys.stderr)


def verdict(review: dict[str, Any]) -> dict[str, float]:
    return {
        "quality": float(review["quality"]),
        "correctness": float(review["correctness"]),
        "mergeable": float(is_mergeable(review)),
    }


def mean_verdicts(verdicts: list[dict[str, float]]) -> dict[str, float]:
    means: dict[str, float] = {name: round(statistics.fmean(item[name] for item in verdicts), 2) for name in verdicts[0]}
    return {**means, "reviews": float(len(verdicts))}


def summarize(review_dir: Path) -> dict[str, Any]:
    """Mean verdict per arm over every reference, and the quality score per reference and arm."""
    key: dict[str, dict[str, str]] = json.loads((review_dir / "key.json").read_text(encoding="utf-8"))
    by_arm: dict[str, list[dict[str, float]]] = {}
    tasks: dict[str, dict[str, float]] = {}
    for sample_id, origin in sorted(key.items()):
        review: dict[str, Any] | None = read_review(review_dir / f"{sample_id}.json")
        if review is None:
            continue
        scores: dict[str, float] = verdict(review)
        by_arm.setdefault(origin["arm"], []).append(scores)
        tasks.setdefault(origin["task"], {})[origin["arm"]] = scores["quality"]
    return {
        "reviewer": reviewer_id(SEAT, QUALITY_RULE),
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
