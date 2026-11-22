import json
from pathlib import Path
from typing import Any

import quality_review


def write_review(review_dir: Path, sample_id: str, quality: int, changes: list[dict[str, str]]) -> None:
    review: dict[str, Any] = {"correctness": 9, "quality": quality, "merge_as_is": not changes, "changes": changes}
    (review_dir / f"{sample_id}.json").write_text(json.dumps({"structured_output": review}), encoding="utf-8")


def test_summarize_averages_each_arm_and_lists_quality_per_reference(tmp_path: Path) -> None:
    key: dict[str, dict[str, str]] = {
        "a1": {"arm": "none", "task": "python", "run": "1", "submission": "x"},
        "b2": {"arm": "chef15", "task": "python", "run": "1", "submission": "y"},
        "c3": {"arm": "chef15", "task": "go", "run": "1", "submission": "z"},
    }
    (tmp_path / "key.json").write_text(json.dumps(key), encoding="utf-8")
    write_review(tmp_path, "a1", 5, [{"change": "add tests", "severity": "major"}])
    write_review(tmp_path, "b2", 8, [{"change": "rename", "severity": "minor"}])
    write_review(tmp_path, "c3", 9, [])

    summary: dict[str, Any] = quality_review.summarize(tmp_path)

    assert summary["arms"] == {
        "chef15": {"quality": 8.5, "correctness": 9.0, "mergeable": 1.0, "reviews": 2.0},
        "none": {"quality": 5.0, "correctness": 9.0, "mergeable": 0.0, "reviews": 1.0},
    }
    assert summary["tasks"] == {"go": {"chef15": 9.0}, "python": {"chef15": 8.0, "none": 5.0}}
    assert len(summary["reviewer"]) > 0


def test_summarize_skips_a_missing_review(tmp_path: Path) -> None:
    key: dict[str, dict[str, str]] = {
        "a1": {"arm": "none", "task": "python", "run": "1", "submission": "x"},
        "b2": {"arm": "none", "task": "go", "run": "1", "submission": "y"},
    }
    (tmp_path / "key.json").write_text(json.dumps(key), encoding="utf-8")
    write_review(tmp_path, "a1", 6, [])

    summary: dict[str, Any] = quality_review.summarize(tmp_path)

    assert summary["arms"]["none"]["reviews"] == 1.0
    assert summary["tasks"] == {"python": {"none": 6.0}}


def test_every_quality_task_matches_a_reference() -> None:
    references: Path = quality_review.QUALITY_DIR.parent.parent / "skills" / "chef" / "references"
    tasks: list[Path] = sorted(path for path in quality_review.QUALITY_DIR.iterdir() if path.is_dir())

    assert len(tasks) == 32
    assert [task.name for task in tasks if not (references / f"{task.name}.md").is_file()] == []
    assert all((task / "prompt.md").is_file() for task in tasks)
