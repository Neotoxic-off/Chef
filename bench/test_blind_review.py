import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

import blind_review

FINISHED_RESULT: str = json.dumps({"type": "result", "subtype": "success", "terminal_reason": "completed"})


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
    (workspace.parent / "stream.jsonl").write_text(FINISHED_RESULT, encoding="utf-8")

    key: dict[str, dict[str, str]] = blind_review.anonymize(tmp_path / "out", ["none"])

    origin: dict[str, str] = next(iter(key.values()))
    assert sorted(path.name for path in Path(origin["submission"]).iterdir()) == ["endpoints.py"]
    assert (origin["arm"], origin["task"], origin["run"]) == ("none", "python", "1")


def test_anonymize_refuses_a_run_that_gave_no_answer(tmp_path: Path) -> None:
    (tmp_path / "out" / "none" / "python" / "1" / "workspace").mkdir(parents=True)

    with pytest.raises(SystemExit, match="blind_review: these runs gave no answer"):
        blind_review.anonymize(tmp_path / "out", ["none"])


def test_reviewer_id_is_stable_and_changes_with_the_seat_or_the_merge_rule() -> None:
    first: str = blind_review.reviewer_id("senior", "rule")

    assert blind_review.reviewer_id("senior", "rule") == first
    assert blind_review.reviewer_id("security", "rule") != first
    assert blind_review.reviewer_id("senior", "other rule") != first
    assert len(first) == blind_review.REVIEWER_ID_LENGTH


def test_judge_prompt_names_the_seat_and_the_task_only() -> None:
    prompt: str = blind_review.judge_prompt("docker", blind_review.ROLES["security"])

    assert blind_review.ROLES["security"] in prompt
    assert "Dockerfile" in prompt
    assert "chef" not in prompt.lower()


def test_judge_prompt_reads_the_task_from_another_task_set(tmp_path: Path) -> None:
    (tmp_path / "slug").mkdir()
    (tmp_path / "slug" / "prompt.md").write_text("Write a slug function.\n", encoding="utf-8")

    prompt: str = blind_review.judge_prompt("slug", "a reviewer", tmp_path)

    assert "Write a slug function." in prompt


def test_copy_submission_leaves_out_gitignored_build_output(tmp_path: Path) -> None:
    workspace: Path = tmp_path / "workspace"
    for name, text in (
        (".gitignore", "node_modules/\ndist/\n"),
        ("src/app.ts", "x"),
        ("node_modules/a/index.js", "x"),
        ("dist/app.js", "x"),
    ):
        (workspace / name).parent.mkdir(parents=True, exist_ok=True)
        (workspace / name).write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(workspace)], check=True)

    blind_review.copy_submission(workspace, tmp_path / "copy")

    assert sorted(
        path.relative_to(tmp_path / "copy").as_posix() for path in (tmp_path / "copy").rglob("*") if path.is_file()
    ) == [
        ".gitignore",
        "src/app.ts",
    ]
