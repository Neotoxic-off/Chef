from typing import Any

import charts

SUMMARY: dict[str, Any] = {
    "tasks": {arm: {"go": {"cost_usd": cost}} for arm, cost in (("none", 0.05), ("control", 0.08), ("chef", 0.2))},
    "pairwise": {"chef_vs_none": {"per_task": {"go": {"b": 2, "a": 0, "tie": 1}}}},
    "reviews": {"none": {"merge_as_is": 0.47, "major_changes": 0.81}, "chef": {"merge_as_is": 0.88, "major_changes": 0.12}},
    "overall": {"none": {"median_cost_usd": 0.063}, "chef": {"median_cost_usd": 0.155}},
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


def test_overview_chart_lists_each_reviewed_arm() -> None:
    svg: str = charts.overview_chart(charts.LIGHT, SUMMARY)

    assert "Plain Claude: merged as is 47%, 0.81 changes required per review, median cost $0.063 per task" in svg
    assert "Control" not in svg
