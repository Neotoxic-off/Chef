"""Score the held-react task: a tag input component in JSX, its hidden Vitest + Testing Library suite run in jsdom."""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from score import Metrics, run
from scorer_lib import (
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

HIDDEN_TEST: Path = Path(__file__).resolve().parent / "hidden.test.jsx"
HIDDEN_TEST_NAME: str = "bench_hidden.test.jsx"
TEST_PACKAGES: tuple[str, ...] = (
    "vitest@4.1.12",
    "jsdom@30.1.3",
    "@testing-library/react@16.3.3",
    "@testing-library/dom@10.4.2",
)
BENCH_VITEST_CONFIG: str = "bench.vitest.config.mjs"
REPORT_NAME: str = "bench-vitest-report.json"
IGNORED_DIRS: tuple[str, ...] = (".git", "node_modules", "dist", "coverage")
JS_SUFFIXES: tuple[str, ...] = (".js", ".jsx", ".mjs", ".cjs")
JS_PATTERNS: tuple[str, ...] = ("**/*.js", "**/*.jsx", "**/*.mjs", "**/*.cjs")
# The bench's own config: the agent's vite or vitest config may need plugins it never installed.
VITEST_CONFIG: str = f"""export default {{ test: {{ environment: "jsdom", include: ["{HIDDEN_TEST_NAME}"] }} }};
"""
ESLINT_CONFIG: str = """import js from "@eslint/js";
import globals from "globals";

export default [
  { ignores: ["node_modules/**", "coverage/**", "dist/**", "bench*"] },
  js.configs.recommended,
  {
    files: ["**/*.{js,jsx,mjs,cjs}"],
    languageOptions: {
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: { ...globals.browser, ...globals.node, ...globals.vitest },
    },
  },
];
"""


def hidden_test_passes(copy: Path) -> bool:
    shutil.copy(HIDDEN_TEST, copy / HIDDEN_TEST_NAME)
    (copy / BENCH_VITEST_CONFIG).write_text(VITEST_CONFIG, encoding="utf-8")
    run(
        [
            executable("node"),
            "node_modules/vitest/vitest.mjs",
            "run",
            "--config",
            BENCH_VITEST_CONFIG,
            "--reporter=json",
            f"--outputFile={REPORT_NAME}",
        ],
        copy,
    )
    report_path: Path = copy / REPORT_NAME
    if not report_path.is_file():
        raise RuntimeError(f"vitest wrote no report in {copy}")
    report: dict[str, Any] = json.loads(report_path.read_text(encoding="utf-8"))
    return bool(report["success"]) and report["numFailedTestSuites"] == 0 and report["numPassedTests"] > 0


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
        npm_install(copy, (*TEST_PACKAGES, *ESLINT_PACKAGES, PRETTIER_PACKAGE))
        metrics["format_clean"] = prettier_clean(copy, JS_PATTERNS)
        metrics["eslint_findings"] = eslint_findings(copy, ESLINT_CONFIG)
        metrics["hidden_test_passes"] = hidden_test_passes(copy)
    return metrics
