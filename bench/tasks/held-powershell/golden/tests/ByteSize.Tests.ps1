BeforeAll {
    Import-Module (Join-Path $PSScriptRoot '..' 'ByteSize.psd1') -Force
}

Describe 'ConvertFrom-ByteSize' {
    It 'converts <Size> to <Expected> bytes' -ForEach @(
        @{ Size = '0'; Expected = 0 }
        @{ Size = '12 B'; Expected = 12 }
        @{ Size = '1.5KB'; Expected = 1500 }
        @{ Size = ' 2 mib '; Expected = 2097152 }
        @{ Size = '1 TiB'; Expected = 1099511627776 }
        @{ Size = '2.5'; Expected = 3 }
        @{ Size = '1.1 MB'; Expected = 1100000 }
        @{ Size = '9223372036854775807'; Expected = [long]::MaxValue }
    ) {
        $result = ConvertFrom-ByteSize -Size $Size

        $result | Should -BeOfType ([long])
        $result | Should -Be $Expected
    }

    It 'reads the separator as . in a culture that uses ,' {
        $culture = [cultureinfo]::CurrentCulture
        try {
            [cultureinfo]::CurrentCulture = 'fr-FR'

            ConvertFrom-ByteSize -Size '1.5 KB' | Should -Be 1500
        } finally {
            [cultureinfo]::CurrentCulture = $culture
        }
    }

    It 'writes ByteSize.InvalidFormat for <Size>' -ForEach @(
        @{ Size = '' }
        @{ Size = '-1' }
        @{ Size = '1e3' }
        @{ Size = '.5' }
        @{ Size = '1 PB' }
        @{ Size = 'KB' }
    ) {
        { ConvertFrom-ByteSize -Size $Size -ErrorAction Stop } |
            Should -Throw -ErrorId 'ByteSize.InvalidFormat,ConvertFrom-ByteSize' -ExpectedMessage "*'$Size'*"
    }

    It 'writes ByteSize.OutOfRange for <Size>' -ForEach @(
        @{ Size = '9223372036854775808' }
        @{ Size = '8388608 TiB' }
        @{ Size = '99999999999999999999999999999999999999' }
    ) {
        { ConvertFrom-ByteSize -Size $Size -ErrorAction Stop } |
            Should -Throw -ErrorId 'ByteSize.OutOfRange,ConvertFrom-ByteSize' -ExpectedMessage "*'$Size'*"
    }

    It 'goes on with the next input after an error' {
        $result = @('1 KB', 'bad', '2 KB' | ConvertFrom-ByteSize -ErrorAction SilentlyContinue -ErrorVariable sizeErrors)

        $result | Should -Be @(1000, 2000)
        $sizeErrors.Count | Should -Be 1
    }
}
