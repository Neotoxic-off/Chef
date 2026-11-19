import json
from pathlib import Path
from typing import Any

import blind_review


def test_review_metrics_counts_changes_by_severity() -> None:
    review: dict[str, Any] = {
        "correctness": 8,
        "quality": 6,
        "merge_as_is": False,
        "changes": [
            {"severity": "blocker", "change": "a"},
            {"severity": "minor", "change": "b"},
            {"severity": "minor", "change": "c"},
        ],
    }

    metrics: dict[str, float] = blind_review.review_metrics(review)

    assert metrics == {"correctness": 8, "quality": 6, "merge_as_is": 0.0, "blocker": 1, "major": 0, "minor": 2}


def test_mean_metrics_averages_and_counts_reviews() -> None:
    reviews: list[dict[str, float]] = [{"quality": 6.0}, {"quality": 9.0}]

    assert blind_review.mean_metrics(reviews) == {"quality": 7.5, "reviews": 2.0}


def test_read_review_without_structured_output_returns_none(tmp_path: Path) -> None:
    review_path: Path = tmp_path / "review.json"
    review_path.write_text(json.dumps({"result": "text only"}), encoding="utf-8")

    assert blind_review.read_review(review_path) is None


def test_read_review_missing_file_returns_none(tmp_path: Path) -> None:
    assert blind_review.read_review(tmp_path / "absent.json") is None


def test_anonymize_hides_history_caches_and_scoring_files(tmp_path: Path) -> None:
    workspace: Path = tmp_path / "out" / "none" / "python" / "1" / "workspace"
    for name in (".git/HEAD", ".venv/x", ".bench-coverage.json", ".chef.md", "CLAUDE.md", "endpoints.py"):
        (workspace / name).parent.mkdir(parents=True, exist_ok=True)
        (workspace / name).write_text("x", encoding="utf-8")

    key: dict[str, dict[str, str]] = blind_review.anonymize(tmp_path / "out", ["none"])

    origin: dict[str, str] = next(iter(key.values()))
    assert sorted(path.name for path in Path(origin["submission"]).iterdir()) == ["endpoints.py"]
    assert (origin["arm"], origin["task"], origin["run"]) == ("none", "python", "1")


def test_judge_prompt_names_the_seat_and_the_task_only() -> None:
    prompt: str = blind_review.judge_prompt("docker", blind_review.ROLES["security"])

    assert blind_review.ROLES["security"] in prompt
    assert "Dockerfile" in prompt
    assert "chef" not in prompt.lower()
