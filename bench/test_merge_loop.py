import json
from pathlib import Path
from typing import Any

import merge_loop


def review(merge: bool, severities: tuple[str, ...]) -> dict[str, Any]:
    return {"merge_as_is": merge, "changes": [{"severity": severity, "change": severity} for severity in severities]}


def test_required_changes_keeps_blockers_and_majors_only() -> None:
    assert merge_loop.required_changes(review(False, ("blocker", "minor", "major"))) == ["blocker", "major"]


def test_is_mergeable_when_only_minor_changes_remain() -> None:
    assert merge_loop.is_mergeable(review(False, ("minor",)))


def test_is_not_mergeable_with_a_major_change() -> None:
    assert not merge_loop.is_mergeable(review(False, ("major",)))


def test_arm_summary_counts_unmerged_runs_in_the_cost() -> None:
    records: list[dict[str, Any]] = [
        {"merged_after_fixes": 0, "fix_costs": [], "first_cost": 0.2, "total_cost": 0.2},
        {"merged_after_fixes": 1, "fix_costs": [0.1], "first_cost": 0.1, "total_cost": 0.2},
        {"fix_costs": [0.1, 0.1], "first_cost": 0.1, "total_cost": 0.3},
    ]

    summary: dict[str, float] = merge_loop.arm_summary(records)

    assert summary["merged_first_time"] == 0.333
    assert summary["merged_in_the_end"] == 0.667
    assert summary["total_cost"] == 0.7
    assert summary["cost_per_merged_run"] == 0.35


def test_summarize_groups_records_by_arm(tmp_path: Path) -> None:
    record_dir: Path = tmp_path / "none" / "go" / "1"
    record_dir.mkdir(parents=True)
    record: dict[str, Any] = {"arm": "none", "merged_after_fixes": 0, "fix_costs": [], "first_cost": 0.1, "total_cost": 0.1}
    (record_dir / "record.json").write_text(json.dumps(record), encoding="utf-8")

    assert merge_loop.summarize(tmp_path)["none"]["merged_first_time"] == 1.0


def test_lines_to_review_counts_text_lines_and_skips_binaries(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("a = 1" + chr(10) + "b = 2" + chr(10), encoding="utf-8")
    (tmp_path / "logo.png").write_bytes(bytes([0, 1, 10, 10]))

    assert merge_loop.lines_to_review(tmp_path) == 2


def test_review_cost_of_a_crashed_review_is_zero(tmp_path: Path) -> None:
    (tmp_path / "review-0.json").write_text("", encoding="utf-8")

    assert merge_loop.review_cost(tmp_path / "review-0.json") == 0.0
