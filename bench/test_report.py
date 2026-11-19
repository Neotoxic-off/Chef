from typing import Any

import report


def arm(cost: float, passed: bool) -> dict[str, Any]:
    run: dict[str, Any] = {"cost_usd": cost, "hidden_test_passes": passed}
    return {"go": {"runs": [run, run], "summary": {"cost_usd": cost, "turns": 3, "hidden_test_passes": float(passed)}}}


def test_build_keys_pairwise_by_arms_and_keeps_task_metrics() -> None:
    pairwise: list[dict[str, Any]] = [{"arm_a": "none", "arm_b": "chef", "b_win_rate": 0.7}]

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
