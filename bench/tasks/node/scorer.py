"""Score the node task: an Express API in plain JavaScript, its hidden node:test suite run against the exported app."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from score import Metrics, run
from scorer_lib import (
    ERROR_TAIL_CHARS,
    ESLINT_PACKAGES,
    PRETTIER_PACKAGE,
    copy_workspace,
    count_js_tests,
    eslint_findings,
    executable,
    npm_install,
    prettier_clean,
    source_files,
)

HIDDEN_TEST: Path = Path(__file__).resolve().parent / "hidden.test.mjs"
HIDDEN_TEST_NAME: str = "bench_hidden.test.mjs"
IGNORED_DIRS: tuple[str, ...] = (".git", "node_modules")
JS_SUFFIXES: tuple[str, ...] = (".js", ".mjs", ".cjs")
JS_PATTERNS: tuple[str, ...] = ("**/*.js", "**/*.mjs", "**/*.cjs")
TAP_FAIL_PATTERN: re.Pattern[str] = re.compile(r"^# fail (\d+)$", re.MULTILINE)
TAP_PASS_PATTERN: re.Pattern[str] = re.compile(r"^# pass (\d+)$", re.MULTILINE)
ESLINT_CONFIG: str = """import js from "@eslint/js";
import globals from "globals";

export default [
  { ignores: ["node_modules/**", "coverage/**", "dist/**", "bench*"] },
  js.configs.recommended,
  { languageOptions: { globals: globals.node } },
];
"""


def hidden_test_passes(copy: Path) -> bool:
    shutil.copy(HIDDEN_TEST, copy / HIDDEN_TEST_NAME)
    # --test-force-exit: an app.js that listens on import would otherwise hold the run open until the timeout.
    outcome: subprocess.CompletedProcess[str] = run(
        [executable("node"), "--test", "--test-force-exit", "--test-reporter=tap", HIDDEN_TEST_NAME], copy
    )
    failed: re.Match[str] | None = TAP_FAIL_PATTERN.search(outcome.stdout)
    passed: re.Match[str] | None = TAP_PASS_PATTERN.search(outcome.stdout)
    if failed is None or passed is None:
        raise RuntimeError(f"node --test did not run in {copy}: {outcome.stderr.strip()[:ERROR_TAIL_CHARS]}")
    return outcome.returncode == 0 and int(failed.group(1)) == 0 and int(passed.group(1)) > 0


def score(workspace: Path) -> Metrics:
    files: list[Path] = source_files(workspace, JS_SUFFIXES, IGNORED_DIRS)
    metrics: Metrics = {
        "hidden_test_passes": False,
        "tests_written": count_js_tests(workspace, files),
        "eslint_findings": None,
        "format_clean": None,
    }
    if not files or not (workspace / "package.json").is_file():
        return metrics
    with tempfile.TemporaryDirectory() as scratch:
        copy: Path = copy_workspace(workspace, Path(scratch), IGNORED_DIRS)
        npm_install(copy, (*ESLINT_PACKAGES, PRETTIER_PACKAGE))
        metrics["format_clean"] = prettier_clean(copy, JS_PATTERNS)
        metrics["eslint_findings"] = eslint_findings(copy, ESLINT_CONFIG)
        metrics["hidden_test_passes"] = hidden_test_passes(copy)
    return metrics
