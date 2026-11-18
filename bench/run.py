"""Benchmark Claude Code with and without the chef plugin.

Each run is a headless `claude -p` session in a fresh temp folder. The two arms
differ only by the chef plugin: every other plugin is disabled in both.

Usage:
    python bench/run.py run --runs 2 --model sonnet     # writes bench/results.jsonl
    python bench/run.py report                          # writes bench/results.md
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
from statistics import mean
from threading import Lock
from typing import Any

BENCH_DIR: Path = Path(__file__).resolve().parent
RESULTS: Path = BENCH_DIR / "results.jsonl"
REPORT: Path = BENCH_DIR / "results.md"
USER_SETTINGS: Path = Path.home() / ".claude" / "settings.json"
CHEF_ID: str = "chef@chef"
RUN_TIMEOUT_S: int = 1200
TEST_TIMEOUT_S: int = 600
SOURCE_EXT: dict[str, str] = {".cs": "//", ".ts": "//", ".js": "//", ".py": "#"}
SKIP_DIRS: set[str] = {"node_modules", "bin", "obj", ".venv", "dist", ".git", "__pycache__", ".pytest_cache"}
WRITE_LOCK: Lock = Lock()
ALLOWED_TOOLS: list[str] = [
    "Read", "Write", "Edit", "Glob", "Grep", "Agent", "Skill", "TodoWrite", "WebSearch", "WebFetch",
    "Bash(dotnet *)", "Bash(npm *)", "Bash(npx *)", "Bash(node *)", "Bash(python *)", "Bash(uv *)",
    "Bash(pip *)", "Bash(ls *)", "Bash(mkdir *)", "Bash(cat *)", "PowerShell(Get-CimInstance *)",
]


def settings_for(arm: str) -> dict[str, Any]:
    user: dict[str, Any] = json.loads(USER_SETTINGS.read_text(encoding="utf-8"))
    ids: list[str] = list(user.get("enabledPlugins", {}).keys())
    if CHEF_ID not in ids:
        ids.append(CHEF_ID)
    return {"enabledPlugins": {pid: arm == "with" and pid == CHEF_ID for pid in ids}}


def source_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file() and not SKIP_DIRS.intersection(p.relative_to(root).parts)]


def code_and_comment_lines(files: list[Path]) -> tuple[int, int]:
    code: int = 0
    comments: int = 0
    for f in files:
        marker: str | None = SOURCE_EXT.get(f.suffix)
        if marker is None:
            continue
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped: str = line.strip()
            if not stripped:
                continue
            if stripped.startswith((marker, "/*", "*", '"""')):
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


def run_tests(task_id: str, root: Path) -> bool | None:
    commands: list[list[str]]
    if task_id == "csharp":
        projects: list[Path] = [p for p in root.rglob("*.csproj") if "test" in p.name.lower()]
        if not projects:
            return None
        commands = [["dotnet", "test", str(p)] for p in projects]
    elif task_id == "typescript":
        if not (root / "package.json").exists():
            return None
        commands = [["npm", "install", "--silent"], ["npm", "test", "--silent"]]
    elif task_id == "python":
        if not any("test" in p.name for p in root.rglob("*.py")):
            return None
        commands = [["uv", "run", "--with", "pytest", "python", "-m", "pytest", "-q"]]
    else:
        return None
    for cmd in commands:
        result: subprocess.CompletedProcess[str] = subprocess.run(
            cmd, cwd=root, capture_output=True, text=True, timeout=TEST_TIMEOUT_S, shell=sys.platform == "win32")
        if result.returncode != 0:
            return False
    return True


def score(task_id: str, root: Path) -> dict[str, Any]:
    files: list[Path] = source_files(root)
    code, comments = code_and_comment_lines(files)
    text_of: dict[str, str] = {f.name: f.read_text(encoding="utf-8", errors="replace") for f in files}
    joined: str = "\n".join(text_of.values())
    m: dict[str, Any] = {
        "code_lines": code,
        "comment_ratio": round(comments / code, 2) if code else 0.0,
        "try_blocks": count(r"\btry\s*[{:]", files, (".cs", ".ts", ".js", ".py")),
        "test_cases": count(r"\[(Fact|Theory)\]|\b(it|test)\(\s*['\"`]|^\s*def test_", files, (".cs", ".ts", ".js", ".py")),
    }
    if task_id == "csharp":
        m["inferred_var"] = count(r"\bvar\s+\w+\s*=", files, (".cs",))
        m["warnings_as_errors"] = "TreatWarningsAsErrors>true" in joined
        m["nullable"] = "<Nullable>enable" in joined
    elif task_id == "typescript":
        m["any_usages"] = count(r":\s*any\b|\bas any\b", files, (".ts",))
        m["untyped_decls"] = count(r"\b(const|let)\s+\w+\s*=", files, (".ts",))
        m["strict_tsconfig"] = bool(re.search(r'"strict"\s*:\s*true', text_of.get("tsconfig.json", "")))
        m["eslint"] = any(n.startswith("eslint.config") or n.startswith(".eslintrc") for n in text_of)
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
    m["tests_pass"] = run_tests(task_id, root)
    return m


