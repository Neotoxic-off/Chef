import re
from typing import Any

import charts

SUMMARY: dict[str, Any] = {
    "tasks": {arm: {"go": {"cost_usd": cost}} for arm, cost in (("none", 0.05), ("control", 0.08), ("chef", 0.2))},
    "pairwise": {"chef_vs_none": {"per_task": {"go": {"b": 2, "a": 0, "tie": 1}}}},
    "reviews": {"none": {"merge_as_is": 0.47, "major_changes": 0.81}, "chef": {"merge_as_is": 0.88, "major_changes": 0.12}},
    "overall": {"none": {"median_cost_usd": 0.063}, "chef": {"median_cost_usd": 0.155}},
}


def test_quality_chart_draws_a_tile_per_language_with_its_icon_biggest_gain_first() -> None:
    scores: dict[str, float] = {"quality": 5.5, "clarity": 6.0, "maintainability": 4.5, "functionality": 7.0}
    quality: dict[str, Any] = {
        "criteria": ["quality", "clarity", "maintainability", "functionality"],
        "arms": {"none": scores, "chef16": {name: value + 3 for name, value in scores.items()}},
        "tasks": {
            "go": {"none": 5.0, "chef16": 8.2},
            "csharp": {"none": 6.0, "chef16": 8.5},
            "cpp": {"none": 7.0, "chef16": 7.0},
        },
    }

    svg: str = charts.quality_chart(charts.LIGHT, quality)

    labels: list[str] = [">All 3 languages<", ">Go<", ">C#<", ">C++<"]
    assert [svg.index(label) for label in labels] == sorted(svg.index(label) for label in labels)
    assert svg.count("<path ") == 2
    assert ">+3.2<" in svg and ">+0.0<" in svg and ">5.8<" in svg and ">8.8<" in svg
    assert "Go 5.0 to 8.2" in svg


def test_rows_chart_puts_the_legend_on_its_own_line_under_the_title() -> None:
    chart: charts.Chart = charts.Chart("A long title " * 6, "label", 10.0, "/10")
    series: list[charts.Series] = [charts.Series("none", "Plain Claude", "#111111")]

    svg: str = charts.rows_chart(charts.LIGHT, chart, [("go", {"none": 5.0})], series)

    title: re.Match[str] | None = re.search(r'<text x="[^"]*" y="([^"]*)"[^>]*>A long title', svg)
    legend: re.Match[str] | None = re.search(r'<text x="[^"]*" y="([^"]*)"[^>]*>Plain Claude<', svg)
    assert title is not None and legend is not None
    assert float(legend.group(1)) > float(title.group(1))


def test_arm_shades_give_the_newest_chef_the_chef_color_and_older_ones_lighter_shades() -> None:
    shades: dict[str, str] = charts.arm_shades(charts.LIGHT, ["none", "chef13", "chef14", "chef15"])

    assert shades == {
        "none": charts.LIGHT.without,
        "chef15": charts.LIGHT.chef,
        "chef14": charts.LIGHT.old,
        "chef13": charts.LIGHT.older,
    }


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
        "chef152": {"runs": 2.0, "merged_first_time": 1.0, "fix_rounds_per_run": 0.0, "total_cost": 0.4},
        "chef16": {"runs": 2.0, "merged_first_time": 1.0, "fix_rounds_per_run": 0.0, "total_cost": 0.3},
    }

    svg: str = charts.overview_chart(charts.LIGHT, merge)

    assert "Chef 1.5: first answer accepted 100%, 0 review rounds per 100 tasks, $0.200 per task with fixes" in svg
    assert "Chef 1.6: first answer accepted 100%, 0 review rounds per 100 tasks, $0.150 per task with fixes" in svg
    assert charts.LIGHT.chef in svg
    assert charts.LIGHT.old in svg


def test_overview_chart_takes_its_own_title_and_arm_names() -> None:
    merge: dict[str, dict[str, float]] = {
        "none": {"runs": 2.0, "merged_first_time": 0.5, "fix_rounds_per_run": 0.5, "total_cost": 0.2},
        "chef14": {"runs": 2.0, "merged_first_time": 1.0, "fix_rounds_per_run": 0.0, "total_cost": 0.4},
    }

    svg: str = charts.overview_chart(charts.LIGHT, merge, charts.DEVOPS_TITLE)

    assert charts.DEVOPS_TITLE in svg
    assert "Chef 1.4: first answer accepted 100%" in svg
    assert charts.OVERVIEW_TITLE not in svg


