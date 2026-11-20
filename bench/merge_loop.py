"""Cost to mergeable: review each first answer blind, send the required changes back, repeat.

Usage:
  python bench/merge_loop.py run <out-dir> <loop-dir> <arm>=<plugin-dir or empty> ...
  python bench/merge_loop.py summarize <loop-dir> ... > bench/results/merge.json

For every run of every listed arm, the workspace is copied into the loop dir. A blind reviewer
(a fresh `claude -p --restricted` session that sees an anonymized copy) lists the changes it
requires; a run is merged when none is a blocker or major. Otherwise the same setup that wrote the code
(plain Claude, the control's CLAUDE.md, or chef via --plugin-dir) gets those changes as a new
prompt in that workspace, then a fresh reviewer looks again, up to ROUND_LIMIT fix rounds.
The total cost of a run is the first answer plus every fix; reviewer costs are reported apart.
"""

import json
import shutil
import statistics
import subprocess
import sys
import tempfile
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from blind_review import BENCH_DIR, PARALLEL_JUDGES, copy_submission, read_review, reviewer_id, run_judge, submission_files
from score import refuse_failed_runs, run_failure, usage_metrics

ROUND_LIMIT: int = 2
MILLISECONDS_PER_SECOND: float = 1000.0
NUL_BYTE: bytes = bytes([0])
WORKER_MODEL: str = "claude-sonnet-5-5"
WORKER_BUDGET_USD: str = "1"
REQUIRED: tuple[str, ...] = ("blocker", "major")
FIX_TIMEOUT_SECONDS: int = 1800
GIT_TIMEOUT_SECONDS: int = 30
# Hashed into the reviewer id: change it whenever is_mergeable changes. The 1.2 loop also accepted merge_as_is.
MERGE_RULE: str = "merged when no " + "/".join(REQUIRED) + " change is listed"
SEAT: str = (
    "the whole review panel: a senior engineer (design and correctness), a security reviewer, an SRE who will run it, "
    "and the engineer who will maintain it."
)
FIX_PROMPT: str = (
    "A reviewer read your work in this folder and requires these changes before merging:\n\n{changes}\n\n"
    "Make them. Work autonomously: nobody will answer questions."
)


@dataclass(frozen=True)
class Sample:
    arm: str
    task: str
    run: str
    workspace: Path
    first_cost: float
    first_seconds: float


def required_changes(review: dict[str, Any]) -> list[str]:
    return [item["change"] for item in review["changes"] if item["severity"] in REQUIRED]


def is_mergeable(review: dict[str, Any]) -> bool:
    """The required changes decide, even when the reviewer also ticked merge_as_is."""
    return not required_changes(review)


def stream_number(stream_path: Path, key: str) -> float:
    value: float | int | bool | None = usage_metrics(stream_path)[key]
    return float(value) if isinstance(value, (int, float)) else 0.0


def stream_cost(stream_path: Path) -> float:
    return stream_number(stream_path, "cost_usd")


