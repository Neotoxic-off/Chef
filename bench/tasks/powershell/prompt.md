Write a PowerShell 7 module `DotEnv` at the root of this folder (`DotEnv.psm1`, plus a `DotEnv.psd1` manifest if you want one) that exports only the function `Read-DotEnv`, with a mandatory `-Path` parameter (string) to a `.env` file, and returns its variables as an ordered dictionary, in file order.

Format: the file may use LF or CRLF line endings. Blank lines and lines whose first non-blank character is `#` are skipped; every other line is `NAME=value`, where `NAME` matches `[A-Za-z_][A-Za-z0-9_]*`, the value runs to the end of the line and may contain `=`, and whitespace around the name and the value is trimmed. A value wrapped in single or double quotes loses the quotes and is kept as is inside them, `#` and spaces included; in an unquoted value, a `#` preceded by whitespace starts a comment that is dropped. When a name appears twice, the last value wins.

Errors are terminating: a missing file gives the error ID `DotEnv.FileNotFound` with the category `ObjectNotFound`; any other malformed line gives the error ID `DotEnv.InvalidLine` with the category `InvalidData` and a message that contains `line <n>`, the 1-based line number in the file. Test it with Pester 5.

Work autonomously: nobody will answer questions.