def one_run(task: dict[str, Any], arm: str, run: int, model: str, budget: float) -> dict[str, Any]:
    work: Path = Path(tempfile.mkdtemp(prefix=f"chefbench-{task['id']}-{arm}-"))
    for name, content in task["seed"].items():
        (work / name).write_text(content, encoding="utf-8")
    settings: Path = work.parent / f"{work.name}.settings.json"
    settings.write_text(json.dumps(settings_for(arm)), encoding="utf-8")
    cmd: list[str] = [
        "claude", "-p", task["prompt"], "--model", model, "--output-format", "json",
        "--settings", str(settings), "--permission-mode", "acceptEdits",
        "--max-budget-usd", str(budget), "--allowedTools", *ALLOWED_TOOLS,
    ]
    stdout: str = ""
    status: str
    try:  # subprocess.run has no non-raising timeout
        proc: subprocess.CompletedProcess[str] = subprocess.run(
            cmd, cwd=work, capture_output=True, text=True, timeout=RUN_TIMEOUT_S, shell=False)
        stdout, status = proc.stdout, f"exit {proc.returncode}"
    except subprocess.TimeoutExpired:
        status = "timeout"
    session: dict[str, Any] = json.loads(stdout) if stdout.strip().startswith("{") else {}
    row: dict[str, Any] = {
        "task": task["id"], "arm": arm, "run": run, "model": model,
        "cost_usd": session.get("total_cost_usd"), "duration_s": round(session.get("duration_ms", 0) / 1000, 1),
        "turns": session.get("num_turns"), "status": session.get("subtype", status),
        **score(task["id"], work),
    }
    shutil.rmtree(work, ignore_errors=True)
    settings.unlink(missing_ok=True)
    with WRITE_LOCK, RESULTS.open("a", encoding="utf-8") as out:
        out.write(json.dumps(row) + "\n")
    print(json.dumps(row), flush=True)
    return row


def cmd_run(args: argparse.Namespace) -> None:
    tasks: list[dict[str, Any]] = json.loads((BENCH_DIR / "tasks.json").read_text(encoding="utf-8"))
    jobs: list[tuple[dict[str, Any], str, int]] = [(t, a, r) for t in tasks for r in range(args.runs) for a in ("without", "with")]
    RESULTS.unlink(missing_ok=True)
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        list(pool.map(lambda j: one_run(j[0], j[1], j[2], args.model, args.budget), jobs))


def summarize(values: list[Any]) -> str:
    present: list[Any] = [v for v in values if v is not None]
    if not present:
        return "-"
    if all(isinstance(v, bool) for v in present):
        return f"{sum(present)}/{len(present)}"
    return f"{mean(present):.2f}".rstrip("0").rstrip(".")


def cmd_report(_: argparse.Namespace) -> None:
    rows: list[dict[str, Any]] = [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines() if line]
    lines: list[str] = []
    for task in dict.fromkeys(r["task"] for r in rows):
        task_rows: list[dict[str, Any]] = [r for r in rows if r["task"] == task]
        keys: list[str] = [k for k in task_rows[0] if k not in ("task", "arm", "run", "model", "status")]
        lines += [f"### {task}", "", "| Metric | Without chef | With chef |", "|---|---|---|"]
        for k in keys:
            cells: list[str] = [summarize([r.get(k) for r in task_rows if r["arm"] == arm]) for arm in ("without", "with")]
            lines.append(f"| {k} | {cells[0]} | {cells[1]} |")
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(REPORT.read_text(encoding="utf-8"))


def cmd_selftest(_: argparse.Namespace) -> None:
    root: Path = Path(tempfile.mkdtemp())
    (root / "a.py").write_text("def f(x: int) -> int:\n    # why\n    return x\n\ndef g(y):\n    return y\n", encoding="utf-8")
    (root / "test_a.py").write_text("def test_f() -> None:\n    assert True\n", encoding="utf-8")
    files: list[Path] = source_files(root)
    assert code_and_comment_lines(files) == (6, 1)
    assert python_annotation_ratio(files) == 0.67
    assert count(r"^\s*def test_", files, (".py",)) == 1
    assert settings_for("without")["enabledPlugins"][CHEF_ID] is False
    assert settings_for("with")["enabledPlugins"][CHEF_ID] is True
    assert summarize([True, False, None]) == "1/2" and summarize([1.0, 2.0]) == "1.5"
    shutil.rmtree(root)
    print("selftest ok")


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser: argparse.ArgumentParser = sub.add_parser("run")
    run_parser.add_argument("--runs", type=int, default=2)
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
