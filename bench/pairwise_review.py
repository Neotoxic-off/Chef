"""Blind pairwise review: which of two arms' submissions would a reviewer merge.

Usage:
  python bench/pairwise_review.py judge <out-dir> <review-dir> <arm-a> <arm-b>
  python bench/pairwise_review.py summarize <review-dir>

For every task and run present in both arms, the two workspaces are copied side by side into a
fresh temp folder as `first/` and `second/`, without history, caches or files that name the tool.
Each pair is judged twice, once in each order, by separate `claude -p --restricted` sessions with
read-only tools confined to that folder. A verdict counts only when both orders agree; otherwise
it is a tie. The key telling which folder held which arm stays in the review dir.
"""

import json
import random
import subprocess
import sys
import tempfile
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from math import comb
from pathlib import Path
from typing import Any

from blind_review import BENCH_DIR, JUDGE_BUDGET_USD, JUDGE_MODEL, PARALLEL_JUDGES, copy_submission

ORDERS: tuple[str, str] = ("ab", "ba")
WINNERS: tuple[str, ...] = ("first", "second", "tie")
BOOTSTRAP_SAMPLES: int = 10000
BOOTSTRAP_SEED: int = 7
TALLY_KEYS: tuple[str, ...] = ("b", "a", "tie", "merge_a", "merge_b", "major_a", "major_b", "verdicts")
OUTCOME_SCORES: dict[str, float] = {"b": 1.0, "a": 0.0, "tie": 0.5}
PAIR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "winner": {"enum": list(WINNERS)},
        "first_merge_as_is": {"type": "boolean"},
        "second_merge_as_is": {"type": "boolean"},
        "first_major_changes": {"type": "integer", "minimum": 0},
        "second_major_changes": {"type": "integer", "minimum": 0},
        "reason": {"type": "string"},
    },
    "required": ["winner", "first_merge_as_is", "second_merge_as_is", "first_major_changes", "second_major_changes", "reason"],
}


@dataclass(frozen=True)
class Pair:
    task: str
    run: str
    workspace_a: Path
    workspace_b: Path


def find_pairs(out_dir: Path, arm_a: str, arm_b: str) -> list[Pair]:
    pairs: list[Pair] = []
    for workspace_a in sorted(out_dir.glob(f"{arm_a}/*/*/workspace")):
        task: str = workspace_a.parents[1].name
        run: str = workspace_a.parent.name
        workspace_b: Path = out_dir / arm_b / task / run / "workspace"
        if workspace_b.is_dir():
            pairs.append(Pair(task, run, workspace_a, workspace_b))
    return pairs


def stage(first: Path, second: Path) -> Path:
    folder: Path = Path(tempfile.mkdtemp(prefix="pair-"))
    for name, source in (("first", first), ("second", second)):
        copy_submission(source, folder / name)
    return folder


def judge_prompt(task: str) -> str:
    template: str = (BENCH_DIR / "judge_pairwise.md").read_text(encoding="utf-8")
    return template.replace("{task}", (BENCH_DIR / "tasks" / task / "prompt.md").read_text(encoding="utf-8").strip())


def run_judge(folder: Path, task: str, verdict_path: Path) -> None:
    command: list[str] = [
        "claude", "-p", judge_prompt(task),
        "--model", JUDGE_MODEL,
        "--output-format", "json",
        "--json-schema", json.dumps(PAIR_SCHEMA),
        "--restricted",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--tools", "Read,Glob,Grep",
        "--max-budget-usd", JUDGE_BUDGET_USD,
    ]  # fmt: skip
    with verdict_path.open("w", encoding="utf-8") as verdict_file:
        subprocess.run(command, cwd=folder, stdin=subprocess.DEVNULL, stdout=verdict_file, check=True)


