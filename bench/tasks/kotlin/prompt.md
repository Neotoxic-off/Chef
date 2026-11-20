Create a Kotlin/JVM library in this folder that splits one line of CSV into its fields, for an import job.

Make it a Gradle project at the folder root (Kotlin DSL, building with Gradle 9.9 on JDK 21) with JUnit 5 tests, and put a top-level function `fun parseCsvLine(line: String): List<String>` in the package `com.example.csv`. Fields are separated by commas. A field may be wrapped in double quotes, and then it may contain commas, and a doubled quote `""` inside it stands for one quote. Return every field in order, empty ones included: `a,,b` gives `["a", "", "b"]`, a trailing comma gives a trailing empty field, and an empty line gives one empty field. Spaces are part of the field, and the line never contains a line break.

Throw an `IllegalArgumentException` for a quoted field without its closing quote, a quote inside an unquoted field (`a"b`), and any character between a closing quote and the next comma (`"a"b`).

Work autonomously: nobody will answer questions.