def test_overview_chart_draws_a_bench_where_no_arm_needed_a_review_round() -> None:
    merge: dict[str, dict[str, float]] = {
        "chef14": {"runs": 1.0, "merged_first_time": 1.0, "fix_rounds_per_run": 0.0, "total_cost": 0.5},
        "chef16": {"runs": 2.0, "merged_first_time": 1.0, "fix_rounds_per_run": 0.0, "total_cost": 0.7},
    }

    svg: str = charts.overview_chart(charts.LIGHT, merge, charts.BENCH_11_TITLE)

    assert "Chef 1.6: first answer accepted 100%, 0 review rounds per 100 tasks, $0.350 per task with fixes" in svg


def test_overview_chart_scales_review_rounds_on_100_per_100_tasks() -> None:
    merge: dict[str, dict[str, float]] = {
        "chef16": {"runs": 20.0, "merged_first_time": 0.95, "fix_rounds_per_run": 0.05, "total_cost": 2.0},
    }

    svg: str = charts.overview_chart(charts.LIGHT, merge)

    review_bar: str = f'width="{charts.PANEL_WIDTH * 5 / 100:.1f}"'
    assert review_bar in svg


def test_break_even_is_the_extra_machine_cost_over_the_rounds_saved() -> None:
    plain: dict[str, float] = {"runs": 10.0, "total_cost": 1.0, "fix_rounds_per_run": 0.5}
    chef: dict[str, float] = {"runs": 10.0, "total_cost": 2.0, "fix_rounds_per_run": 0.1}

    assert round(charts.break_even(plain, chef), 3) == 0.25


def test_break_even_chart_labels_the_threshold_and_the_example_round() -> None:
    merge: dict[str, dict[str, float]] = {
        "none": {"runs": 10.0, "total_cost": 1.0, "fix_rounds_per_run": 0.5},
        "chef152": {"runs": 10.0, "total_cost": 2.5, "fix_rounds_per_run": 0.2},
        "chef16": {"runs": 10.0, "total_cost": 2.0, "fix_rounds_per_run": 0.1},
    }

    svg: str = charts.break_even_chart(charts.LIGHT, merge)

    assert "costs less once a round costs more than $0.25" in svg
    assert "plain Claude $15.10 and chef 1.6 $11.20 per task, 26% less" in svg
    assert "Chef 1.5" not in svg


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
        "chef16": {
            "runs": 2.0,
            "merged_first_time": 1.0,
            "first_answer_seconds": 40,
            "first_review_seconds": 25,
            "back_and_forth_seconds": 10,
        },
    }
    history: dict[str, Any] = {
        "versions": [
            {"version": "1.1", "seconds": 45.0, "plain_seconds": 15.0},
            {"version": "1.6", "seconds": 90.0, "plain_seconds": 45.0},
        ],
        "baseline": {"seconds": 45.0},
    }

    svg: str = charts.time_chart(charts.DARK, merge, history)

    assert "Plain Claude: first answer 20 s, first review 20 s, fixes and new reviews 30 s, 50% sent back" in svg
    assert "Chef 1.6: first answer 40 s, first review 25 s, fixes and new reviews 10 s, 0% sent back" in svg
    assert "First answer by version, as a multiple of plain Claude's: 1.1 3.0×, 1.6 2.0×." in svg
    assert "Chef 1.4:" not in svg
    assert charts.LIGHT.ink not in svg


def test_history_chart_labels_every_version_and_the_baseline() -> None:
    history: dict[str, Any] = {
        "tasks": ["python"],
        "versions": [
            {"version": "0.9.0", "cost": 0.2, "plain_cost": 0.05, "merge": 40.0},
            {"version": "1.1.0", "cost": 0.15, "plain_cost": 0.1, "merge": 90.0},
        ],
        "baseline": {"cost": 0.1, "merge": 45.0},
    }

    cost: str = charts.history_chart(charts.LIGHT, history, "cost")
    merge: str = charts.history_chart(charts.LIGHT, history, "merge")

    assert "as a multiple of plain Claude's, on python: 0.9.0 4.0×, 1.1.0 1.5×. Plain Claude: 1.0×." in cost
    assert "merge it as is, on python: 0.9.0 40%, 1.1.0 90%. Plain Claude: 45%." in merge


