from typing import Any

import charts

SUMMARY: dict[str, Any] = {
    "tasks": {arm: {"go": {"cost_usd": cost}} for arm, cost in (("none", 0.05), ("control", 0.08), ("chef", 0.2))},
    "pairwise": {"chef_vs_none": {"per_task": {"go": {"b": 2, "a": 0, "tie": 1}}}},
    "reviews": {"none": {"merge_as_is": 0.47, "major_changes": 0.81}, "chef": {"merge_as_is": 0.88, "major_changes": 0.12}},
    "overall": {"none": {"median_cost_usd": 0.063}, "chef": {"median_cost_usd": 0.155}},
}


def test_quality_chart_shows_each_criterion_then_each_reference_with_one_bar_per_arm() -> None:
    scores: dict[str, float] = {"quality": 5.5, "clarity": 6.0, "maintainability": 4.5, "functionality": 7.0}
    quality: dict[str, Any] = {
        "criteria": ["quality", "clarity", "maintainability", "functionality"],
        "arms": {"none": scores, "chef15": {name: value + 3 for name, value in scores.items()}},
        "tasks": {"go": {"none": 5.0, "chef15": 8.25}, "python": {"none": 6.0, "chef15": 8.5}},
    }

    svg: str = charts.quality_chart(charts.LIGHT, quality)

    assert "2 most-used references" in svg
    labels: list[str] = [">Quality<", ">Clarity<", ">Maintainability<", ">Functionality<", ">go.md<", ">python.md<"]
    assert [svg.index(label) for label in labels] == sorted(svg.index(label) for label in labels)
    assert "Plain Claude" in svg and "Chef 1.5" in svg and "Chef 1.4" not in svg
    assert ">7.5<" in svg and ">8.2<" in svg
    assert charts.LIGHT.chef in svg


def test_cost_chart_is_an_svg_with_an_accessible_label() -> None:
    svg: str = charts.cost_chart(charts.LIGHT, SUMMARY)

    assert svg.startswith("<svg")
    assert 'role="img"' in svg
    assert "go: Plain Claude $0.050" in svg


def test_pairwise_chart_skips_missing_comparisons() -> None:
    svg: str = charts.pairwise_chart(charts.DARK, SUMMARY)

    assert "Chef vs plain Claude 83%" in svg
    assert "Chef vs control" not in svg
    assert charts.LIGHT.ink not in svg


def test_win_rate_counts_ties_as_half() -> None:
    assert charts.win_rate({"b": 1.0, "a": 1.0, "tie": 2.0}) == 50.0


def test_overview_chart_lists_each_looped_arm() -> None:
    merge: dict[str, dict[str, float]] = {
        "none": {"runs": 2.0, "merged_first_time": 0.5, "fix_rounds_per_run": 0.5, "total_cost": 0.2},
    }

    svg: str = charts.overview_chart(charts.LIGHT, merge)

    assert "Plain Claude: first answer accepted 50%, 50 review rounds per 100 tasks, $0.100 per task with fixes" in svg
    assert "Chef 1.3" not in svg


def test_overview_chart_draws_the_latest_chef_in_the_chef_color_and_the_previous_one_in_the_old_color() -> None:
    merge: dict[str, dict[str, float]] = {
        "none": {"runs": 2.0, "merged_first_time": 0.5, "fix_rounds_per_run": 0.5, "total_cost": 0.2},
        "chef13": {"runs": 2.0, "merged_first_time": 1.0, "fix_rounds_per_run": 0.0, "total_cost": 0.4},
        "chef14": {"runs": 2.0, "merged_first_time": 1.0, "fix_rounds_per_run": 0.0, "total_cost": 0.3},
    }

    svg: str = charts.overview_chart(charts.LIGHT, merge)

    assert "Chef 1.3: first answer accepted 100%, 0 review rounds per 100 tasks, $0.200 per task with fixes" in svg
    assert "Chef 1.4: first answer accepted 100%, 0 review rounds per 100 tasks, $0.150 per task with fixes" in svg
    assert charts.LIGHT.chef in svg
    assert charts.LIGHT.old in svg


def test_overview_chart_takes_its_own_title_and_arm_names() -> None:
    merge: dict[str, dict[str, float]] = {
        "none": {"runs": 2.0, "merged_first_time": 0.5, "fix_rounds_per_run": 0.5, "total_cost": 0.2},
        "chef14": {"runs": 2.0, "merged_first_time": 1.0, "fix_rounds_per_run": 0.0, "total_cost": 0.4},
    }

    svg: str = charts.overview_chart(charts.LIGHT, merge, charts.STACKS_TITLE, charts.STACKS_ARMS)

    assert charts.STACKS_TITLE in svg
    assert "Chef 1.4: first answer accepted 100%" in svg
    assert "Same 13 tasks" not in svg


def test_break_even_is_the_extra_machine_cost_over_the_rounds_saved() -> None:
    plain: dict[str, float] = {"runs": 10.0, "total_cost": 1.0, "fix_rounds_per_run": 0.5}
    chef: dict[str, float] = {"runs": 10.0, "total_cost": 2.0, "fix_rounds_per_run": 0.1}

    assert round(charts.break_even(plain, chef), 3) == 0.25


