"""Score the php task: hidden PHPUnit test, PHPStan level max errors and the test methods the agent wrote.

Everything runs in one Composer container (PHP 8.4, with the bcmath and gmp extensions). The workspace is copied into the container, without vendor/,
so dependencies come from the agent's composer.json; Composer's cache and the pinned PHPStan live in Docker volumes.
"""

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import scorer_lib
from score import Metrics

TASK_DIR: Path = Path(__file__).resolve().parent
COMPOSER_IMAGE: str = "composer:2.8.12@sha256:5248900ab8b5f7f880c2d62180e40960cd87f60149ec9a1abfd62ac72a02577c"
# Money code often requires ext-bcmath or ext-gmp, which the Composer image lacks; a missing extension is not the agent's fault.
SCORING_IMAGE: str = "bench-php:2.8.12-bcmath-gmp"
SCORING_DOCKERFILE: str = f"FROM {COMPOSER_IMAGE}\nRUN apk add --no-cache gmp-dev && docker-php-ext-install bcmath gmp\n"
CACHE_VOLUME: str = "bench-composer-cache"
TOOLS_VOLUME: str = "bench-php-tools"
# Used only when the agent's composer.json does not bring PHPUnit.
PHPUNIT_PACKAGE: str = "phpunit/phpunit:13.4.5"
PHPSTAN_VERSION: str = "2.3.5"
PHPSTAN_DIR: str = f"/tools/phpstan-{PHPSTAN_VERSION}"
NETWORK_FAILURES: tuple[str, ...] = ("curl error", "Could not resolve host", "failed to open stream: Connection")
PHPSTAN_OK_CODES: frozenset[int] = frozenset({0, 1})
IGNORED_PARTS: tuple[str, ...] = (".git", "vendor")
TEST_METHOD: re.Pattern[str] = re.compile(r"function\s+test\w*\s*\(|#\[Test\]")
RESULT_LINE: re.Pattern[str] = re.compile(r"^bench:(\w+)=(\d+)$", re.MULTILINE)
COMPOSER: str = "composer --no-interaction --no-progress"
SCRIPT: str = f"""
set -u
mkdir /project && tar -C /src --exclude=./vendor --exclude=./.git -cf - . | tar -C /project -xf - && cd /project || exit 1
[ -x {PHPSTAN_DIR}/vendor/bin/phpstan ] \\
  || {{ mkdir -p {PHPSTAN_DIR} && {COMPOSER} require --working-dir {PHPSTAN_DIR} phpstan/phpstan:{PHPSTAN_VERSION} >&2; }}
if ! {COMPOSER} install --no-scripts >/tmp/install.log 2>&1 \\
   || ! {{ [ -x vendor/bin/phpunit ] || {COMPOSER} require --dev --no-scripts {PHPUNIT_PACKAGE} >>/tmp/install.log 2>&1; }}; then
  cat /tmp/install.log >&2; echo bench:install=1; exit 0
fi
echo bench:install=0
vendor/bin/phpunit --no-configuration --bootstrap vendor/autoload.php /bench/BenchHiddenTest.php >&2; echo bench:hidden=$?
if [ -d src ]; then
  cd /tmp && {PHPSTAN_DIR}/vendor/bin/phpstan analyse --level max --no-progress --error-format json --memory-limit 1G \\
    --autoload-file /project/vendor/autoload.php /project/src >/out/phpstan.json; echo bench:phpstan=$?
fi
"""


def count_tests_written(workspace: Path) -> int:
    sources: list[Path] = scorer_lib.source_files(workspace, (".php",), IGNORED_PARTS)
    return sum(len(TEST_METHOD.findall((workspace / path).read_text(encoding="utf-8", errors="replace"))) for path in sources)


def count_phpstan_errors(report: Path) -> int:
    loaded: dict[str, Any] = json.loads(report.read_text(encoding="utf-8"))
    totals: dict[str, int] = loaded["totals"]
    return totals["errors"] + totals["file_errors"]


def run_container(workspace: Path, out: Path) -> dict[str, int]:
    outcome: subprocess.CompletedProcess[str] = scorer_lib.docker_run(
        [
            *("-v", f"{workspace.resolve()}:/src:ro", "-v", f"{TASK_DIR}:/bench:ro", "-v", f"{out}:/out"),
            *("-v", f"{CACHE_VOLUME}:/tmp/composer-cache", "-e", "COMPOSER_CACHE_DIR=/tmp/composer-cache"),
            *(
                "-v",
                f"{TOOLS_VOLUME}:/tools",
                "--entrypoint",
                "sh",
                scorer_lib.local_image(SCORING_IMAGE, SCORING_DOCKERFILE),
                "-c",
                SCRIPT,
            ),
        ],
        workspace,
    )
    results: dict[str, int] = {name: int(code) for name, code in RESULT_LINE.findall(outcome.stdout)}
    network_down: bool = results.get("install") == 1 and any(failure in outcome.stderr for failure in NETWORK_FAILURES)
    if "install" not in results or network_down:
        raise RuntimeError(f"the php scorer did not run in {workspace}: {outcome.stderr.strip()[-scorer_lib.ERROR_TAIL_CHARS :]}")
    return results


def score(workspace: Path) -> Metrics:
    metrics: Metrics = {"hidden_test_passes": False, "tests_written": count_tests_written(workspace), "phpstan_errors": 0}
    if not (workspace / "composer.json").is_file():
        return metrics
    with tempfile.TemporaryDirectory() as out_name:
        out: Path = Path(out_name)
        results: dict[str, int] = run_container(workspace, out)
        metrics["hidden_test_passes"] = results.get("hidden") == 0
        if "phpstan" in results:
            if results["phpstan"] not in PHPSTAN_OK_CODES:
                raise RuntimeError(f"phpstan failed in {workspace} with exit code {results['phpstan']}")
            metrics["phpstan_errors"] = count_phpstan_errors(out / "phpstan.json")
    return metrics