def test_history_chart_hides_plain_claude_merge_line_judged_by_another_reviewer() -> None:
    history: dict[str, Any] = {
        "tasks": ["python"],
        "versions": [
            {"version": "1.2.0", "cost": 0.2, "plain_cost": 0.06, "merge": 40.0, "reviewer": "old"},
            {"version": "1.3.0", "cost": 0.15, "plain_cost": 0.06, "merge": 90.0, "reviewer": "new"},
        ],
        "baseline": {"cost": 0.06, "merge": 45.0, "reviewer": "old"},
    }

    cost: str = charts.history_chart(charts.LIGHT, history, "cost")
    merge: str = charts.history_chart(charts.LIGHT, history, "merge")

    assert ">plain Claude 1.0×<" in cost
    assert ">plain Claude 45%<" not in merge
    assert cost.count("<polyline") == 1
    assert merge.count("<polyline") == 2


def test_time_chart_is_tall_enough_for_the_version_panel_and_the_legend() -> None:
    steps: dict[str, float] = {
        "runs": 1.0,
        "merged_first_time": 1.0,
        "first_answer_seconds": 10,
        "first_review_seconds": 10,
        "back_and_forth_seconds": 10,
    }
    merge: dict[str, dict[str, float]] = dict.fromkeys(("none", "chef14", "chef152", "chef16"), steps)
    history: dict[str, Any] = {
        "versions": [{"version": "1.4", "seconds": 40.0, "plain_seconds": 15.0}],
        "baseline": {"seconds": 15.0},
    }
    legend_bottom: float = charts.HISTORY_TOP + 4 * charts.TIME_ROW_STEP + 24
    panel_bottom: float = charts.HISTORY_TOP + charts.HISTORY_PANEL_HEIGHT + 40

    svg: str = charts.time_chart(charts.LIGHT, merge, history)

    assert f'height="{int(max(legend_bottom, panel_bottom))}"' in svg


def style_loop(merged_first_time: float, total_cost: float, lines: float) -> dict[str, float]:
    return {"runs": 2.0, "merged_first_time": merged_first_time, "total_cost": total_cost, "lines_to_review": lines}


def test_style_chart_shows_each_setup_with_its_mean_over_the_tasks_every_setup_ran() -> None:
    loops: dict[str, dict[str, float]] = {arm: style_loop(1.0, 0.4, 100) for arm in charts.STYLE_ARMS}
    styles: dict[str, Any] = {
        "tasks": {
            "python": loops | {"caveman": style_loop(0.0, 0.2, 50)},
            "bash": loops,
            "sql": {"none": style_loop(0.5, 0.4, 100)},
        }
    }

    svg: str = charts.style_chart(charts.LIGHT, styles)

    assert "Caveman 4.1: first answer accepted 50%, $0.150 per task, 75 lines to review" in svg
    assert "Plain Claude: first answer accepted 100%, $0.200 per task, 100 lines to review" in svg
    assert ">75 lines<" in svg and ">lower is better<" in svg


def test_minor_releases_keeps_the_latest_patch_of_each_minor_labelled_major_minor() -> None:
    history: dict[str, Any] = {
        "versions": [{"version": "1.4.0", "cost": 0.3}, {"version": "1.5.0", "cost": 0.2}, {"version": "1.5.2", "cost": 0.1}],
        "baseline": {"cost": 0.05},
    }

    minor: dict[str, Any] = charts.minor_releases(history)

    assert minor["versions"] == [{"version": "1.4", "cost": 0.3}, {"version": "1.5", "cost": 0.1}]
    assert minor["baseline"] == {"cost": 0.05}


def test_icon_scales_a_logo_drawn_on_another_viewbox_to_24_units() -> None:
    icons: dict[str, Any] = {"paths": {"java": "M0 0h128", "go": "M0 0h24"}, "viewbox": 24, "viewboxes": {"java": 128}}

    java: list[str] = charts.icon(charts.LIGHT, 10.0, 20.0, "java", icons)
    go: list[str] = charts.icon(charts.LIGHT, 10.0, 20.0, "go", icons)

    assert 'transform="translate(10.0 20.0) scale(0.1875)"' in java[0]
    assert 'transform="translate(10.0 20.0)"' in go[0]


def test_relative_to_plain_divides_each_version_by_its_own_plain_claude_and_sets_plain_to_one() -> None:
    history: dict[str, Any] = {
        "versions": [{"version": "1.4", "cost": 0.18, "plain_cost": 0.06}, {"version": "1.6", "cost": 0.27, "plain_cost": 0.135}],
        "baseline": {"cost": 0.135},
    }

    relative: dict[str, Any] = charts.relative_to_plain(history, "cost")

    assert [round(entry["cost"], 2) for entry in relative["versions"]] == [3.0, 2.0]
    assert relative["baseline"]["cost"] == 1.0
