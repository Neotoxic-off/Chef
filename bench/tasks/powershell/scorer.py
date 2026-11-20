"""Score the powershell task: hidden Pester 5 tests, PSScriptAnalyzer findings and the Pester tests the agent wrote.

Both modules are saved once from the PowerShell Gallery into the Docker volume MODULES_VOLUME at pinned versions.
"""

import re
import subprocess
from pathlib import Path

import scorer_lib
from score import Metrics

TASK_DIR: Path = Path(__file__).resolve().parent
POWERSHELL_IMAGE: str = (
    "mcr.microsoft.com/powershell:7.5-ubuntu-24.04@sha256:042240d57ec9e47e511033b92625a8d95875ee5860af3015992c248b58a8be81"
)
MODULES_VOLUME: str = "bench-powershell-modules"
PESTER_VERSION: str = "5.7.1"
ANALYZER_VERSION: str = "1.25.0"
IGNORED_PARTS: tuple[str, ...] = (".git",)
MODULE_FILES: tuple[str, ...] = ("DotEnv.psm1", "DotEnv.psd1")
TEST_BLOCK: re.Pattern[str] = re.compile(r"^\s*It\s+['\"]", re.MULTILINE | re.IGNORECASE)
RESULT_LINE: re.Pattern[str] = re.compile(r"^bench:(\w+)=(\d+)$", re.MULTILINE)
# Only the tool setup stops on errors: a global ErrorActionPreference would make the agent's Write-Error terminating.
SCRIPT: str = f"""
foreach ($tool in @(@('Pester', '{PESTER_VERSION}'), @('PSScriptAnalyzer', '{ANALYZER_VERSION}'))) {{
    if (-not (Test-Path "/modules/$($tool[0])/$($tool[1])")) {{
        Save-Module -Name $tool[0] -RequiredVersion $tool[1] -Path /modules -Repository PSGallery -Force -ErrorAction Stop
    }}
}}
Import-Module /modules/Pester/{PESTER_VERSION}/Pester.psd1 -ErrorAction Stop
Import-Module /modules/PSScriptAnalyzer/{ANALYZER_VERSION}/PSScriptAnalyzer.psd1 -ErrorAction Stop
$config = New-PesterConfiguration
$config.Run.Path = '/bench/BenchHidden.Tests.ps1'
$config.Run.PassThru = $true
$config.Output.Verbosity = 'Detailed'
$result = Invoke-Pester -Configuration $config
"bench:hidden=$([int]($result.Result -ne 'Passed' -or $result.PassedCount -eq 0))"
$sources = Get-ChildItem /work -Recurse -File -Include *.ps1, *.psm1, *.psd1 |
    Where-Object {{ $_.Name -notlike '*.Tests.ps1' -and $_.FullName -notlike '/work/.git/*' }}
$findings = @($sources | ForEach-Object {{ Invoke-ScriptAnalyzer -Path $_.FullName }})
$findings | Format-Table -AutoSize | Out-String | Write-Host
"bench:analyzer=$($findings.Count)"
"""


def count_tests_written(workspace: Path) -> int:
    tests: list[Path] = scorer_lib.source_files(workspace, (".Tests.ps1",), IGNORED_PARTS)
    return sum(len(TEST_BLOCK.findall((workspace / path).read_text(encoding="utf-8", errors="replace"))) for path in tests)


def run_container(workspace: Path) -> dict[str, int]:
    outcome: subprocess.CompletedProcess[str] = scorer_lib.docker_run(
        [
            *("-v", f"{workspace.resolve()}:/work:ro", "-v", f"{TASK_DIR}:/bench:ro", "-v", f"{MODULES_VOLUME}:/modules"),
            *("-e", "BENCH_WORKSPACE=/work", POWERSHELL_IMAGE, "pwsh", "-NoLogo", "-NoProfile", "-Command", SCRIPT),
        ],
        workspace,
    )
    results: dict[str, int] = {name: int(code) for name, code in RESULT_LINE.findall(outcome.stdout)}
    if results.keys() != {"hidden", "analyzer"}:
        failure: str = (outcome.stderr or outcome.stdout).strip()[-scorer_lib.ERROR_TAIL_CHARS :]
        raise RuntimeError(f"the powershell scorer did not run in {workspace}: {failure}")
    return results


def score(workspace: Path) -> Metrics:
    metrics: Metrics = {"hidden_test_passes": False, "tests_written": count_tests_written(workspace), "analyzer_findings": 0}
    if not any((workspace / name).is_file() for name in MODULE_FILES):
        return metrics
    results: dict[str, int] = run_container(workspace)
    metrics["hidden_test_passes"] = results["hidden"] == 0
    metrics["analyzer_findings"] = results["analyzer"]
    return metrics
