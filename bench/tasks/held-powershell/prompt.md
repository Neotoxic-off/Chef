Write a PowerShell 7 module `ByteSize` at the root of this folder (`ByteSize.psm1`, plus a `ByteSize.psd1` manifest if you want one) that exports only the function `ConvertFrom-ByteSize`, with a mandatory `-Size` parameter (string) that also takes pipeline input, and returns each size in bytes as a `[long]`, one result per input, in input order.

Format: leading and trailing whitespace is ignored; a size is a non-negative decimal number (digits, optionally followed by `.` and at least one digit, with `.` as the separator whatever the current culture), optional whitespace, then an optional case-insensitive unit: none or `B` (1), `KB`, `MB`, `GB`, `TB` (powers of 1000), `KiB`, `MiB`, `GiB`, `TiB` (powers of 1024). A fractional result is rounded to the nearest byte, halves away from zero (`2.5 B` is 3).

Errors are non-terminating: a bad input writes one error and processing goes on with the next input. An empty, blank or otherwise malformed input (sign, exponent, unknown unit, missing number) gives the error ID `ByteSize.InvalidFormat` with the category `InvalidData`; a well-formed size whose rounded result is above `[long]::MaxValue` gives the error ID `ByteSize.OutOfRange` with the category `InvalidArgument`. Both messages contain the input in single quotes. Test it with Pester 5.

Work autonomously: nobody will answer questions.
