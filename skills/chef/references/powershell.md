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

## Code

- Scripts start with `Set-StrictMode -Version Latest` and `$ErrorActionPreference = 'Stop'`. Modules only with `Set-StrictMode`: `Stop` at module scope turns every `WriteError` of their functions into a terminating error; pass `-ErrorAction Stop` to the calls that must stop.
- Every function is advanced: `[CmdletBinding()]`, a `param()` block and `[OutputType([Type])]`.
- Type every parameter. Locals are optional: type one when the value could change type. `[int]$count = 0`.
- Validate at the boundary: `[Parameter(Mandatory)]`, `[ValidateNotNullOrEmpty()]`, `[ValidateSet()]`, `[ValidateRange()]`.
- Names are `Verb-Noun`: an approved verb (`Get-Verb`), a singular noun.
- `SupportsShouldProcess` on anything that changes state; call `$PSCmdlet.ShouldProcess()` before the change.
- No aliases (`%`, `?`, `ls`) and no positional arguments in scripts. Full cmdlet and parameter names.
- Return objects (`[pscustomobject]` or a `class`), not formatted text. No `Write-Host` for data; use `Write-Verbose`, `Write-Warning`, `Write-Error`.
- No `Invoke-Expression`. Never build commands from strings.
- Reusable code: a module (`.psm1` + `.psd1`) with explicit `FunctionsToExport`.

## Tests

- Pester 6 (classic `Should -Be` still works). One `*.Tests.ps1` per source file; `BeforeAll { . $PSCommandPath.Replace('.Tests.ps1', '.ps1') }`.
- Isolate I/O with `Mock` inside the module scope (`-ModuleName`); verify with `Should -Invoke`.
- `TestDrive:` for files, `TestRegistry:` for the registry; tag integration tests `-Tag 'Integration'`.
- Coverage is command coverage (no branch coverage). `CoveragePercentTarget` only reports, so gate it yourself:
  ```powershell
  $config = New-PesterConfiguration
  $config.Run.Path = './tests'
  $config.Run.PassThru = $true
  $config.CodeCoverage.Enabled = $true
  $config.CodeCoverage.Path = './src'
  $config.CodeCoverage.CoveragePercentTarget = 90
  $result = Invoke-Pester -Configuration $config
  if ($result.CodeCoverage.CoveragePercent -lt 90) { throw "Coverage under 90%." }
  ```
- No maintained mutation testing tool exists for PowerShell.

## Pitfalls

- `@{}` and `[ordered]@{}` literals compare keys without case: `a` then `A` is one entry. When case matters, use `[System.Collections.Specialized.OrderedDictionary]::new([StringComparer]::Ordinal)` or a `Dictionary[string, T]` with `Ordinal`.
- .NET methods (`[System.IO.File]::ReadAllText`) resolve a relative path against the process's current directory, which `Set-Location` does not change. Resolve it first: `$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)`.

Order before done: `Invoke-Formatter` then `Invoke-ScriptAnalyzer` then `Invoke-Pester`.

No `pwsh` 7 (Windows PowerShell 5.1 is not it) or no modules: run in `mcr.microsoft.com/dotnet/sdk:10.0`, which ships PowerShell 7.6 (1.3 GB; the PowerShell team's images are deprecated). The modules install once into the `chef-pwsh-modules` volume (the first run takes about a minute and needs network, later ones about 3 s). It formats the files, then prints one line per finding and failed test. The lint is retried only on PSScriptAnalyzer 1.25.0's `NullReferenceException` race: `export MSYS_NO_PATHCONV=1; src=$PWD; command -v cygpath >/dev/null && src=$(cygpath -m "$PWD"); docker run --rm -v chef-pwsh-modules:/root/.local/share/powershell/Modules -v "$src:/w" -w /w mcr.microsoft.com/dotnet/sdk:10.0 pwsh -NoProfile -Command '$ErrorActionPreference = "Stop"; $PSStyle.OutputRendering = "PlainText"; foreach ($m in @{ Pester = "6.2.0"; PSScriptAnalyzer = "1.25.0" }.GetEnumerator()) { if (-not (Get-Module -ListAvailable $m.Key | Where-Object Version -EQ $m.Value)) { Install-Module $m.Key -RequiredVersion $m.Value -Scope CurrentUser -Force } }; $settings = Import-PowerShellDataFile ./PSScriptAnalyzerSettings.psd1; foreach ($file in Get-ChildItem -Recurse -File -Include *.ps1, *.psm1, *.psd1) { $text = Get-Content -Raw $file; $formatted = Invoke-Formatter -ScriptDefinition $text -Settings $settings; if ($formatted -cne $text) { Set-Content -NoNewline -Path $file -Value $formatted } }; $lint = $null; foreach ($attempt in 1..3) { try { $lint = @(Invoke-ScriptAnalyzer -Path . -Recurse -Settings $settings); break } catch [System.NullReferenceException] { "PSScriptAnalyzer hit its known race (attempt $attempt), running it again" } }; if ($null -eq $lint) { throw "PSScriptAnalyzer crashed 3 times" }; $lint | ForEach-Object { "$($_.ScriptName):$($_.Line) $($_.RuleName): $($_.Message)" }; $c = New-PesterConfiguration; $c.Run.PassThru = $true; $c.Output.Verbosity = "None"; $tests = Invoke-Pester -Configuration $c; $tests.Failed | ForEach-Object { "FAIL $($_.ExpandedPath): $($_.ErrorRecord[0].Exception.Message)" }; "lint: $($lint.Count) findings; tests: $($tests.PassedCount) passed, $($tests.FailedCount) failed"; if ($lint.Count -or $tests.Result -ne "Passed") { exit 1 }'`.
