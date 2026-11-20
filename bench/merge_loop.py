"""Cost to mergeable: review each first answer blind, send the required changes back, repeat.

Usage:
  python bench/merge_loop.py run <out-dir> <loop-dir> <arm>=<plugin-dir or empty> ...
  python bench/merge_loop.py summarize <loop-dir>

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

from blind_review import PARALLEL_JUDGES, copy_submission, read_review, run_judge, submission_files
from score import refuse_failed_runs, run_failure, usage_metrics

ROUND_LIMIT: int = 2
NUL_BYTE: bytes = bytes([0])
WORKER_MODEL: str = "claude-sonnet-5-5"
WORKER_BUDGET_USD: str = "1"
REQUIRED: tuple[str, ...] = ("blocker", "major")
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


def required_changes(review: dict[str, Any]) -> list[str]:
    return [item["change"] for item in review["changes"] if item["severity"] in REQUIRED]


def is_mergeable(review: dict[str, Any]) -> bool:
    """The required changes decide, even when the reviewer also ticked merge_as_is."""
    return not required_changes(review)


def stream_cost(stream_path: Path) -> float:
    cost: float | int | bool | None = usage_metrics(stream_path)["cost_usd"]
    return float(cost) if isinstance(cost, (int, float)) else 0.0


def review(sample: Sample, review_path: Path) -> dict[str, Any] | None:
    blind: Path = Path(tempfile.mkdtemp(prefix="review-")) / "submission"
    copy_submission(sample.workspace, blind)
    run_judge(blind, sample.task, SEAT, review_path)
    shutil.rmtree(blind.parent)
    return read_review(review_path)


def review_cost(review_path: Path) -> float:
    text: str = review_path.read_text(encoding="utf-8") if review_path.is_file() else ""
    try:
        cost: Any = json.loads(text).get("total_cost_usd") if text.strip() else None
    except json.JSONDecodeError:
        return 0.0
    return float(cost) if isinstance(cost, (int, float)) else 0.0


def lines_to_review(workspace: Path) -> int:
    """Lines of text a reviewer reads in the submission, the proxy for human review time."""
    total: int = 0
    for relative in submission_files(workspace):
        content: bytes = (workspace / relative).read_bytes()
        if NUL_BYTE not in content:
            total += content.count(b"\n")
    return total


def fix(sample: Sample, changes: list[str], plugin_dir: str, stream_path: Path) -> float:
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
        subprocess.run(command, cwd=sample.workspace, stdin=subprocess.DEVNULL, stdout=stream_file, check=False)
    return stream_cost(stream_path)


def loop(sample: Sample, plugin_dir: str, record_dir: Path) -> dict[str, Any]:
    """Review, fix, review again; returns the record of the sample's rounds."""
    record: dict[str, Any] = {"arm": sample.arm, "task": sample.task, "run": sample.run, "first_cost": sample.first_cost}
    record["lines_to_review"] = lines_to_review(sample.workspace)
    fix_costs: list[float] = []
    reviewer_costs: list[float] = []
    for round_index in range(ROUND_LIMIT + 1):
        verdict: dict[str, Any] | None = review(sample, record_dir / f"review-{round_index}.json")
        reviewer_costs.append(review_cost(record_dir / f"review-{round_index}.json"))
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
        fix_costs.append(fix(sample, required_changes(verdict), plugin_dir, fix_stream))
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
        samples.append(Sample(arm, task, run_dir.name, copy, stream_cost(run_dir / "stream.jsonl")))
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
    }


def summarize(loop_dir: Path) -> dict[str, dict[str, float]]:
    by_arm: dict[str, list[dict[str, Any]]] = {}
    for record_path in sorted(loop_dir.glob("*/*/*/record.json")):
        record: dict[str, Any] = json.loads(record_path.read_text(encoding="utf-8"))
        by_arm.setdefault(record["arm"], []).append(record)
    if not by_arm:
        raise SystemExit(f"merge_loop: no record in {loop_dir}")
    unfinished: list[str] = [
        f"{record['arm']}/{record['task']}/{record['run']}: {record['error']}"
        for records in by_arm.values()
        for record in records
        if "error" in record
    ]
    if unfinished:
        raise SystemExit("merge_loop: unfinished records, run the loop again in a new loop dir:\n" + "\n".join(unfinished))
    return {arm: arm_summary(records) for arm, records in sorted(by_arm.items())}


def main(arguments: list[str]) -> None:
    if arguments[0] == "summarize":
        print(json.dumps(summarize(Path(arguments[1])), indent=2))
        return
    arm_sources: dict[str, str] = dict(argument.split("=", 1) for argument in arguments[3:])
    run_all(Path(arguments[1]), Path(arguments[2]), arm_sources)


if __name__ == "__main__":
    main(sys.argv[1:])
