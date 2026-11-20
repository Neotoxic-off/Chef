Set-StrictMode -Version Latest

function Read-DotEnv {
    <#
    .SYNOPSIS
    Reads the variables of a .env file into an ordered dictionary, in file order.

    .PARAMETER Path
    The .env file to read.

    .EXAMPLE
    $settings = Read-DotEnv -Path ./.env
    #>
    [CmdletBinding()]
    [OutputType([System.Collections.Specialized.OrderedDictionary])]
    param(
        [Parameter(Mandatory)]
        [string] $Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        $PSCmdlet.ThrowTerminatingError([System.Management.Automation.ErrorRecord]::new(
                [System.IO.FileNotFoundException]::new("No .env file at '$Path'."),
                'DotEnv.FileNotFound',
                [System.Management.Automation.ErrorCategory]::ObjectNotFound,
                $Path))
    }

    $variables = [ordered]@{}
    $number = 0
    # Get-Content splits on both LF and CRLF.
    foreach ($line in Get-Content -LiteralPath $Path) {
        $number++
        $text = $line.Trim()
        if ($text -eq '' -or $text.StartsWith('#')) {
            continue
        }
        $separator = $text.IndexOf('=')
        $name = if ($separator -gt 0) { $text.Substring(0, $separator).Trim() } else { '' }
        if ($name -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
            $PSCmdlet.ThrowTerminatingError([System.Management.Automation.ErrorRecord]::new(
                    [System.FormatException]::new("Invalid line $number in '$Path': expected NAME=value."),
                    'DotEnv.InvalidLine',
                    [System.Management.Automation.ErrorCategory]::InvalidData,
                    $line))
        }
        $raw = $text.Substring($separator + 1)
        $value = $raw.Trim()
        $quoted = $value.Length -ge 2 -and $value[0] -in '"', "'" -and $value[-1] -eq $value[0]
        $variables[$name] = if ($quoted) { $value.Substring(1, $value.Length - 2) } else { ($raw -replace '\s#.*$', '').Trim() }
    }
    $variables
}

Export-ModuleMember -Function Read-DotEnv
