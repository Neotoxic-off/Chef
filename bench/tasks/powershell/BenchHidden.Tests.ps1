BeforeAll {
    $manifest = Join-Path $env:BENCH_WORKSPACE 'DotEnv.psd1'
    $module = if (Test-Path -LiteralPath $manifest) { $manifest } else { Join-Path $env:BENCH_WORKSPACE 'DotEnv.psm1' }
    Import-Module $module -Force

    function New-EnvFile([string] $Text) {
        $path = Join-Path $TestDrive "$([guid]::NewGuid()).env"
        [System.IO.File]::WriteAllText($path, $Text)
        $path
    }

    function Get-ReadError([string] $Path) {
        try {
            Read-DotEnv -Path $Path | Out-Null
        } catch {
            return $_
        }
        $null
    }
}

Describe 'Read-DotEnv contract' {
    It 'exports only Read-DotEnv, with a mandatory string Path' {
        @((Get-Module DotEnv).ExportedFunctions.Keys) | Should -Be @('Read-DotEnv')
        $parameter = (Get-Command Read-DotEnv).Parameters['Path']
        $parameter.ParameterType | Should -Be ([string])
        @($parameter.Attributes | Where-Object { $_ -is [System.Management.Automation.ParameterAttribute] -and $_.Mandatory }).Count |
            Should -BeGreaterThan 0
    }

    It 'returns an ordered dictionary in file order' {
        $result = Read-DotEnv -Path (New-EnvFile "ZED=1`nALPHA=2`nmid_3=3`n")
        $result | Should -BeOfType ([System.Collections.Specialized.OrderedDictionary])
        @($result.Keys) | Should -Be @('ZED', 'ALPHA', 'mid_3')
        $result['ALPHA'] | Should -Be '2'
    }

    It 'reads CRLF files without a trailing carriage return' {
        $result = Read-DotEnv -Path (New-EnvFile "A=1`r`nB=two`r`n")
        $result['B'] | Should -BeExactly 'two'
    }

    It 'skips blank and comment lines and trims names and values' {
        $result = Read-DotEnv -Path (New-EnvFile "  # comment`n`n   `n  NAME =  some value  `n")
        @($result.Keys) | Should -Be @('NAME')
        $result['NAME'] | Should -BeExactly 'some value'
    }

    It 'keeps = in values and allows empty values' {
        $result = Read-DotEnv -Path (New-EnvFile "URL=a=b=c`nEMPTY=`n")
        $result['URL'] | Should -BeExactly 'a=b=c'
        $result['EMPTY'] | Should -BeExactly ''
    }

    It 'keeps quoted values verbatim, # included' {
        $result = Read-DotEnv -Path (New-EnvFile "D=`"x # y`"`nS='  z  '`n")
        $result['D'] | Should -BeExactly 'x # y'
        $result['S'] | Should -BeExactly '  z  '
    }

    It 'drops a comment after whitespace in an unquoted value only' {
        $result = Read-DotEnv -Path (New-EnvFile "A=x # note`nB=x#y`nC=x`t# tab`n")
        $result['A'] | Should -BeExactly 'x'
        $result['B'] | Should -BeExactly 'x#y'
        $result['C'] | Should -BeExactly 'x'
    }

    It 'lets the last duplicate win' {
        $result = Read-DotEnv -Path (New-EnvFile "A=1`nA=2`n")
        $result.Count | Should -Be 1
        $result['A'] | Should -BeExactly '2'
    }

    It 'throws DotEnv.FileNotFound for a missing file' {
        $record = Get-ReadError (Join-Path $TestDrive 'missing.env')
        $record | Should -Not -BeNullOrEmpty
        $record.FullyQualifiedErrorId | Should -BeLike 'DotEnv.FileNotFound*'
        $record.CategoryInfo.Category | Should -Be 'ObjectNotFound'
    }

    It 'throws DotEnv.InvalidLine with the physical line number, comments and blanks counted' {
        $record = Get-ReadError (New-EnvFile "A=1`n`n# c`n1BAD=2`n")
        $record | Should -Not -BeNullOrEmpty
        $record.FullyQualifiedErrorId | Should -BeLike 'DotEnv.InvalidLine*'
        $record.CategoryInfo.Category | Should -Be 'InvalidData'
        $record.Exception.Message | Should -Match '\bline 4\b'
    }

    It 'rejects a line without = and a line without a name' {
        foreach ($text in "A=1`nNO_EQUALS`n", "=value`n", "BAD-NAME=1`n") {
            (Get-ReadError (New-EnvFile $text)).FullyQualifiedErrorId | Should -BeLike 'DotEnv.InvalidLine*'
        }
    }
}
