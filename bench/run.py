"""Benchmark Claude Code with and without the chef plugin.

Three arms per task, each a headless `claude -p` session in a fresh temp folder:
  without  vanilla Claude Code
  control  vanilla + one line asking for production-quality code
  with     chef loaded from this repo (--plugin-dir)
Every installed plugin is disabled in all arms, so chef is the only difference.
Transcripts, test output and the produced files go to bench/logs/ (gitignored).

Usage:
    python bench/run.py run --runs 3 --model sonnet
    python bench/run.py report
    python bench/run.py selftest
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import mean, stdev
from threading import Lock
from typing import Any

BENCH_DIR: Path = Path(__file__).resolve().parent
REPO_DIR: Path = BENCH_DIR.parent
RESULTS: Path = BENCH_DIR / "results.jsonl"
PARTIAL: Path = BENCH_DIR / "results.partial.jsonl"
REPORT: Path = BENCH_DIR / "results.md"
LOGS: Path = BENCH_DIR / "logs"
USER_SETTINGS: Path = Path.home() / ".claude" / "settings.json"
ARMS: tuple[str, ...] = ("without", "control", "with")
CONTROL_SUFFIX: str = (
    " Write production-quality code: unit tests, strict lint and type-checking configuration,"
    " explicit types, and no hidden warnings."
)
RUN_TIMEOUT_S: int = 1500
TEST_TIMEOUT_S: int = 600
CODE_TASKS: set[str] = {"csharp", "typescript", "python"}
SOURCE_EXT: dict[str, str] = {".cs": "//", ".ts": "//", ".js": "//", ".py": "#"}
SKIP_DIRS: set[str] = {
    "node_modules", "bin", "obj", ".venv", "dist", ".git", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "coverage",
}
NPM_DEFAULT_TEST: str = "no test specified"
WRITE_LOCK: Lock = Lock()
ALLOWED_TOOLS: list[str] = [
    "Read", "Write", "Edit", "Glob", "Grep", "Agent", "Skill", "TodoWrite", "WebSearch", "WebFetch",
    "Bash(dotnet *)", "Bash(npm *)", "Bash(npx *)", "Bash(node *)", "Bash(python *)", "Bash(uv *)",
    "Bash(pip *)", "Bash(ls *)", "Bash(mkdir *)", "Bash(cat *)",
    "Bash(docker buildx imagetools *)", "Bash(docker manifest inspect *)", "Bash(git ls-remote *)", "Bash(gh api *)",
]


def settings_all_plugins_off() -> dict[str, Any]:
    user: dict[str, Any] = json.loads(USER_SETTINGS.read_text(encoding="utf-8"))
    return {"enabledPlugins": {plugin_id: False for plugin_id in user.get("enabledPlugins", {})}}


def is_test_file(path: Path) -> bool:
    name: str = path.name.lower()
    return "test" in name or "spec" in name or any("test" in part.lower() for part in path.parts[:-1])


def source_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file() and not SKIP_DIRS.intersection(p.relative_to(root).parts)]


def code_and_comment_lines(files: list[Path]) -> tuple[int, int]:
    code: int = 0
    comments: int = 0
    for f in files:
        marker: str | None = SOURCE_EXT.get(f.suffix)
        if marker is None or is_test_file(f):
            continue
        in_block: bool = False
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped: str = line.strip()
            if not stripped:
                continue
            delimiter: str = '"""' if f.suffix == ".py" else "/*"
            closer: str = '"""' if f.suffix == ".py" else "*/"
            if in_block:
                comments += 1
                in_block = closer not in stripped
            elif stripped.startswith(delimiter):
                comments += 1
                rest: str = stripped[len(delimiter):]
                in_block = closer not in rest
            elif stripped.startswith(marker):
                comments += 1
            else:
                code += 1
    return code, comments


def count(pattern: str, files: list[Path], suffixes: tuple[str, ...]) -> int:
    regex: re.Pattern[str] = re.compile(pattern, re.MULTILINE)
    return sum(len(regex.findall(f.read_text(encoding="utf-8", errors="replace"))) for f in files if f.suffix in suffixes)