def harness_commit() -> str:
    """The bench commit that ran the loop, `-dirty` when it had local changes."""
    try:
        described: subprocess.CompletedProcess[str] = subprocess.run(
            ["git", "-C", str(BENCH_DIR), "describe", "--always", "--dirty"],
            capture_output=True,
            text=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return "unknown"
    return described.stdout.strip() if described.returncode == 0 else "unknown"


def review(sample: Sample, review_path: Path) -> dict[str, Any] | None:
    blind: Path = Path(tempfile.mkdtemp(prefix="review-")) / "submission"
    copy_submission(sample.workspace, blind)
    run_judge(blind, sample.task, SEAT, review_path)
    shutil.rmtree(blind.parent)
    return read_review(review_path)


def review_number(review_path: Path, key: str) -> float:
    """A number from the judge's result file, 0 when the judge crashed and left none."""
    text: str = review_path.read_text(encoding="utf-8") if review_path.is_file() else ""
    try:
        value: Any = json.loads(text).get(key) if text.strip() else None
    except json.JSONDecodeError:
        return 0.0
    return float(value) if isinstance(value, (int, float)) else 0.0


def review_cost(review_path: Path) -> float:
    return review_number(review_path, "total_cost_usd")


def lines_to_review(workspace: Path) -> int:
    """Lines of text a reviewer reads in the submission, the proxy for human review time."""
    total: int = 0
    for relative in submission_files(workspace):
        content: bytes = (workspace / relative).read_bytes()
        if NUL_BYTE not in content:
            total += content.count(b"\n")
    return total


def fix(sample: Sample, changes: list[str], plugin_dir: str, stream_path: Path) -> tuple[float, bool]:
    """The fix's cost and whether it timed out; a killed fix wrote no result event, so its spend reads as 0."""
    prompt: str = FIX_PROMPT.format(changes="\n".join(f"- {change}" for change in changes))
    plugin_args: list[str] = ["--plugin-dir", plugin_dir] if plugin_dir else []
    command: list[str] = [
        "claude", "-p", prompt,
        "--model", WORKER_MODEL,
        "--output-format", "stream-json", "--verbose",
        "--setting-sources", "project",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--dangerously-skip-permissions",
        "--max-budget-usd", WORKER_BUDGET_USD,
        *plugin_args,
    ]  # fmt: skip
    with stream_path.open("w", encoding="utf-8") as stream_file:
        try:
            subprocess.run(
                command,
                cwd=sample.workspace,
                stdin=subprocess.DEVNULL,
                stdout=stream_file,
                check=False,
                timeout=FIX_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            # The killed fix wrote no result event, so loop records it as a fix that gave no answer.
            print(f"merge_loop: the fix in {sample.workspace} timed out after {FIX_TIMEOUT_SECONDS} s", file=sys.stderr)
            return stream_cost(stream_path), True
    return stream_cost(stream_path), False


def new_record(sample: Sample) -> dict[str, Any]:
    return {
        "arm": sample.arm,
        "task": sample.task,
        "run": sample.run,
        "harness": harness_commit(),
        "reviewer": reviewer_id(SEAT, MERGE_RULE),
        "first_cost": sample.first_cost,
        "first_seconds": sample.first_seconds,
        "lines_to_review": lines_to_review(sample.workspace),
        "review_seconds": [],
        "fix_seconds": [],
    }


def loop(sample: Sample, plugin_dir: str, record_dir: Path) -> dict[str, Any]:
    """Review, fix, review again; returns the record of the sample's rounds."""
    record: dict[str, Any] = new_record(sample)
    fix_costs: list[float] = []
    reviewer_costs: list[float] = []
    for round_index in range(ROUND_LIMIT + 1):
        review_path: Path = record_dir / f"review-{round_index}.json"
        verdict: dict[str, Any] | None = review(sample, review_path)
        reviewer_costs.append(review_cost(review_path))
        record["review_seconds"].append(review_number(review_path, "duration_ms") / MILLISECONDS_PER_SECOND)
        if verdict is None:
            record["error"] = f"no readable review in round {round_index}"
            break
        record[f"required_{round_index}"] = len(required_changes(verdict))
        if is_mergeable(verdict):
            record["merged_after_fixes"] = round_index
            break
        if round_index == ROUND_LIMIT:
            break
        fix_stream: Path = record_dir / f"fix-{round_index + 1}.jsonl"
        fix_cost, timed_out = fix(sample, required_changes(verdict), plugin_dir, fix_stream)
        fix_costs.append(fix_cost)
        if timed_out:
            record["fix_timed_out"] = True
        record["fix_seconds"].append(stream_number(fix_stream, "seconds"))
        failure: str | None = run_failure(fix_stream)
        if failure is not None:
            record["error"] = f"fix {round_index + 1} gave no answer: {failure}"
            break
    record["fix_costs"] = fix_costs
    record["reviewer_cost"] = round(sum(reviewer_costs), 4)
    record["total_cost"] = round(sample.first_cost + sum(fix_costs), 4)
    (record_dir / "record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def run_dirs_of(out_dir: Path, arm: str) -> list[Path]:
    return sorted(path for path in out_dir.glob(f"{arm}/*/*") if (path / "workspace").is_dir())


def collect_samples(out_dir: Path, loop_dir: Path, arm: str) -> list[Sample]:
    samples: list[Sample] = []
    for run_dir in run_dirs_of(out_dir, arm):
        task: str = run_dir.parent.name
        copy: Path = loop_dir / arm / task / run_dir.name / "workspace"
        shutil.copytree(run_dir / "workspace", copy)
        stream: Path = run_dir / "stream.jsonl"
        samples.append(Sample(arm, task, run_dir.name, copy, stream_cost(stream), stream_number(stream, "seconds")))
    return samples


def run_all(out_dir: Path, loop_dir: Path, arm_sources: dict[str, str]) -> None:
    if loop_dir.exists():
        raise SystemExit(f"merge_loop: {loop_dir} exists, use a new loop dir")
    refuse_failed_runs([run_dir for arm in arm_sources for run_dir in run_dirs_of(out_dir, arm)], "merge_loop")
    jobs: list[tuple[Sample, str]] = [
        (sample, source) for arm, source in arm_sources.items() for sample in collect_samples(out_dir, loop_dir, arm)
    ]
    with ThreadPoolExecutor(max_workers=PARALLEL_JUDGES) as pool:
        futures: dict[Future[dict[str, Any]], Sample] = {
            pool.submit(loop, sample, source, sample.workspace.parent): sample for sample, source in jobs
        }
        for future in as_completed(futures):
            error: BaseException | None = future.exception()
            if error is not None:
                sample: Sample = futures[future]
                print(f"merge_loop: {sample.arm}/{sample.task}/{sample.run} failed: {error}", file=sys.stderr)


def arm_summary(records: list[dict[str, Any]]) -> dict[str, float]:
    merged: list[dict[str, Any]] = [record for record in records if "merged_after_fixes" in record]
    return {
        "runs": float(len(records)),
        "merged_first_time": round(sum(1 for record in merged if record["merged_after_fixes"] == 0) / len(records), 3),
        "merged_in_the_end": round(len(merged) / len(records), 3),
        "fix_rounds_per_run": round(statistics.fmean(len(record["fix_costs"]) for record in records), 2),
        "first_answer_cost": round(sum(record["first_cost"] for record in records), 2),
        "total_cost": round(sum(record["total_cost"] for record in records), 2),
        "cost_per_merged_run": round(sum(record["total_cost"] for record in records) / len(merged), 3) if merged else 0.0,
        "reviewer_cost": round(sum(record.get("reviewer_cost", 0.0) for record in records), 2),
        "lines_to_review": round(statistics.median(record.get("lines_to_review", 0) for record in records)),
        "first_answer_seconds": round(statistics.fmean(record["first_seconds"] for record in records), 1),
        "first_review_seconds": round(statistics.fmean(record["review_seconds"][0] for record in records), 1),
        "back_and_forth_seconds": round(
            statistics.fmean(sum(record["fix_seconds"]) + sum(record["review_seconds"][1:]) for record in records), 1
        ),
    }


def sample_name(record: dict[str, Any]) -> str:
    return f"{record['arm']}/{record['task']}/{record['run']}"


def load_records(loop_dirs: list[Path]) -> list[dict[str, Any]]:
    """Every record of the loop dirs; refuses none, duplicates and unfinished ones."""
    paths: list[Path] = sorted(path for loop_dir in loop_dirs for path in loop_dir.glob("*/*/*/record.json"))
    records: list[dict[str, Any]] = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    if not records:
        raise SystemExit(f"merge_loop: no record in {', '.join(map(str, loop_dirs))}")
    names: list[str] = [sample_name(record) for record in records]
    duplicates: list[str] = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise SystemExit("merge_loop: samples present in more than one loop dir:\n" + "\n".join(duplicates))
    unfinished: list[str] = [f"{sample_name(record)}: {record['error']}" for record in records if "error" in record]
    if unfinished:
        raise SystemExit("merge_loop: unfinished records, run the loop again in a new loop dir:\n" + "\n".join(unfinished))
    return records


def summarize(loop_dirs: list[Path]) -> dict[str, Any]:
    """The results/merge.json content: one summary per arm, and where the records come from."""
    records: list[dict[str, Any]] = load_records(loop_dirs)
    reviewers: list[str] = sorted({record["reviewer"] for record in records})
    if len(reviewers) > 1:
        raise SystemExit(f"merge_loop: records from different reviewers are not comparable: {', '.join(reviewers)}")
    by_arm: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_arm.setdefault(record["arm"], []).append(record)
    return {
        "provenance": {"reviewer": reviewers[0], "harness": sorted({record["harness"] for record in records})},
        "arms": {arm: arm_summary(arm_records) for arm, arm_records in sorted(by_arm.items())},
    }


def main(arguments: list[str]) -> None:
    if arguments[0] == "summarize":
        print(json.dumps(summarize([Path(argument) for argument in arguments[1:]]), indent=2))
        return
    arm_sources: dict[str, str] = dict(argument.split("=", 1) for argument in arguments[3:])
    run_all(Path(arguments[1]), Path(arguments[2]), arm_sources)


if __name__ == "__main__":
    main(sys.argv[1:])
