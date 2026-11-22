Set-StrictMode -Version Latest

# A hashtable compares its string keys case-insensitively, which makes the units case-insensitive.
$script:Multipliers = @{
    ''    = [decimal]1
    'B'   = [decimal]1
    'KB'  = [decimal]1000
    'MB'  = [decimal]1000000
    'GB'  = [decimal]1000000000
    'TB'  = [decimal]1000000000000
    'KiB' = [decimal]1024
    'MiB' = [decimal]1048576
    'GiB' = [decimal]1073741824
    'TiB' = [decimal]1099511627776
}
$script:SizePattern = '^\s*(?<number>\d+(?:\.\d+)?)\s*(?<unit>[A-Za-z]*)\s*$'

function Get-SizeErrorRecord {
    param(
        [string] $Size,
        [string] $ErrorId,
        [System.Management.Automation.ErrorCategory] $Category,
        [string] $Reason
    )

    [System.Management.Automation.ErrorRecord]::new(
        [System.ArgumentException]::new("Invalid size '$Size': $Reason"), $ErrorId, $Category, $Size)
}

function ConvertFrom-ByteSize {
    <#
    .SYNOPSIS
    Converts a size such as '1.5 GiB' or '200 KB' to a number of bytes.

    .PARAMETER Size
    A non-negative number with an optional unit: B, KB, MB, GB, TB (powers of 1000) or KiB, MiB, GiB, TiB (powers of 1024).

    .EXAMPLE
    '1.5 GiB', '200 KB' | ConvertFrom-ByteSize
    #>
    [CmdletBinding()]
    [OutputType([long])]
    param(
        [Parameter(Mandatory, ValueFromPipeline)]
        [AllowEmptyString()]
        [string] $Size
    )

    process {
        $match = [regex]::Match($Size, $script:SizePattern)
        if (-not $match.Success -or -not $script:Multipliers.ContainsKey($match.Groups['unit'].Value)) {
            $PSCmdlet.WriteError((Get-SizeErrorRecord -Size $Size -ErrorId 'ByteSize.InvalidFormat' -Category InvalidData `
                        -Reason 'expected a number and an optional unit.'))
            return
        }
        $multiplier = $script:Multipliers[$match.Groups['unit'].Value]
        $number = [decimal]0
        # Above the bound, the number cannot fit in a long; below it, the product cannot overflow a decimal.
        $bound = ([decimal][long]::MaxValue + 1) / $multiplier
        $parsed = [decimal]::TryParse($match.Groups['number'].Value, 'AllowDecimalPoint', [cultureinfo]::InvariantCulture, [ref] $number)
        $bytes = if ($parsed -and $number -le $bound) { [decimal]::Round($number * $multiplier, [System.MidpointRounding]::AwayFromZero) }
        if ($null -eq $bytes -or $bytes -gt [long]::MaxValue) {
            $PSCmdlet.WriteError((Get-SizeErrorRecord -Size $Size -ErrorId 'ByteSize.OutOfRange' -Category InvalidArgument `
                        -Reason 'the size is larger than [long]::MaxValue bytes.'))
            return
        }
        [long] $bytes
    }
}

Export-ModuleMember -Function ConvertFrom-ByteSize
