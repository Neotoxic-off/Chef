BeforeAll {
    $manifest = Join-Path $env:BENCH_WORKSPACE 'ByteSize.psd1'
    $module = if (Test-Path -LiteralPath $manifest) { $manifest } else { Join-Path $env:BENCH_WORKSPACE 'ByteSize.psm1' }
    Import-Module $module -Force

    function Get-SizeError([string] $Size) {
        $output = @($Size | ConvertFrom-ByteSize -ErrorAction SilentlyContinue -ErrorVariable sizeErrors)
        $output.Count | Should -Be 0
        @($sizeErrors).Count | Should -Be 1
        $sizeErrors[0]
    }
}

Describe 'ConvertFrom-ByteSize contract' {
    It 'exports only ConvertFrom-ByteSize, with a mandatory string Size from the pipeline' {
        @((Get-Module ByteSize).ExportedFunctions.Keys) | Should -Be @('ConvertFrom-ByteSize')
        $parameter = (Get-Command ConvertFrom-ByteSize).Parameters['Size']
        $parameter.ParameterType | Should -Be ([string])
        $attributes = @($parameter.Attributes | Where-Object { $_ -is [System.Management.Automation.ParameterAttribute] })
        @($attributes | Where-Object Mandatory).Count | Should -BeGreaterThan 0
        @($attributes | Where-Object ValueFromPipeline).Count | Should -BeGreaterThan 0
    }

    It 'returns a long' {
        ConvertFrom-ByteSize -Size '0' | Should -BeOfType ([long])
        ConvertFrom-ByteSize -Size '1 KiB' | Should -BeOfType ([long])
    }

    It 'converts every unit' {
        $sizes = '7', '7B', '1KB', '1MB', '1GB', '1TB', '1KiB', '1MiB', '1GiB', '1TiB'
        $expected = 7, 7, 1000, 1000000, 1000000000, 1000000000000, 1024, 1048576, 1073741824, 1099511627776
        @($sizes | ConvertFrom-ByteSize) | Should -Be $expected
    }

    It 'ignores case and whitespace around and inside the size' {
        @('  1.5 kb ', "2`tMIB", '3kib', '4 b' | ConvertFrom-ByteSize) | Should -Be @(1500, 2097152, 3072, 4)
    }

    It 'rounds halves away from zero' {
        @('2.5 B', '0.5', '0.4', '1.0005 KB', '0.0001 KiB' | ConvertFrom-ByteSize) | Should -Be @(3, 1, 0, 1001, 0)
    }

    It 'is exact on decimal fractions' {
        ConvertFrom-ByteSize -Size '1.1 MB' | Should -Be 1100000
        ConvertFrom-ByteSize -Size '0.3 TB' | Should -Be 300000000000
    }

    It 'uses . as the separator whatever the current culture' {
        $culture = [cultureinfo]::CurrentCulture
        try {
            [cultureinfo]::CurrentCulture = 'de-DE'
            ConvertFrom-ByteSize -Size '1.5 KB' | Should -Be 1500
        } finally {
            [cultureinfo]::CurrentCulture = $culture
        }
    }

    It 'accepts the largest long and rejects one byte more' {
        ConvertFrom-ByteSize -Size '9223372036854775807' | Should -Be ([long]::MaxValue)
        $record = Get-SizeError '9223372036854775808'
        $record.FullyQualifiedErrorId | Should -BeLike 'ByteSize.OutOfRange*'
        $record.CategoryInfo.Category | Should -Be 'InvalidArgument'
        $record.Exception.Message | Should -BeLike "*'9223372036854775808'*"
    }

    It 'rejects <Size> as out of range' -ForEach @(
        @{ Size = '8388608 TiB' }
        @{ Size = '9223372036854775807.5' }
        @{ Size = '99999999999999999999999999999999999999 TB' }
    ) {
        (Get-SizeError $Size).FullyQualifiedErrorId | Should -BeLike 'ByteSize.OutOfRange*'
    }

    It 'rejects <Size> as an invalid format' -ForEach @(
        @{ Size = '' }
        @{ Size = '   ' }
        @{ Size = '-1 KB' }
        @{ Size = '+1' }
        @{ Size = '1e3' }
        @{ Size = '1,5 KB' }
        @{ Size = '.5 KB' }
        @{ Size = '5. KB' }
        @{ Size = '1 K' }
        @{ Size = '1 KiBs' }
        @{ Size = '1 PB' }
        @{ Size = 'KB' }
        @{ Size = '1 2 KB' }
    ) {
        $record = Get-SizeError $Size
        $record.FullyQualifiedErrorId | Should -BeLike 'ByteSize.InvalidFormat*'
        $record.CategoryInfo.Category | Should -Be 'InvalidData'
        $record.Exception.Message | Should -BeLike "*'$Size'*"
    }

    It 'goes on with the next input after an error' {
        $output = @('1KB', 'bad', '2KB' | ConvertFrom-ByteSize -ErrorAction SilentlyContinue -ErrorVariable sizeErrors)
        $output | Should -Be @(1000, 2000)
        @($sizeErrors).Count | Should -Be 1
    }
}
