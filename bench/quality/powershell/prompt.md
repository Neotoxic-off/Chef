Write a PowerShell 7.6 module `LogTools` exporting `Get-LogSummary -Path <string>` that reads a log file with lines like `2026-11-02T10:15:00Z ERROR message`, and returns one object per level with `Level`, `Count`, `First` and `Last` (`[datetimeoffset]`). Lines that do not match are counted in a `Malformed` property of a final summary object. A missing file writes a terminating error.

Work autonomously: nobody will answer questions.