def test_break_even_chart_labels_the_threshold_and_the_example_round() -> None:
    merge: dict[str, dict[str, float]] = {
        "none": {"runs": 10.0, "total_cost": 1.0, "fix_rounds_per_run": 0.5},
        "chef14": {"runs": 10.0, "total_cost": 2.0, "fix_rounds_per_run": 0.1},
    }

    svg: str = charts.break_even_chart(charts.LIGHT, merge)

    assert "costs less once a round costs more than $0.25" in svg
    assert "plain Claude $15.10 and chef 1.4 $11.20 per task, 26% less" in svg
    assert "Chef 1.3" not in svg


def test_break_even_chart_draws_chef_13_beside_the_latest_chef() -> None:
    merge: dict[str, dict[str, float]] = {
        "none": {"runs": 10.0, "total_cost": 1.0, "fix_rounds_per_run": 0.5},
        "chef13": {"runs": 10.0, "total_cost": 2.5, "fix_rounds_per_run": 0.2},
        "chef14": {"runs": 10.0, "total_cost": 2.0, "fix_rounds_per_run": 0.1},
    }

    svg: str = charts.break_even_chart(charts.LIGHT, merge)

    assert "Chef 1.3: 1.20 reviews per task" in svg
    assert charts.LIGHT.old in svg


def test_same_reviewer_segments_breaks_the_line_where_the_reviewer_changes() -> None:
    versions: list[dict[str, Any]] = [{"reviewer": "old"}, {"reviewer": "old"}, {"reviewer": "new"}]
    points: list[tuple[float, float]] = [(0.0, 1.0), (1.0, 2.0), (2.0, 3.0)]

    segments: list[list[tuple[float, float]]] = charts.same_reviewer_segments(versions, points)

    assert segments == [[(0.0, 1.0), (1.0, 2.0)], [(2.0, 3.0)]]


def test_time_chart_labels_each_arm_step_and_version() -> None:
    merge: dict[str, dict[str, float]] = {
        "none": {
            "runs": 2.0,
            "merged_first_time": 0.5,
            "first_answer_seconds": 20,
            "first_review_seconds": 20,
            "back_and_forth_seconds": 30,
        },
        "chef12": {
            "runs": 2.0,
            "merged_first_time": 1.0,
            "first_answer_seconds": 40,
            "first_review_seconds": 25,
            "back_and_forth_seconds": 10,
        },
    }
    history: dict[str, Any] = {
        "versions": [{"version": "1.1.0", "seconds": 50.0}, {"version": "1.2.0", "seconds": 40.0}],
        "baseline": {"seconds": 15.0},
    }

    svg: str = charts.time_chart(charts.DARK, merge, history)

    assert "Plain Claude: first answer 20 s, first review 20 s, fixes and new reviews 30 s, 50% sent back" in svg
    assert "Chef 1.2: first answer 40 s, first review 25 s, fixes and new reviews 10 s, 0% sent back" in svg
    assert "First answer by version: 1.1.0 50 s, 1.2.0 40 s; plain Claude 15 s." in svg
    assert "Chef 1.1:" not in svg
    assert charts.LIGHT.ink not in svg


def test_history_chart_labels_every_version_and_the_baseline() -> None:
    history: dict[str, Any] = {
        "tasks": ["python"],
        "versions": [{"version": "0.9.0", "cost": 0.2, "merge": 40.0}, {"version": "1.1.0", "cost": 0.15, "merge": 90.0}],
        "baseline": {"cost": 0.06, "merge": 45.0},
    }

    cost: str = charts.history_chart(charts.LIGHT, history, "cost")
    merge: str = charts.history_chart(charts.LIGHT, history, "merge")

    assert "cost per task (median), on python: 0.9.0 $0.200, 1.1.0 $0.150. Plain Claude: $0.060." in cost
    assert "merge it as is, on python: 0.9.0 40%, 1.1.0 90%. Plain Claude: 45%." in merge


def test_history_chart_hides_plain_claude_merge_line_judged_by_another_reviewer() -> None:
    history: dict[str, Any] = {
        "tasks": ["python"],
        "versions": [
            {"version": "1.2.0", "cost": 0.2, "merge": 40.0, "reviewer": "old"},
            {"version": "1.3.0", "cost": 0.15, "merge": 90.0, "reviewer": "new"},
        ],
        "baseline": {"cost": 0.06, "merge": 45.0, "reviewer": "old"},
    }

    cost: str = charts.history_chart(charts.LIGHT, history, "cost")
    merge: str = charts.history_chart(charts.LIGHT, history, "merge")

    assert ">plain Claude $0.060<" in cost
    assert ">plain Claude 45%<" not in merge
    assert cost.count("<polyline") == 1
    assert merge.count("<polyline") == 2


def test_time_chart_grows_to_fit_the_legend_under_five_arms() -> None:
    steps: dict[str, float] = {
        "runs": 1.0,
        "merged_first_time": 1.0,
        "first_answer_seconds": 10,
        "first_review_seconds": 10,
        "back_and_forth_seconds": 10,
    }
    merge: dict[str, dict[str, float]] = dict.fromkeys(("none", "chef11", "chef12", "chef13", "chef14"), steps)
    history: dict[str, Any] = {"versions": [{"version": "1.4.0", "seconds": 40.0}], "baseline": {"seconds": 15.0}}
    legend_bottom: int = int(charts.HISTORY_TOP + 5 * charts.TIME_ROW_STEP + 24)

    svg: str = charts.time_chart(charts.LIGHT, merge, history)

    assert f'height="{legend_bottom}"' in svg