def judge(out_dir: Path, review_dir: Path, arm_a: str, arm_b: str) -> None:
    if review_dir.exists():
        raise SystemExit(f"pairwise_review: {review_dir} exists, use a new review dir")
    review_dir.mkdir(parents=True)
    key: dict[str, dict[str, str]] = {}
    jobs: list[tuple[Path, str, Path]] = []
    pairs: list[Pair] = find_pairs(out_dir, arm_a, arm_b)
    if not pairs:
        raise SystemExit(f"pairwise_review: no run present in both {arm_a} and {arm_b} under {out_dir}")
    for index, pair in enumerate(pairs):
        for order in ORDERS:
            first, second = (pair.workspace_a, pair.workspace_b) if order == "ab" else (pair.workspace_b, pair.workspace_a)
            pair_id: str = f"{index:03d}-{order}"
            key[pair_id] = {
                "task": pair.task,
                "run": pair.run,
                "first": arm_a if order == "ab" else arm_b,
                "arm_a": arm_a,
                "arm_b": arm_b,
            }
            jobs.append((stage(first, second), pair.task, review_dir / f"{pair_id}.json"))
    (review_dir / "key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    with ThreadPoolExecutor(max_workers=PARALLEL_JUDGES) as pool:
        futures: dict[Future[None], str] = {pool.submit(run_judge, *job): job[2].name for job in jobs}
        for future in as_completed(futures):
            error: BaseException | None = future.exception()
            if error is not None:
                print(f"pairwise_review: judge {futures[future]} failed: {error}", file=sys.stderr)


def read_verdict(verdict_path: Path) -> dict[str, Any] | None:
    if not verdict_path.is_file():
        print(f"pairwise_review: {verdict_path} is missing, skipped", file=sys.stderr)
        return None
    try:
        result: Any = json.loads(verdict_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"pairwise_review: {verdict_path} is not JSON (judge crashed?), skipped", file=sys.stderr)
        return None
    structured: Any = result.get("structured_output") if isinstance(result, dict) else None
    if isinstance(structured, dict):
        return structured
    print(f"pairwise_review: {verdict_path} has no structured verdict, skipped", file=sys.stderr)
    return None


def winning_arm(verdict: dict[str, Any], first_arm: str, other_arm: str) -> str:
    return {"first": first_arm, "second": other_arm}.get(verdict["winner"], "tie")


def side_metrics(verdict: dict[str, Any], first_arm: str, arm: str) -> tuple[float, float]:
    side: str = "first" if first_arm == arm else "second"
    return float(verdict[f"{side}_merge_as_is"]), float(verdict[f"{side}_major_changes"])


def consistent_outcome(verdicts: list[tuple[dict[str, Any], str]], arm_a: str, arm_b: str) -> str:
    """'b', 'a' or 'tie' for one pair; a win needs both orders to agree."""
    winners: set[str] = {winning_arm(verdict, first, arm_b if first == arm_a else arm_a) for verdict, first in verdicts}
    if len(verdicts) != len(ORDERS) or len(winners) != 1:
        return "tie"
    winner: str = winners.pop()
    return {arm_b: "b", arm_a: "a"}.get(winner, "tie")


def sign_test_p(wins: int, losses: int) -> float:
    """Two-sided exact binomial test of wins against losses, ties dropped."""
    trials: int = wins + losses
    if trials == 0:
        return 1.0
    extreme: int = min(wins, losses)
    tail: float = sum(comb(trials, k) for k in range(extreme + 1)) / 2**trials
    return min(1.0, 2 * tail)


def bootstrap_ci(scores_by_task: dict[str, list[float]], statistic: Callable[[list[float]], float]) -> tuple[float, float]:
    """95% interval resampling whole tasks, so runs of one task stay together."""
    generator: random.Random = random.Random(BOOTSTRAP_SEED)
    tasks: list[str] = sorted(scores_by_task)
    estimates: list[float] = []
    for _ in range(BOOTSTRAP_SAMPLES):
        sample: list[float] = [score for task in generator.choices(tasks, k=len(tasks)) for score in scores_by_task[task]]
        estimates.append(statistic(sample))
    estimates.sort()
    return estimates[int(0.025 * BOOTSTRAP_SAMPLES)], estimates[int(0.975 * BOOTSTRAP_SAMPLES) - 1]


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def group_verdicts(review_dir: Path, key: dict[str, dict[str, str]]) -> dict[tuple[str, str], list[tuple[dict[str, Any], str]]]:
    grouped: dict[tuple[str, str], list[tuple[dict[str, Any], str]]] = {}
    for pair_id, origin in key.items():
        verdict: dict[str, Any] | None = read_verdict(review_dir / f"{pair_id}.json")
        if verdict is not None:
            grouped.setdefault((origin["task"], origin["run"]), []).append((verdict, origin["first"]))
    return grouped


def add_side_metrics(counts: dict[str, float], verdicts: list[tuple[dict[str, Any], str]], arm_a: str, arm_b: str) -> None:
    for verdict, first in verdicts:
        for arm, suffix in ((arm_a, "a"), (arm_b, "b")):
            merge, major = side_metrics(verdict, first, arm)
            counts[f"merge_{suffix}"] += merge
            counts[f"major_{suffix}"] += major
        counts["verdicts"] += 1


def tally(
    grouped: dict[tuple[str, str], list[tuple[dict[str, Any], str]]], arm_a: str, arm_b: str
) -> tuple[dict[str, dict[str, float]], dict[str, list[float]]]:
    """Per task: consistent wins, losses and ties, plus merge and major-change totals over every verdict."""
    per_task: dict[str, dict[str, float]] = {}
    scores_by_task: dict[str, list[float]] = {}
    for (task, _), verdicts in sorted(grouped.items()):
        outcome: str = consistent_outcome(verdicts, arm_a, arm_b)
        counts: dict[str, float] = per_task.setdefault(task, dict.fromkeys(TALLY_KEYS, 0.0))
        counts[outcome] += 1
        add_side_metrics(counts, verdicts, arm_a, arm_b)
        scores_by_task.setdefault(task, []).append(OUTCOME_SCORES[outcome])
    return per_task, scores_by_task


def summarize(review_dir: Path) -> dict[str, Any]:
    key: dict[str, dict[str, str]] = json.loads((review_dir / "key.json").read_text(encoding="utf-8"))
    if not key:
        raise SystemExit(f"pairwise_review: {review_dir} has no pairs")
    arm_a: str = next(iter(key.values()))["arm_a"]
    arm_b: str = next(iter(key.values()))["arm_b"]
    per_task, scores_by_task = tally(group_verdicts(review_dir, key), arm_a, arm_b)
    if not scores_by_task:
        raise SystemExit(f"pairwise_review: no readable verdict in {review_dir}")
    task_wins: int = sum(1 for counts in per_task.values() if counts["b"] > counts["a"])
    task_losses: int = sum(1 for counts in per_task.values() if counts["a"] > counts["b"])
    return {
        "arm_a": arm_a,
        "arm_b": arm_b,
        "per_task": per_task,
        "b_win_rate": round(mean([score for scores in scores_by_task.values() for score in scores]), 3),
        "b_win_rate_ci95": [round(bound, 3) for bound in bootstrap_ci(scores_by_task, mean)],
        "tasks_b_ahead": task_wins,
        "tasks_a_ahead": task_losses,
        "task_sign_test_p": round(sign_test_p(task_wins, task_losses), 4),
    }


def main(arguments: list[str]) -> None:
    if arguments[0] == "judge":
        judge(Path(arguments[1]), Path(arguments[2]), arguments[3], arguments[4])
        return
    print(json.dumps(summarize(Path(arguments[1])), indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])
