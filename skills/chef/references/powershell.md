# PowerShell

Written for PowerShell 7.7 (7.6 is the current LTS; 7.4 reached end of support on 2026-11-10), PSScriptAnalyzer 1.25.0, Pester 6.2.0 (Nov 2026), not benchmarked.

Target PowerShell 7.6+. Only target Windows PowerShell 5.1 when the host requires it, and say so in the manifest (`PowerShellVersion`, `CompatiblePSEditions`).

## Lint and format: PSScriptAnalyzer

`PSScriptAnalyzerSettings.psd1` at the repo root:

```powershell
@{
    Severity = @('Error', 'Warning', 'Information')
    Rules    = @{  # formatting rules are off by default: enable them here
        PSUseConsistentIndentation = @{ Enable = $true; IndentationSize = 4; Kind = 'space' }
        PSUseConsistentWhitespace  = @{ Enable = $true }
        PSPlaceOpenBrace           = @{ Enable = $true; OnSameLine = $true }
        PSPlaceCloseBrace          = @{ Enable = $true }
        PSUseCorrectCasing         = @{ Enable = $true }
    }
}
```

- Lint in CI, failing on any finding: `Invoke-ScriptAnalyzer -Path . -Recurse -Settings ./PSScriptAnalyzerSettings.psd1 -EnableExit`.
- Format with `Invoke-Formatter -ScriptDefinition $text -Settings ./PSScriptAnalyzerSettings.psd1`. It has no check mode: in CI, fail when its output differs from the file.
- Never suppress a rule (`SuppressMessageAttribute`, `-ErrorAction SilentlyContinue`): fix the cause, or tell the user if you cannot.

## Code

- Start every script and module with:
  ```powershell
  Set-StrictMode -Version Latest
  $ErrorActionPreference = 'Stop'
  ```
- Every function is advanced: `[CmdletBinding()]`, a `param()` block and `[OutputType([Type])]`.
- Type every parameter. Locals are optional: type one when the value could change type. `[int]$count = 0`, `[System.Collections.Generic.List[string]]$items = [System.Collections.Generic.List[string]]::new()`.
- Validate at the boundary: `[Parameter(Mandatory)]`, `[ValidateNotNullOrEmpty()]`, `[ValidateSet()]`, `[ValidateRange()]`.
- Names are `Verb-Noun` with an approved verb (`Get-Verb`) and a singular noun. PSScriptAnalyzer enforces it.
- `SupportsShouldProcess` on anything that changes state; call `$PSCmdlet.ShouldProcess()` before the change.
- No aliases (`%`, `?`, `ls`) and no positional arguments in scripts. Full cmdlet and parameter names.
- Return objects (`[pscustomobject]` or a `class`), not formatted text. No `Write-Host` for data; use `Write-Verbose`, `Write-Warning`, `Write-Error`.
- No `Invoke-Expression`. Never build commands from strings.
- Ship reusable code as a module (`.psm1` + `.psd1`) with an explicit `FunctionsToExport`.

## Tests

- Pester 6 (same configuration object as Pester 5; classic `Should -Be` still works, new `Should-*` assertions are optional; runs on 5.1 and 7.4+). One `*.Tests.ps1` per source file; `BeforeAll { . $PSCommandPath.Replace('.Tests.ps1', '.ps1') }`.
- Isolate I/O with `Mock` inside the module scope (`-ModuleName`); verify with `Should -Invoke`.
- Use `TestDrive:` for files and `TestRegistry:` for the registry. Tag integration tests: `-Tag 'Integration'`.
- Coverage is command coverage (no branch coverage). `CoveragePercentTarget` only reports, so gate it yourself:
  ```powershell
  $config = New-PesterConfiguration
  $config.Run.Path = './tests'
  $config.Run.PassThru = $true
  $config.Run.Exit = $true
  $config.CodeCoverage.Enabled = $true
  $config.CodeCoverage.Path = './src'
  $config.CodeCoverage.CoveragePercentTarget = 90
  $result = Invoke-Pester -Configuration $config
  if ($result.CodeCoverage.CoveragePercent -lt 90) { throw "Coverage under 90%." }
  ```
- No maintained mutation testing tool exists for PowerShell.

Order before done: `Invoke-Formatter` then `Invoke-ScriptAnalyzer` then `Invoke-Pester`.

No `pwsh` 7 (Windows PowerShell 5.1 is not it) or no modules: run in `mcr.microsoft.com/dotnet/sdk:10.0`, which ships PowerShell 7.6 (1.3 GB; the PowerShell team's own images are deprecated). The modules install on each run (about 10 s, needs network); the settings file enables the formatting rules, so the analyzer also reports formatting: `MSYS_NO_PATHCONV=1 docker run --rm -v "$PWD:/w" -w /w mcr.microsoft.com/dotnet/sdk:10.0 pwsh -NoProfile -Command 'Install-Module Pester -RequiredVersion 6.2.0 -Scope CurrentUser -Force; Install-Module PSScriptAnalyzer -RequiredVersion 1.25.0 -Scope CurrentUser -Force; $lint = Invoke-ScriptAnalyzer -Path . -Recurse -Settings ./PSScriptAnalyzerSettings.psd1; $lint; $c = New-PesterConfiguration; $c.Run.PassThru = $true; $tests = Invoke-Pester -Configuration $c; if ($lint -or $tests.Result -ne "Passed") { exit 1 }'`.
