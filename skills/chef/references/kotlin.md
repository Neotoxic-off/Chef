# Kotlin

Verified against Kotlin 2.4.21, Spotless 8.11.0, detekt 1.23.8 (2.0.0-alpha.6 next), Kover 0.9.11, Kotest 6.2.7, MockK 1.14.12 (Nov 2026).

Build with Gradle (Kotlin DSL), version catalog in `gradle/libs.versions.toml`, wrapper committed.

## Lint and format: ktlint (via Spotless), detekt

```kotlin
plugins {
    id("com.diffplug.spotless") version "8.11.0"
    id("io.gitlab.arturbosch.detekt") version "1.23.8"  // 2.x moves to id("dev.detekt")
    id("org.jetbrains.kotlinx.kover") version "0.9.11"
}

spotless { kotlin { ktlint() }; kotlinGradle { ktlint() } }

detekt {
    buildUponDefaultConfig = true
    config.setFrom("config/detekt.yml")
}

kotlin {
    explicitApi()
    compilerOptions {
        allWarningsAsErrors = true
        extraWarnings = true
    }
}
```

- Keep `.editorconfig` as the single source of style for ktlint and the IDE. Turn off the rule that contradicts explicit types:
  ```ini
  [*.{kt,kts}]
  # contradicts the house rule: explicit return types (`: Unit`)
  ktlint_standard_no-unit-return = disabled
  ```
- detekt fails on any finding by default (`maxIssues: 0`); do not raise it and never `@Suppress`: fix the cause, or ask the user.
- detekt 1.23.8 is built against Kotlin 2.0.21; on newer Kotlin expect some false positives. Upgrade to detekt 2.x (`dev.detekt`, built against Kotlin 2.4) once it is stable; it is alpha as of Nov 2026.

## Code

- Explicit types: `val count: Int = 0`, `fun name(): String`, typed lambda parameters `{ user: User -> user.id }` (see SKILL.md). `explicitApi()` enforces visibility and return types on the public API; type locals by hand.
- `val` over `var`; read-only collections (`List`, `Map`) in signatures.
- No `!!`. Model absence with nullable types and `?.`/`?:`; model failure with sealed result types or exceptions at the boundary.
- `data class` for values, `sealed interface` for closed hierarchies with exhaustive `when`.
- Coroutines: structured concurrency only, no `GlobalScope`. Inject `CoroutineDispatcher` and `Clock`; test with `kotlinx-coroutines-test` (`runTest`).
- Constructor injection; no top-level mutable state.

## Android

- Android Lint in CI as an error gate:
  ```kotlin
  android { lint { warningsAsErrors = true; abortOnError = true; checkDependencies = true } }
  ```
- Jetpack Compose UI, ViewModels hold state as `StateFlow`; no logic in composables or Activities.
- Local unit tests (JVM, Robolectric where Android APIs are needed); instrumented tests with `AndroidJUnit4` and Compose UI test for UI flows.
- Coverage per variant: `./gradlew koverVerifyDebug`. Exclude generated code (`*_Factory`, `Hilt_*`, `ComposableSingletons*`) in the Kover filters with a comment.

## Tests

- JUnit (Jupiter) with `kotlin-test` assertions or Kotest; MockK only at boundaries.
- Integration tests tagged `@Tag("integration")`, using Testcontainers.
- Coverage gate with Kover:
  ```kotlin
  kover { reports { verify { rule {
      minBound(90, kotlinx.kover.gradle.plugin.dsl.CoverageUnit.LINE)
      minBound(90, kotlinx.kover.gradle.plugin.dsl.CoverageUnit.BRANCH)
  } } } }
  ```
- Mutation testing: PIT via `info.solidsoft.pitest`. Without a Kotlin-aware plugin (the commercial Arcmutate one), PIT reports junk mutants in compiler-generated code; review survivors before acting.

Order before done: `./gradlew spotlessApply` then `./gradlew detekt check koverVerify` (Android: `lint` and `koverVerifyDebug`).
