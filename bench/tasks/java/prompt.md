Create a Java 21 library in this folder that parses human-written durations such as `1h30m` or `45s`.

Make it a Maven project at the folder root with groupId `com.example` and artifactId `durations`, and put the logic in the package `com.example.durations`, class `DurationParser`, method `public static java.time.Duration parse(String text)`. The text is one or more parts, each a non-negative decimal integer followed by a unit: `h` (hours), `m` (minutes) or `s` (seconds). Units appear at most once and in that order (`1h30m`, `2m5s` and `90m` are valid; `30m1h` and `1m2m` are not). `0s` is valid and returns a zero duration.

Throw an `IllegalArgumentException` for null, an empty or blank text, any whitespace, sign, decimal point or unknown unit, a number without a unit, a unit without a number, and a number too large to fit in a `Duration` without overflow.

Work autonomously: nobody will answer questions.
