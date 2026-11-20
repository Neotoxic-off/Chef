import json
from pathlib import Path
from typing import Any

import pytest

import score


def test_summarize_uses_keys_from_every_run() -> None:
    runs: list[score.Metrics] = [{"container_healthy": False}, {"container_healthy": True, "non_root_user": True}]

    summary: score.Metrics = score.summarize(runs)

    assert summary == {"container_healthy": 0.5, "non_root_user": 1.0}


def test_summarize_skips_missing_values() -> None:
    runs: list[score.Metrics] = [{"cost_usd": None}, {"cost_usd": 0.4}]

    assert score.summarize(runs) == {"cost_usd": 0.4, "cost_usd_min": 0.4, "cost_usd_max": 0.4}


def test_summarize_reports_pass_rate_for_checks() -> None:
    runs: list[score.Metrics] = [{"completed": True}, {"completed": False}, {"completed": False}]

    assert score.summarize(runs) == {"completed": 0.333}


def test_summarize_reports_median_not_mean() -> None:
    runs: list[score.Metrics] = [{"turns": 4}, {"turns": 5}, {"turns": 30}]

    assert score.summarize(runs)["turns"] == 5


def test_last_user_is_not_root_with_app_user_returns_true() -> None:
    assert score.last_user_is_not_root(["FROM python:3.13-slim", "USER root", "USER app"])


def test_last_user_is_not_root_without_user_returns_false() -> None:
    assert not score.last_user_is_not_root(["FROM python:3.13-slim"])


def test_last_user_is_not_root_with_uid_zero_returns_false() -> None:
    assert not score.last_user_is_not_root(["USER app", "USER 0"])


def test_service_is_hardened_with_read_only_and_no_new_privileges_returns_true() -> None:
    service: dict[str, Any] = {"read_only": True, "security_opt": ["no-new-privileges:true"]}

    assert score.service_is_hardened(service)


def test_service_is_hardened_without_read_only_returns_false() -> None:
    assert not score.service_is_hardened({"cap_drop": ["ALL"]})


def test_alert_rules_ignores_rule_test_files_and_bad_groups() -> None:
    rules_file: dict[str, Any] = {"groups": ["not a group", {"rules": [{"alert": "Down"}, {"record": "job:up:sum"}]}]}
    test_file: dict[str, Any] = {"tests": [], "groups": [{"rules": [{"alert": "Ignored"}]}]}

    alerts: list[dict[str, Any]] = score.alert_rules([(Path("a.yml"), rules_file), (Path("b.yml"), test_file)])

    assert alerts == [{"alert": "Down"}]


def test_usage_metrics_without_result_event_marks_run_incomplete(tmp_path: Path) -> None:
    stream_path: Path = tmp_path / "stream.jsonl"
    stream_path.write_text('{"type": "system"}\ncrash', encoding="utf-8")

    metrics: score.Metrics = score.usage_metrics(stream_path)

    assert metrics["completed"] is False
    assert metrics["cost_usd"] is None


USAGE_LIMIT_RESULT: str = json.dumps(
    {"type": "result", "subtype": "success", "is_error": True, "terminal_reason": "api_error", "api_error": "usage_limit_reached"}
)
FINISHED_RESULT: str = json.dumps({"type": "result", "subtype": "success", "is_error": False, "terminal_reason": "completed"})


def write_run(run_dir: Path, last_line: str) -> Path:
    run_dir.mkdir(parents=True)
    (run_dir / "stream.jsonl").write_text('{"type": "system"}\n' + last_line + "\n", encoding="utf-8")
    return run_dir


def test_run_failure_of_a_usage_limited_run_names_the_api_error(tmp_path: Path) -> None:
    run_dir: Path = write_run(tmp_path / "1", USAGE_LIMIT_RESULT)

    assert score.run_failure(run_dir / "stream.jsonl") == "API error: usage_limit_reached"


def test_run_failure_without_result_event_says_so(tmp_path: Path) -> None:
    run_dir: Path = write_run(tmp_path / "1", "crash")

    assert score.run_failure(run_dir / "stream.jsonl") == "no result event"


def test_run_failure_without_stream_file_says_no_result_event(tmp_path: Path) -> None:
    assert score.run_failure(tmp_path / "stream.jsonl") == "no result event"


def test_run_failure_of_an_error_that_is_not_an_api_error_is_none(tmp_path: Path) -> None:
    capped: str = json.dumps({"type": "result", "subtype": "error_max_budget_usd", "is_error": True})
    run_dir: Path = write_run(tmp_path / "1", capped)

    assert score.run_failure(run_dir / "stream.jsonl") is None


def test_run_failure_of_a_finished_run_is_none(tmp_path: Path) -> None:
    run_dir: Path = write_run(tmp_path / "1", FINISHED_RESULT)

    assert score.run_failure(run_dir / "stream.jsonl") is None


def test_check_exits_and_lists_only_the_failed_runs(tmp_path: Path) -> None:
    finished: Path = write_run(tmp_path / "ok", FINISHED_RESULT)
    limited: Path = write_run(tmp_path / "limited", USAGE_LIMIT_RESULT)

    with pytest.raises(SystemExit) as stopped:
        score.check([finished, limited])

    assert str(stopped.value) == f"{limited}: API error: usage_limit_reached"


def test_main_refuses_to_score_an_out_dir_with_a_failed_run(tmp_path: Path) -> None:
    run_dir: Path = write_run(tmp_path / "chef" / "go" / "1", USAGE_LIMIT_RESULT)
    (run_dir / "workspace").mkdir()

    with pytest.raises(SystemExit, match="score: these runs gave no answer"):
        score.main(tmp_path)


def test_usage_metrics_splits_tokens_and_counts_tool_traffic(tmp_path: Path) -> None:
    assistant: dict[str, Any] = {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": "hi"}, {"type": "tool_use", "name": "Read"}]},
    }
    tool_result: dict[str, Any] = {"type": "user", "message": {"content": [{"type": "tool_result", "content": "abc"}]}}
    result: dict[str, Any] = {
        "type": "result",
        "subtype": "success",
        "total_cost_usd": 0.3,
        "duration_ms": 2000,
        "num_turns": 4,
        "modelUsage": {
            "sonnet": {"inputTokens": 10, "cacheReadInputTokens": 100, "cacheCreationInputTokens": 5, "outputTokens": 7},
            "haiku": {"inputTokens": 1, "outputTokens": 2},
        },
    }
    stream_path: Path = tmp_path / "stream.jsonl"
    stream_path.write_text("\n".join(json.dumps(event) for event in (assistant, tool_result, result)), encoding="utf-8")

    metrics: score.Metrics = score.usage_metrics(stream_path)

    assert metrics == {
        "cost_usd": 0.3,
        "seconds": 2.0,
        "turns": 4,
        "input_tokens": 11,
        "cache_write_tokens": 5,
        "cache_read_tokens": 100,
        "output_tokens": 9,
        "tool_calls": 1,
        "tool_result_chars": len(json.dumps("abc", ensure_ascii=False)),
        "completed": True,
    }


def test_is_test_file_detects_tests_folder() -> None:
    assert score.is_test_file(Path("tests/check_config.py"))
    assert not score.is_test_file(Path("endpoints.py"))
