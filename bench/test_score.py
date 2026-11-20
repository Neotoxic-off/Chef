import json
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import score
import scorer_lib


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


def test_score_run_records_a_checker_timeout_as_not_scored(tmp_path: Path) -> None:
    run_dir: Path = write_run(tmp_path / "1", FINISHED_RESULT)

    def hanging_scorer(_workspace: Path) -> score.Metrics:
        raise subprocess.TimeoutExpired(["pytest"], score.COMMAND_TIMEOUT_SECONDS)

    metrics: score.Metrics = score.score_run(run_dir, hanging_scorer)

    assert metrics["scored"] is False
    assert "hidden_test_passes" not in metrics


def test_score_run_records_a_scratch_dir_locked_by_a_timeout_as_not_scored(tmp_path: Path) -> None:
    run_dir: Path = write_run(tmp_path / "1", FINISHED_RESULT)

    def locked_scorer(_workspace: Path) -> score.Metrics:
        try:
            raise subprocess.TimeoutExpired(["npx"], score.COMMAND_TIMEOUT_SECONDS)
        finally:
            raise PermissionError(13, "in use", "scratch")

    assert score.score_run(run_dir, locked_scorer)["scored"] is False


def test_score_run_raises_a_permission_error_without_a_timeout(tmp_path: Path) -> None:
    run_dir: Path = write_run(tmp_path / "1", FINISHED_RESULT)

    def denied_scorer(_workspace: Path) -> score.Metrics:
        raise PermissionError(13, "denied", "workspace")

    with pytest.raises(PermissionError):
        score.score_run(run_dir, denied_scorer)


def test_run_kills_a_grandchild_holding_the_pipes_on_timeout(tmp_path: Path) -> None:
    sleeper: str = "import time; time.sleep(60)"
    spawner: str = f"import subprocess, sys; subprocess.run([sys.executable, '-c', {sleeper!r}])"
    started: float = time.monotonic()

    with pytest.raises(subprocess.TimeoutExpired):
        score.run([sys.executable, "-c", spawner], tmp_path, timeout=2)

    assert time.monotonic() - started < 30


def test_run_tool_refuses_a_missing_python_module(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="bench_no_such_linter is not installed"):
        score.run_tool([sys.executable, "-m", "bench_no_such_linter", "check", "."], tmp_path)


def recording_run(commands: list[list[str]]) -> Callable[..., subprocess.CompletedProcess[str]]:
    """A stand-in for score.run that records each command; `docker build` times out when asked to."""

    def fake_run(command: list[str], _cwd: Path, _stdin: str | None = None, timeout: int = 0) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[1] == "build" and timeout < 0:
            raise subprocess.TimeoutExpired(command, timeout)
        return subprocess.CompletedProcess(command, 0, "container-id\n", "")

    return fake_run


def test_container_serves_health_removes_its_container_and_image(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(score, "run", recording_run(commands))
    monkeypatch.setattr(score, "wait_for_health", lambda: True)

    assert score.container_serves_health(tmp_path, "bench-tag")
    assert commands[-2:] == [["docker", "rm", "-f", "container-id"], ["docker", "rmi", "-f", "bench-tag"]]


def test_container_serves_health_removes_its_image_when_the_build_times_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(score, "run", recording_run(commands))
    monkeypatch.setattr(score, "BUILD_TIMEOUT_SECONDS", -1)

    with pytest.raises(subprocess.TimeoutExpired):
        score.container_serves_health(tmp_path, "bench-tag")
    assert commands[-1] == ["docker", "rmi", "-f", "bench-tag"]


def write_costed_run(run_dir: Path, cost: float) -> None:
    write_run(run_dir, json.dumps({"type": "result", "terminal_reason": "completed", "total_cost_usd": cost}))


def test_budget_exits_once_the_runs_cost_the_cap(tmp_path: Path) -> None:
    write_costed_run(tmp_path / "none" / "go" / "1", 0.6)
    write_costed_run(tmp_path / "chef" / "go" / "1", 0.4)

    with pytest.raises(SystemExit, match=r"cost \$1\.00, the cap is \$1\.00"):
        score.budget(tmp_path, 1.0)


def test_budget_below_the_cap_ignores_runs_without_a_cost(tmp_path: Path) -> None:
    write_costed_run(tmp_path / "none" / "go" / "1", 0.6)
    write_run(tmp_path / "none" / "go" / "2", "crash")

    score.budget(tmp_path, 1.0)


def test_docker_run_removes_its_named_container_on_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def hanging_docker(
        command: list[str], _cwd: Path, _stdin: str | None = None, timeout: int = 0
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[1] == "run":
            raise subprocess.TimeoutExpired(command, timeout)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(scorer_lib, "run", hanging_docker)

    with pytest.raises(subprocess.TimeoutExpired):
        scorer_lib.docker_run(["alpine", "sleep", "999"], tmp_path)

    name: str = commands[0][commands[0].index("--name") + 1]
    assert commands[1] == ["docker", "rm", "-f", name]


def test_docker_run_raises_when_docker_cannot_run_the_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_command(command: list[str], *_arguments: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 127, "", "exec: not found")

    monkeypatch.setattr(scorer_lib, "run", missing_command)

    with pytest.raises(RuntimeError, match="exit code 127"):
        scorer_lib.docker_run(["alpine", "nope"], tmp_path)


@pytest.mark.parametrize("compile_commands", [None, "[]"])
def test_cppcheck_finds_nothing_without_compile_commands(
    compile_commands: str | None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_docker(*_arguments: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("cppcheck should not run")

    monkeypatch.setattr(scorer_lib, "in_gcc_toolchain", no_docker)
    if compile_commands is not None:
        (tmp_path / scorer_lib.CMAKE_BUILD_DIR).mkdir()
        (tmp_path / scorer_lib.CMAKE_BUILD_DIR / "compile_commands.json").write_text(compile_commands, encoding="utf-8")

    assert scorer_lib.cppcheck_findings(tmp_path) == 0


def test_source_files_match_name_suffixes_outside_ignored_directories(tmp_path: Path) -> None:
    for name in ("DotEnv.Tests.ps1", "DotEnv.ps1", ".git/hooks/x.Tests.ps1"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("", encoding="utf-8")

    assert scorer_lib.source_files(tmp_path, (".Tests.ps1",), (".git",)) == [Path("DotEnv.Tests.ps1")]
