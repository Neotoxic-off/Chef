import json
from pathlib import Path
from typing import Any

import pytest

import merge_loop


def review(merge: bool, severities: tuple[str, ...]) -> dict[str, Any]:
    return {"merge_as_is": merge, "changes": [{"severity": severity, "change": severity} for severity in severities]}


def test_required_changes_keeps_blockers_and_majors_only() -> None:
    assert merge_loop.required_changes(review(False, ("blocker", "minor", "major"))) == ["blocker", "major"]


def test_is_mergeable_when_only_minor_changes_remain() -> None:
    assert merge_loop.is_mergeable(review(False, ("minor",)))


def test_is_not_mergeable_with_a_major_change() -> None:
    assert not merge_loop.is_mergeable(review(False, ("major",)))


def test_is_not_mergeable_when_merge_as_is_but_a_major_change_is_listed() -> None:
    assert not merge_loop.is_mergeable(review(True, ("major",)))


def test_loop_records_an_error_when_a_fix_gives_no_answer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def rejecting_review(_sample: merge_loop.Sample, _review_path: Path) -> dict[str, Any]:
        return review(False, ("major",))

    def usage_limited_fix(_sample: merge_loop.Sample, _changes: list[str], _plugin_dir: str, stream_path: Path) -> float:
        stream_path.write_text(json.dumps({"type": "result", "terminal_reason": "api_error", "api_error": "usage_limit_reached"}))
        return 0.0

    monkeypatch.setattr(merge_loop, "review", rejecting_review)
    monkeypatch.setattr(merge_loop, "fix", usage_limited_fix)
    sample: merge_loop.Sample = merge_loop.Sample("none", "go", "1", tmp_path, 0.1)

    record: dict[str, Any] = merge_loop.loop(sample, "", tmp_path)

    assert record["error"] == "fix 1 gave no answer: API error: usage_limit_reached"
    assert "merged_after_fixes" not in record


def test_loop_reviews_again_after_a_fix_that_completes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    verdicts: list[dict[str, Any]] = [review(False, ("major",)), review(False, ())]

    def next_review(_sample: merge_loop.Sample, _review_path: Path) -> dict[str, Any]:
        return verdicts.pop(0)

    def finished_fix(_sample: merge_loop.Sample, _changes: list[str], _plugin_dir: str, stream_path: Path) -> float:
        stream_path.write_text(json.dumps({"type": "result", "terminal_reason": "completed"}))
        return 0.05

    monkeypatch.setattr(merge_loop, "review", next_review)
    monkeypatch.setattr(merge_loop, "fix", finished_fix)
    sample: merge_loop.Sample = merge_loop.Sample("none", "go", "1", tmp_path, 0.1)

    record: dict[str, Any] = merge_loop.loop(sample, "", tmp_path)

    assert record["merged_after_fixes"] == 1
    assert record["total_cost"] == 0.15


def test_run_all_refuses_first_answers_that_gave_no_answer(tmp_path: Path) -> None:
    run_dir: Path = tmp_path / "out" / "none" / "go" / "1"
    (run_dir / "workspace").mkdir(parents=True)
    (run_dir / "stream.jsonl").write_text('{"type": "system"}\n', encoding="utf-8")

    with pytest.raises(SystemExit, match="merge_loop: these runs gave no answer"):
        merge_loop.run_all(tmp_path / "out", tmp_path / "loop", {"none": ""})


def test_summarize_refuses_unfinished_records(tmp_path: Path) -> None:
    record_dir: Path = tmp_path / "none" / "go" / "1"
    record_dir.mkdir(parents=True)
    record: dict[str, Any] = {"arm": "none", "task": "go", "run": "1", "error": "fix 1 gave no answer", "fix_costs": []}
    (record_dir / "record.json").write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(SystemExit, match="none/go/1: fix 1 gave no answer"):
        merge_loop.summarize(tmp_path)


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
