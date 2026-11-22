import json
from pathlib import Path
from typing import Any

import quality_review


def write_review(review_dir: Path, sample_id: str, scores: tuple[int, int, int, int], changes: list[dict[str, str]]) -> None:
    review: dict[str, Any] = dict(zip(quality_review.CRITERIA, scores, strict=True)) | {"changes": changes}
    (review_dir / f"{sample_id}.json").write_text(json.dumps({"structured_output": review}), encoding="utf-8")


def write_key(review_dir: Path, samples: dict[str, tuple[str, str]]) -> None:
    key: dict[str, dict[str, str]] = {
        sample_id: {"arm": arm, "task": task, "run": "1", "submission": sample_id} for sample_id, (arm, task) in samples.items()
    }
    (review_dir / "key.json").write_text(json.dumps(key), encoding="utf-8")


def test_summarize_averages_each_criterion_per_arm_and_the_four_scores_per_reference(tmp_path: Path) -> None:
    write_key(tmp_path, {"a1": ("none", "python"), "b2": ("chef15", "python"), "c3": ("chef15", "go")})
    write_review(tmp_path, "a1", (5, 6, 4, 7), [{"change": "add tests", "severity": "major"}])
    write_review(tmp_path, "b2", (8, 9, 8, 9), [{"change": "rename", "severity": "minor"}])
    write_review(tmp_path, "c3", (9, 9, 10, 8), [])

    summary: dict[str, Any] = quality_review.summarize(tmp_path)

    assert summary["arms"] == {
        "chef15": {
            "quality": 8.5,
            "clarity": 9.0,
            "maintainability": 9.0,
            "functionality": 8.5,
            "mergeable": 1.0,
            "reviews": 2.0,
        },
        "none": {"quality": 5.0, "clarity": 6.0, "maintainability": 4.0, "functionality": 7.0, "mergeable": 0.0, "reviews": 1.0},
    }
    assert summary["tasks"] == {"go": {"chef15": 9.0}, "python": {"chef15": 8.5, "none": 5.5}}
    assert summary["criteria"] == ["quality", "clarity", "maintainability", "functionality"]


def test_summarize_skips_a_missing_review(tmp_path: Path) -> None:
    write_key(tmp_path, {"a1": ("none", "python"), "b2": ("none", "go")})
    write_review(tmp_path, "a1", (6, 6, 6, 6), [])

    summary: dict[str, Any] = quality_review.summarize(tmp_path)

    assert summary["arms"]["none"]["reviews"] == 1.0
    assert summary["tasks"] == {"python": {"none": 6.0}}


def test_judge_prompt_asks_for_the_four_criteria_and_never_names_chef() -> None:
    prompt: str = quality_review.judge_prompt("python")

    assert all(f"`{criterion}`" in prompt for criterion in quality_review.CRITERIA)
    assert "slugify" in prompt
    assert "chef" not in prompt.lower()


def test_the_schema_requires_the_four_criteria_and_the_changes() -> None:
    assert quality_review.QUALITY_SCHEMA["required"] == [*quality_review.CRITERIA, "changes"]


def test_every_quality_task_matches_a_reference() -> None:
    references: Path = quality_review.QUALITY_DIR.parent.parent / "skills" / "chef" / "references"
    tasks: list[Path] = sorted(path for path in quality_review.QUALITY_DIR.iterdir() if path.is_dir())

    assert len(tasks) == 32
    assert [task.name for task in tasks if not (references / f"{task.name}.md").is_file()] == []
    assert all((task / "prompt.md").is_file() for task in tasks)