def python_annotation_ratio(files: list[Path]) -> float | None:
    total: int = 0
    typed: int = 0
    for f in files:
        if f.suffix != ".py":
            continue
        try:  # agent output may not parse; that is a result, not a crash
            tree: ast.Module = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args: list[ast.arg] = [a for a in node.args.args + node.args.kwonlyargs if a.arg not in ("self", "cls")]
                total += 1
                typed += int(node.returns is not None and all(a.annotation is not None for a in args))
    return round(typed / total, 2) if total else None


def npm_has_tests(root: Path) -> bool:
    try:  # agent output may be invalid JSON; then let npm run and fail
        package: dict[str, Any] = json.loads((root / "package.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return True
    script: str = package.get("scripts", {}).get("test", "")
    return bool(script) and NPM_DEFAULT_TEST not in script


def test_commands(task_id: str, root: Path) -> list[list[str]]:
    if task_id == "csharp":
        return [["dotnet", "test", str(p)] for p in root.rglob("*.csproj") if "test" in p.name.lower()]
    if task_id == "typescript" and (root / "package.json").exists() and npm_has_tests(root):
        return [["npm", "install", "--silent"], ["npm", "test", "--silent"]]
    if task_id == "python" and any(p.suffix == ".py" and is_test_file(p) for p in source_files(root)):
        return [["uv", "run", "--with", "pytest", "python", "-m", "pytest", "-q"]]
    return []


def run_tests(task_id: str, root: Path, log: Path) -> bool | None:
    commands: list[list[str]] = test_commands(task_id, root)
    if not commands:
        return None
    with log.open("w", encoding="utf-8") as out:
        for cmd in commands:
            out.write(f"$ {' '.join(cmd)}\n")
            try:  # subprocess.run has no non-raising timeout
                result: subprocess.CompletedProcess[str] = subprocess.run(
                    cmd, cwd=root, capture_output=True, text=True, timeout=TEST_TIMEOUT_S, shell=sys.platform == "win32")
            except subprocess.TimeoutExpired:
                out.write("TIMEOUT\n")
                return False
            out.write(result.stdout + result.stderr + f"\n[exit {result.returncode}]\n")
            if result.returncode != 0:
                return False
    return True


def score(task_id: str, root: Path, test_log: Path) -> dict[str, Any]:
    files: list[Path] = source_files(root)
    text_of: dict[str, str] = {f.relative_to(root).as_posix(): f.read_text(encoding="utf-8", errors="replace") for f in files}
    joined: str = "\n".join(text_of.values())
    m: dict[str, Any] = {}
    if task_id in CODE_TASKS:
        code, comments = code_and_comment_lines(files)
        m["code_lines"] = code
        m["comment_ratio"] = round(comments / code, 2) if code else 0.0
        m["try_blocks"] = count(r"\btry\s*[{:]", [f for f in files if not is_test_file(f)], (".cs", ".ts", ".js", ".py"))
        m["test_cases"] = count(r"\[(Fact|Theory)\]|\b(it|test)\(\s*['\"`]|^\s*def test_", files, (".cs", ".ts", ".js", ".py"))
    if task_id == "csharp":
        m["inferred_var"] = count(r"\bvar\s+\w+\s*=", files, (".cs",))
        m["warnings_as_errors"] = "TreatWarningsAsErrors>true" in joined
        m["nullable"] = "<Nullable>enable" in joined
    elif task_id == "typescript":
        m["any_usages"] = count(r":\s*any\b|\bas any\b", files, (".ts",))
        m["untyped_decls"] = count(r"\b(const|let)\s+\w+\s*=", files, (".ts",))
        m["strict_tsconfig"] = bool(re.search(r'"strict"\s*:\s*true', text_of.get("tsconfig.json", "")))
        m["eslint"] = any(Path(n).name.startswith(("eslint.config", ".eslintrc")) for n in text_of)
    elif task_id == "python":
        m["annotated_functions"] = python_annotation_ratio(files)
        m["strict_types_config"] = bool(re.search(r"strict\s*=\s*true|typeCheckingMode\s*=\s*\"strict\"", joined))
        m["ruff"] = "[tool.ruff" in joined
    elif task_id == "devops":
        dockerfile: str = text_of.get("Dockerfile", "")
        workflows: str = "\n".join(t for n, t in text_of.items() if n.endswith((".yml", ".yaml")))
        uses: list[str] = re.findall(r"uses:\s*\S+@(\S+)", workflows)
        m["multi_stage"] = dockerfile.count("FROM ") >= 2
        m["non_root_user"] = bool(re.search(r"^USER\s+(?!root\b)\S+", dockerfile, re.MULTILINE))
        m["base_pinned_digest"] = "@sha256:" in dockerfile
        m["healthcheck"] = "HEALTHCHECK" in dockerfile
        m["dockerignore"] = ".dockerignore" in text_of
        m["actions_pinned_sha"] = round(sum(bool(re.fullmatch(r"[0-9a-f]{40}", u)) for u in uses) / len(uses), 2) if uses else 0.0
        m["permissions_block"] = "permissions:" in workflows
    m["tests_pass"] = run_tests(task_id, root, test_log)
    return m


def parse_stream(stdout: str) -> tuple[dict[str, Any], list[str], str | None]:
    """Return the final result event, the reference files read, and the resolved model."""
    result: dict[str, Any] = {}
    refs: list[str] = []
    model: str | None = None
    for line in stdout.splitlines():
        if not line.startswith("{"):
            continue
        event: dict[str, Any] = json.loads(line)
        if event.get("type") == "system" and event.get("subtype") == "init":
            model = event.get("model")
        elif event.get("type") == "result":
            result = event
        elif event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                path: str = str(block.get("input", {}).get("file_path", "")) if block.get("type") == "tool_use" else ""
                if block.get("name") == "Read" and "references" in path.replace("\\", "/"):
                    refs.append(Path(path).name)
    return result, sorted(set(refs)), model


def one_run(task: dict[str, Any], arm: str, run: int, model: str, budget: float) -> dict[str, Any]:
    run_id: str = f"{task['id']}-{arm}-{run}"
    work: Path = Path(tempfile.mkdtemp(prefix=f"chefbench-{run_id}-"))
    for name, content in task["seed"].items():
        (work / name).parent.mkdir(parents=True, exist_ok=True)
        (work / name).write_text(content, encoding="utf-8")
    settings: Path = work.parent / f"{work.name}.settings.json"
    settings.write_text(json.dumps(settings_all_plugins_off()), encoding="utf-8")
    prompt: str = task["prompt"] + (CONTROL_SUFFIX if arm == "control" else "")
    cmd: list[str] = [
        "claude", "-p", prompt, "--model", model, "--output-format", "stream-json", "--verbose",
        "--settings", str(settings), "--permission-mode", "acceptEdits",
        "--max-budget-usd", str(budget), "--allowedTools", *ALLOWED_TOOLS,
    ]
    if arm == "with":
        cmd += ["--plugin-dir", str(REPO_DIR)]
    stdout: str = ""
    status: str
    try:  # subprocess.run has no non-raising timeout
        proc: subprocess.CompletedProcess[str] = subprocess.run(
            cmd, cwd=work, capture_output=True, text=True, timeout=RUN_TIMEOUT_S)
        stdout, status = proc.stdout, f"exit {proc.returncode}"
    except subprocess.TimeoutExpired as timeout:
        stdout = timeout.stdout.decode("utf-8", errors="replace") if timeout.stdout else ""
        status = "timeout"
    LOGS.mkdir(exist_ok=True)
    (LOGS / f"{run_id}.transcript.jsonl").write_text(stdout, encoding="utf-8")
    session, refs, resolved_model = parse_stream(stdout)
    row: dict[str, Any] = {
        "task": task["id"], "arm": arm, "run": run, "model": resolved_model or model,
        "status": session.get("subtype", status),
        "cost_usd": session.get("total_cost_usd"), "duration_s": round(session["duration_ms"] / 1000, 1) if "duration_ms" in session else None,
        "turns": session.get("num_turns"), "references_read": refs,
        **score(task["id"], work, LOGS / f"{run_id}.tests.log"),
    }
    shutil.copytree(work, LOGS / run_id, ignore=shutil.ignore_patterns(*SKIP_DIRS), dirs_exist_ok=True)
    shutil.rmtree(work, ignore_errors=True)
    settings.unlink(missing_ok=True)
    with WRITE_LOCK, PARTIAL.open("a", encoding="utf-8") as out:
        out.write(json.dumps(row) + "\n")
    print(json.dumps(row), flush=True)
    return row


def cmd_run(args: argparse.Namespace) -> None:
    tasks: list[dict[str, Any]] = json.loads((BENCH_DIR / "tasks.json").read_text(encoding="utf-8"))
    jobs: list[tuple[dict[str, Any], str, int]] = [(t, a, r) for t in tasks for r in range(args.runs) for a in ARMS]
    PARTIAL.unlink(missing_ok=True)
    shutil.rmtree(LOGS, ignore_errors=True)
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        list(pool.map(lambda j: one_run(j[0], j[1], j[2], args.model, args.budget), jobs))
    PARTIAL.replace(RESULTS)


def summarize(values: list[Any]) -> str:
    present: list[Any] = [v for v in values if v is not None]
    if not present:
        return "-"
    if all(isinstance(v, bool) for v in present):
        return f"{sum(present)}/{len(present)}"
    average: str = f"{mean(present):.2f}".rstrip("0").rstrip(".")
    return f"{average} ±{stdev(present):.1f}" if len(present) > 1 and stdev(present) > 0 else average


def cmd_report(_: argparse.Namespace) -> None:
    rows: list[dict[str, Any]] = [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines() if line]
    models: set[str] = {r["model"] for r in rows}
    lines: list[str] = [f"Model: {', '.join(sorted(models))}. Runs per arm: {max(r['run'] for r in rows) + 1}.", ""]
    for task in dict.fromkeys(r["task"] for r in rows):
        task_rows: list[dict[str, Any]] = [r for r in rows if r["task"] == task]
        keys: list[str] = [k for k in task_rows[0] if k not in ("task", "arm", "run", "model", "status", "references_read")]
        lines += [f"### {task}", "", "| Metric | Without | Control prompt | With chef |", "|---|---|---|---|"]
        for k in keys:
            cells: list[str] = [summarize([r.get(k) for r in task_rows if r["arm"] == arm]) for arm in ARMS]
            lines.append(f"| {k} | {' | '.join(cells)} |")
        refs: set[str] = {ref for r in task_rows if r["arm"] == "with" for ref in r["references_read"]}
        lines += [f"| references read (with chef) | | | {', '.join(sorted(refs)) or 'none'} |", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(REPORT.read_text(encoding="utf-8"))


def cmd_selftest(_: argparse.Namespace) -> None:
    root: Path = Path(tempfile.mkdtemp())
    (root / "a.py").write_text('"""Module doc\nsecond line\n"""\ndef f(x: int) -> int:\n    # why\n    return x\n\ndef g(y):\n    return y\n', encoding="utf-8")
    (root / "test_a.py").write_text("def test_f() -> None:\n    assert True\n", encoding="utf-8")
    (root / "package.json").write_text('{"scripts": {"test": "echo \\"Error: no test specified\\" && exit 1"}}', encoding="utf-8")
    files: list[Path] = source_files(root)
    assert code_and_comment_lines(files) == (4, 4), code_and_comment_lines(files)
    assert python_annotation_ratio(files) == 0.67
    assert count(r"^\s*def test_", files, (".py",)) == 1
    assert not npm_has_tests(root)
    assert all(v is False for v in settings_all_plugins_off()["enabledPlugins"].values())
    assert summarize([True, False, None]) == "1/2" and summarize([1.0, 1.0]) == "1" and summarize([1.0, 3.0]) == "2 ±1.4"
    stream: str = "\n".join([
        json.dumps({"type": "system", "subtype": "init", "model": "claude-sonnet-5-5"}),
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Read", "input": {"file_path": "C:\\x\\references\\docker.md"}}]}}),
        json.dumps({"type": "result", "subtype": "success", "total_cost_usd": 0.1}),
    ])
    assert parse_stream(stream) == ({"type": "result", "subtype": "success", "total_cost_usd": 0.1}, ["docker.md"], "claude-sonnet-5-5")
    shutil.rmtree(root)
    print("selftest ok")


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser: argparse.ArgumentParser = sub.add_parser("run")
    run_parser.add_argument("--runs", type=int, default=3)
    run_parser.add_argument("--model", default="sonnet")
    run_parser.add_argument("--budget", type=float, default=3.0)
    run_parser.add_argument("--parallel", type=int, default=2)
    run_parser.set_defaults(func=cmd_run)
    sub.add_parser("report").set_defaults(func=cmd_report)
    sub.add_parser("selftest").set_defaults(func=cmd_selftest)
    args: argparse.Namespace = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
