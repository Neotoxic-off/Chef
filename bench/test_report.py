from typing import Any

import pytest

import report


def chart_record(task: str, merged_after_fixes: int, reviewer: str = "r1") -> dict[str, Any]:
    return {"task": task, "reviewer": reviewer, "merged_after_fixes": merged_after_fixes}


def test_history_point_takes_medians_of_the_chart_tasks_and_the_first_review() -> None:
    arm_tasks: dict[str, dict[str, Any]] = {
        "python": {"runs": [{"cost_usd": 0.1, "seconds": 30.0}, {"cost_usd": 0.3, "seconds": 50.0}]},
        "docker": {"runs": [{"cost_usd": 0.2, "seconds": 40.0}]},
        "go": {"runs": [{"cost_usd": 9.0, "seconds": 900.0}]},
    }
    records: list[dict[str, Any]] = [chart_record("python", 0), chart_record("docker", 1), chart_record("go", 1)]

    point: dict[str, Any] = report.history_point("1.3.0", arm_tasks, records, ["python", "docker"])

    assert point == {"version": "1.3.0", "cost": 0.2, "merge": 50.0, "reviews": 2, "seconds": 40.0, "reviewer": "r1"}


def test_history_point_refuses_a_chart_task_without_scored_runs() -> None:
    arm_tasks: dict[str, dict[str, Any]] = {"python": {"runs": []}}

    with pytest.raises(SystemExit, match="no scored run for the chart tasks python, docker"):
        report.history_point("1.3.0", arm_tasks, [chart_record("python", 0)], ["python", "docker"])


def test_history_point_skips_runs_without_a_figure() -> None:
    arm_tasks: dict[str, dict[str, Any]] = {
        "python": {"runs": [{"cost_usd": None, "seconds": 30.0}, {"cost_usd": 0.4, "seconds": None}]}
    }

    point: dict[str, Any] = report.history_point("1.3.0", arm_tasks, [chart_record("python", 0)], ["python"])

    assert (point["cost"], point["seconds"]) == (0.4, 30.0)


def test_history_point_refuses_records_from_two_reviewers() -> None:
    arm_tasks: dict[str, dict[str, Any]] = {"python": {"runs": [{"cost_usd": 0.1, "seconds": 30.0}]}}
    records: list[dict[str, Any]] = [chart_record("python", 0, "r1"), chart_record("python", 0, "r2")]

    with pytest.raises(SystemExit, match="one reviewer expected"):
        report.history_point("1.3.0", arm_tasks, records, ["python"])


def test_add_history_point_refuses_a_version_already_there() -> None:
    history: dict[str, Any] = {"versions": [{"version": "1.2.0"}]}

    with pytest.raises(SystemExit, match="1.2.0 is already"):
        report.add_history_point(history, {"version": "1.2.0"})


def arm(cost: float, passed: bool) -> dict[str, Any]:
    run: dict[str, Any] = {"cost_usd": cost, "hidden_test_passes": passed}
    return {"go": {"runs": [run, run], "summary": {"cost_usd": cost, "turns": 3, "hidden_test_passes": float(passed)}}}


def test_build_keys_pairwise_by_arms_and_keeps_task_metrics() -> None:
    pairwise: list[dict[str, Any]] = [{"arm_a": "none", "arm_b": "chef", "b_win_rate": 0.7, "per_task": {}}]

    summary: dict[str, Any] = report.build({"none": arm(0.05, True), "chef": arm(0.2, True)}, "2.1.328\n", pairwise)

    assert summary["pairwise"]["chef_vs_none"]["b_win_rate"] == 0.7
    assert summary["tasks"]["chef"]["go"]["cost_usd"] == 0.2
    assert summary["versions"] == ["2.1.328"]


def test_overall_sums_cost_and_pass_rate_over_runs() -> None:
    assert report.overall(arm(0.25, False)) == {
        "runs": 2.0,
        "total_cost_usd": 0.5,
        "median_cost_usd": 0.25,
        "correct_rate": 0.0,
    }


def test_correct_uses_the_task_specific_check() -> None:
    assert report.correct({"container_healthy": True})
    assert report.correct({"config_valid": True, "rules_valid": True})
    assert not report.correct({"hidden_test_passes": False, "container_healthy": True})


def test_public_versions_drops_local_paths() -> None:
    versions: str = "2.1.328\narm none: \narm chef: C:\\Users\\someone\\Temp\\chef-1.0\n"

    assert report.public_versions(versions) == ["2.1.328", "arm none: ", "arm chef: chef-1.0"]


def test_review_rollup_pools_every_verdict_per_arm() -> None:
    counts: dict[str, float] = {"merge_a": 1, "merge_b": 2, "major_a": 4, "major_b": 0, "verdicts": 2}
    pairwise: list[dict[str, Any]] = [
        {"arm_a": "none", "arm_b": "chef", "per_task": {"go": counts}},
        {"arm_a": "control", "arm_b": "chef", "per_task": {"go": counts}},
    ]

    rollup: dict[str, dict[str, float]] = report.review_rollup(pairwise)

    assert rollup["chef"] == {"merge_as_is": 1.0, "major_changes": 0.0}
    assert rollup["none"] == {"merge_as_is": 0.5, "major_changes": 2.0}
