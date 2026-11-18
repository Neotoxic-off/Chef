# Chef guard. Reads a PreToolUse event on stdin; when its command is a build, test or install and the
# machine is busy, asks the user to confirm. Overrides: CHEF_GUARD_DISABLE=1, CHEF_GUARD_MIN_FREE_GB, CHEF_GUARD_MAX_CPU.
Set-StrictMode -Version Latest

if ($env:CHEF_GUARD_DISABLE -eq '1') { exit 0 }

[string]$raw = [Console]::In.ReadToEnd()
[psobject]$event = $raw | ConvertFrom-Json
[string]$command = $event.tool_input.command
[string]$pattern = (Get-Content -Raw -Path (Join-Path $PSScriptRoot 'heavy-commands.regex')).Trim()
if ($command -notmatch $pattern) { exit 0 }

[double]$minFreeGb = if ($env:CHEF_GUARD_MIN_FREE_GB) { [double]$env:CHEF_GUARD_MIN_FREE_GB } else { 4 }
[int]$maxCpu = if ($env:CHEF_GUARD_MAX_CPU) { [int]$env:CHEF_GUARD_MAX_CPU } else { 80 }

[string[]]$reasons = @()

[ciminstance]$os = Get-CimInstance Win32_OperatingSystem
[double]$freeGb = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
if ($freeGb -lt $minFreeGb) { $reasons += "only $freeGb GB of RAM free (minimum $minFreeGb GB)" }

[double]$cpu = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
if ($cpu -gt $maxCpu) { $reasons += "CPU at $cpu% (maximum $maxCpu%)" }

# SHQueryUserNotificationState: 2 = fullscreen app, 3 = fullscreen Direct3D game, 4 = presentation mode
Add-Type -Namespace ChefGuard -Name Shell -MemberDefinition '[DllImport("shell32.dll")] public static extern int SHQueryUserNotificationState(out int state);'
[int]$state = 0
[void][ChefGuard.Shell]::SHQueryUserNotificationState([ref]$state)
if ($state -in 2, 3, 4) { $reasons += 'a fullscreen app, game or presentation is running' }

# A microphone is in use while an app's LastUsedTimeStop is 0.
[string]$micStore = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone'
[bool]$micInUse = (Test-Path -Path $micStore) -and @(Get-ChildItem -Path $micStore -Recurse |
    Where-Object { $_.GetValue('LastUsedTimeStop') -eq 0 -and $null -ne $_.GetValue('LastUsedTimeStart') }).Count -gt 0
if ($micInUse) { $reasons += 'the microphone is in use (call or voice chat?)' }

if ($reasons.Count -eq 0) { exit 0 }

[string]$why = "Chef guard: the machine looks busy: $($reasons -join '; '). Running this build, test or install now may freeze it. Confirm to run anyway."
@{
    hookSpecificOutput = @{
        hookEventName            = 'PreToolUse'
        permissionDecision       = 'ask'
        permissionDecisionReason = $why
    }
} | ConvertTo-Json -Depth 3 -Compress
exit 0
