Write a Kotlin 2.4 JVM library with `fun parseDuration(text: String): kotlin.time.Duration` accepting forms like `1h30m`, `45s`, `2d4h` (units d, h, m, s, each at most once, in that order). Empty input, unknown units, repeated or out-of-order units throw `IllegalArgumentException` naming the input. Gradle build.

Work autonomously: nobody will answer questions.
