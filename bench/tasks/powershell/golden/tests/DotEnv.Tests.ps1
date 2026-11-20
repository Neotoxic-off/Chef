BeforeAll {
    Import-Module (Join-Path $PSScriptRoot '..' 'DotEnv.psd1') -Force

    function New-EnvFile([string] $Text) {
        $path = Join-Path $TestDrive "$([guid]::NewGuid()).env"
        [System.IO.File]::WriteAllText($path, $Text)
        $path
    }
}

Describe 'Read-DotEnv' {
    It 'reads names and values in file order' {
        $result = Read-DotEnv -Path (New-EnvFile "B=2`r`nA=1`r`n")

        @($result.Keys) | Should -Be @('B', 'A')
        $result['B'] | Should -BeExactly '2'
    }

    It 'reads <Line> as <Expected>' -ForEach @(
        @{ Line = '  KEY =  spaced  '; Expected = 'spaced' }
        @{ Line = 'KEY=a=b'; Expected = 'a=b' }
        @{ Line = 'KEY='; Expected = '' }
        @{ Line = 'KEY="x # y"'; Expected = 'x # y' }
        @{ Line = "KEY=' z '"; Expected = ' z ' }
        @{ Line = 'KEY=x # comment'; Expected = 'x' }
        @{ Line = 'KEY=x#y'; Expected = 'x#y' }
    ) {
        (Read-DotEnv -Path (New-EnvFile "# header`n`n$Line`n"))['KEY'] | Should -BeExactly $Expected
    }

    It 'keeps the last value of a duplicate name' {
        $result = Read-DotEnv -Path (New-EnvFile "A=1`nA=2")

        $result.Count | Should -Be 1
        $result['A'] | Should -BeExactly '2'
    }

    It 'throws DotEnv.FileNotFound for a missing file' {
        { Read-DotEnv -Path (Join-Path $TestDrive 'none.env') } |
            Should -Throw -ErrorId 'DotEnv.FileNotFound,Read-DotEnv'
    }

    It 'throws DotEnv.InvalidLine with the line number for <Line>' -ForEach @(
        @{ Line = 'NO_EQUALS' }
        @{ Line = '=value' }
        @{ Line = '9NAME=1' }
    ) {
        { Read-DotEnv -Path (New-EnvFile "# header`n`n$Line") } |
            Should -Throw -ErrorId 'DotEnv.InvalidLine,Read-DotEnv' -ExpectedMessage '*line 3*'
    }
}
