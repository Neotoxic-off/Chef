"""Build bench/results/summary.json, the single source of the README numbers and charts.

Usage: python bench/report.py <scores.json> <versions.txt> <pairwise-summary.json> [...]
       python bench/report.py history-point <version> <scores.json> <arm> <loop-dir> [...]

<scores.json> is the output of score.py; each pairwise summary is the output of
`pairwise_review.py summarize`. charts.py renders the README charts from the result.
`history-point` adds one version to results/history.json, from that version's scores and merge-loop
records on the chart's tasks.
"""

import json
import statistics
import sys
from pathlib import Path
from typing import Any

from merge_loop import load_records

RESULTS: Path = Path(__file__).resolve().parent / "results" / "summary.json"
HISTORY: Path = RESULTS.parent / "history.json"
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


def is_scored(run: dict[str, Any]) -> bool:
    """False for a run whose checker timed out (score.py writes `"scored": false`)."""
    return bool(run.get("scored", True))


def overall(arm_tasks: dict[str, dict[str, Any]]) -> dict[str, float]:
    runs: list[dict[str, Any]] = [run for report in arm_tasks.values() for run in report["runs"]]
    costs: list[float] = [run["cost_usd"] for run in runs if run.get("cost_usd") is not None]
    # A run whose checker timed out has no answer to judge; it still counts in runs and cost.
    passes: list[bool] = [correct(run) for run in runs if is_scored(run)]
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


def history_point(
    version: str, arm_tasks: dict[str, dict[str, Any]], records: list[dict[str, Any]], tasks: list[str]
) -> dict[str, Any]:
    """One version on the version chart: median cost and time of its first answers, share merged as is."""
    unscored: list[str] = [task for task in tasks if not any(is_scored(run) for run in arm_tasks.get(task, {}).get("runs", []))]
    if unscored:
        raise SystemExit(f"report: no scored run for the chart tasks {', '.join(unscored)}")
    runs: list[dict[str, Any]] = [run for task in tasks for run in arm_tasks[task]["runs"]]
    reviewed: list[dict[str, Any]] = [record for record in records if record["task"] in tasks]
    reviewers: set[str] = {record["reviewer"] for record in reviewed}
    if len(reviewers) != 1:
        raise SystemExit(f"report: one reviewer expected for the version point, got {sorted(reviewers)}")
    return {
        "version": version,
        "cost": round(statistics.median(measured(runs, "cost_usd")), 3),
        "merge": round(100 * sum(1 for record in reviewed if record.get("merged_after_fixes") == 0) / len(reviewed), 1),
        "reviews": len(reviewed),
        "seconds": round(statistics.median(measured(runs, "seconds")), 1),
        "reviewer": reviewers.pop(),
    }


def measured(runs: list[dict[str, Any]], key: str) -> list[float]:
    """The values a run reported; score.py writes None when a stream had no figure for it."""
    values: list[float] = [run[key] for run in runs if run.get(key) is not None]
    if not values:
        raise SystemExit(f"report: no run reported {key}")
    return values


def add_history_point(history: dict[str, Any], point: dict[str, Any]) -> dict[str, Any]:
    if any(entry["version"] == point["version"] for entry in history["versions"]):
        raise SystemExit(f"report: version {point['version']} is already in {HISTORY.name}")
    return history | {"versions": [*history["versions"], point]}


def main_history_point(arguments: list[str]) -> None:
    version: str = arguments[0]
    arm: str = arguments[2]
    scores: dict[str, dict[str, dict[str, Any]]] = json.loads(Path(arguments[1]).read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = [
        record for record in load_records([Path(path) for path in arguments[3:]]) if record["arm"] == arm
    ]
    history: dict[str, Any] = json.loads(HISTORY.read_text(encoding="utf-8"))
    point: dict[str, Any] = history_point(version, scores[arm], records, history["tasks"])
    HISTORY.write_text(json.dumps(add_history_point(history, point), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {HISTORY}: {point}")


def main(arguments: list[str]) -> None:
    if arguments[0] == "history-point":
        main_history_point(arguments[1:])
        return
    scores: dict[str, dict[str, dict[str, Any]]] = json.loads(Path(arguments[0]).read_text(encoding="utf-8"))
    versions: str = Path(arguments[1]).read_text(encoding="utf-8")
    pairwise: list[dict[str, Any]] = [json.loads(Path(path).read_text(encoding="utf-8")) for path in arguments[2:]]
    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.write_text(json.dumps(build(scores, versions, pairwise), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {RESULTS}")


if __name__ == "__main__":
    main(sys.argv[1:])
