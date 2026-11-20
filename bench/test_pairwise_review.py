import json
from pathlib import Path
from typing import Any

import pytest

import pairwise_review

FINISHED_RESULT: str = json.dumps({"type": "result", "subtype": "success", "terminal_reason": "completed"})


def verdict(winner: str, first_merge: bool = False, second_merge: bool = False) -> dict[str, Any]:
    return {
        "winner": winner,
        "first_merge_as_is": first_merge,
        "second_merge_as_is": second_merge,
        "first_major_changes": 2,
        "second_major_changes": 0,
        "reason": "r",
    }


def test_consistent_outcome_counts_a_win_when_both_orders_agree() -> None:
    verdicts: list[tuple[dict[str, Any], str]] = [(verdict("second"), "none"), (verdict("first"), "chef")]

    assert pairwise_review.consistent_outcome(verdicts, "none", "chef") == "b"


def test_consistent_outcome_is_a_tie_when_orders_disagree() -> None:
    verdicts: list[tuple[dict[str, Any], str]] = [(verdict("first"), "none"), (verdict("first"), "chef")]

    assert pairwise_review.consistent_outcome(verdicts, "none", "chef") == "tie"


def test_consistent_outcome_is_a_tie_with_a_single_order() -> None:
    assert pairwise_review.consistent_outcome([(verdict("second"), "none")], "none", "chef") == "tie"


def test_side_metrics_reads_the_side_that_held_the_arm() -> None:
    assert pairwise_review.side_metrics(verdict("tie", second_merge=True), "none", "chef") == (1.0, 0.0)


def test_sign_test_p_matches_exact_binomial() -> None:
    assert round(pairwise_review.sign_test_p(11, 2), 4) == 0.0225


def test_sign_test_p_without_decisive_tasks_is_one() -> None:
    assert pairwise_review.sign_test_p(0, 0) == 1.0


def test_bootstrap_ci_of_identical_scores_is_a_point() -> None:
    assert pairwise_review.bootstrap_ci({"go": [1.0, 1.0], "rust": [1.0]}, pairwise_review.mean) == (1.0, 1.0)


def test_summarize_reports_task_level_wins(tmp_path: Path) -> None:
    key: dict[str, dict[str, str]] = {
        "000-ab": {"task": "go", "run": "1", "first": "none", "arm_a": "none", "arm_b": "chef"},
        "000-ba": {"task": "go", "run": "1", "first": "chef", "arm_a": "none", "arm_b": "chef"},
    }
    (tmp_path / "key.json").write_text(json.dumps(key), encoding="utf-8")
    for pair_id, winner in (("000-ab", "second"), ("000-ba", "first")):
        (tmp_path / f"{pair_id}.json").write_text(json.dumps({"structured_output": verdict(winner)}), encoding="utf-8")

    summary: dict[str, Any] = pairwise_review.summarize(tmp_path)

    assert (summary["b_win_rate"], summary["tasks_b_ahead"], summary["tasks_a_ahead"]) == (1.0, 1, 0)


def test_find_pairs_keeps_runs_present_in_both_arms(tmp_path: Path) -> None:
    for arm, run in (("none", "1"), ("chef", "1"), ("none", "2")):
        (tmp_path / arm / "go" / run / "workspace").mkdir(parents=True)
        (tmp_path / arm / "go" / run / "stream.jsonl").write_text(FINISHED_RESULT, encoding="utf-8")

    pairs: list[pairwise_review.Pair] = pairwise_review.find_pairs(tmp_path, "none", "chef")

    assert [(pair.task, pair.run) for pair in pairs] == [("go", "1")]


def test_find_pairs_refuses_a_run_that_gave_no_answer(tmp_path: Path) -> None:
    for arm in ("none", "chef"):
        (tmp_path / arm / "go" / "1" / "workspace").mkdir(parents=True)
    (tmp_path / "none" / "go" / "1" / "stream.jsonl").write_text(FINISHED_RESULT, encoding="utf-8")

    with pytest.raises(SystemExit, match="pairwise_review: these runs gave no answer"):
        pairwise_review.find_pairs(tmp_path, "none", "chef")


def test_read_verdict_skips_an_empty_file_left_by_a_crashed_judge(tmp_path: Path) -> None:
    verdict_path: Path = tmp_path / "000-ab.json"
    verdict_path.write_text("", encoding="utf-8")

    assert pairwise_review.read_verdict(verdict_path) is None


def test_consistent_outcome_counts_an_a_win_when_both_orders_agree() -> None:
    verdicts: list[tuple[dict[str, Any], str]] = [(verdict("first"), "none"), (verdict("second"), "chef")]

    assert pairwise_review.consistent_outcome(verdicts, "none", "chef") == "a"


def test_consistent_outcome_keeps_a_tie_both_judges_called() -> None:
    verdicts: list[tuple[dict[str, Any], str]] = [(verdict("tie"), "none"), (verdict("tie"), "chef")]

    assert pairwise_review.consistent_outcome(verdicts, "none", "chef") == "tie"
