"""Build bench/results/summary.json, the single source of the README numbers and charts.

Usage: python bench/report.py <scores.json> <versions.txt> <pairwise-summary.json> [...]

<scores.json> is the output of score.py; each pairwise summary is the output of
`pairwise_review.py summarize`. charts.py renders the README charts from the result.
"""

import json
import statistics
import sys
from pathlib import Path
from typing import Any

RESULTS: Path = Path(__file__).resolve().parent / "results" / "summary.json"
TASK_METRICS: tuple[str, ...] = ("cost_usd", "turns", "output_tokens", "cache_write_tokens", "hidden_test_passes")


def task_summary(arm_tasks: dict[str, dict[str, Any]]) -> dict[str, dict[str, float | None]]:
    return {
        task: {metric: report["summary"].get(metric) for metric in TASK_METRICS} for task, report in sorted(arm_tasks.items())
    }


def correct(run: dict[str, Any]) -> bool:
    """The task's own correctness check: a hidden test, a healthy container, or valid Prometheus config and rules."""
    if run.get("hidden_test_passes") is not None:
        return bool(run["hidden_test_passes"])
    if run.get("container_healthy") is not None:
        return bool(run["container_healthy"])
    return bool(run.get("config_valid")) and bool(run.get("rules_valid"))


def overall(arm_tasks: dict[str, dict[str, Any]]) -> dict[str, float]:
    runs: list[dict[str, Any]] = [run for report in arm_tasks.values() for run in report["runs"]]
    costs: list[float] = [run["cost_usd"] for run in runs if run.get("cost_usd") is not None]
    passes: list[bool] = [correct(run) for run in runs]
    return {
        "runs": float(len(runs)),
        "total_cost_usd": round(sum(costs), 2),
        "median_cost_usd": round(statistics.median(costs), 3) if costs else 0.0,
        "correct_rate": round(statistics.fmean(passes), 3) if passes else 0.0,
    }


def public_versions(versions: str) -> list[str]:
    """Keep only the folder name of each arm's source, so no local path is published."""
    lines: list[str] = []
    for line in versions.strip().splitlines():
        prefix, separator, source = line.partition(": ")
        is_arm: bool = prefix.startswith("arm ") and bool(separator)
        lines.append(f"{prefix}: {Path(source.replace(chr(92), '/')).name}" if is_arm else line)
    return lines


def review_rollup(pairwise: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Per arm, over every blind verdict it appeared in: share merged as is and changes required per review."""
    totals: dict[str, dict[str, float]] = {}
    for summary in pairwise:
        for side in ("a", "b"):
            arm: str = summary[f"arm_{side}"]
            entry: dict[str, float] = totals.setdefault(arm, {"merge": 0.0, "major": 0.0, "verdicts": 0.0})
            for counts in summary["per_task"].values():
                entry["merge"] += counts[f"merge_{side}"]
                entry["major"] += counts[f"major_{side}"]
                entry["verdicts"] += counts["verdicts"]
    return {
        arm: {
            "merge_as_is": round(entry["merge"] / entry["verdicts"], 3),
            "major_changes": round(entry["major"] / entry["verdicts"], 2),
        }
        for arm, entry in totals.items()
        if entry["verdicts"]
    }


def build(scores: dict[str, dict[str, dict[str, Any]]], versions: str, pairwise: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "versions": public_versions(versions),
        "arms": sorted(scores),
        "tasks": {arm: task_summary(arm_tasks) for arm, arm_tasks in scores.items()},
        "overall": {arm: overall(arm_tasks) for arm, arm_tasks in scores.items()},
        "pairwise": {f"{summary['arm_b']}_vs_{summary['arm_a']}": summary for summary in pairwise},
        "reviews": review_rollup(pairwise),
    }


def main(arguments: list[str]) -> None:
    scores: dict[str, dict[str, dict[str, Any]]] = json.loads(Path(arguments[0]).read_text(encoding="utf-8"))
    versions: str = Path(arguments[1]).read_text(encoding="utf-8")
    pairwise: list[dict[str, Any]] = [json.loads(Path(path).read_text(encoding="utf-8")) for path in arguments[2:]]
    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.write_text(json.dumps(build(scores, versions, pairwise), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {RESULTS}")


if __name__ == "__main__":
    main(sys.argv[1:])
