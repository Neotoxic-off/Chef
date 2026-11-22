# Kotlin

Written for Kotlin 2.4.21, Spotless 8.11.0, detekt 2.0.0-alpha.6, Kover 0.9.11, Kotest 6.2.7, MockK 1.14.12 (Nov 2026), not benchmarked.

Build with Gradle (Kotlin DSL), version catalog in `gradle/libs.versions.toml`, wrapper committed.

## Lint and format: ktlint (via Spotless), detekt

```kotlin
plugins {
    id("com.diffplug.spotless") version "8.11.0"
    id("dev.detekt") version "2.0.0-alpha.6"
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

- Keep `.editorconfig` as the single source of style for ktlint and the IDE.
- detekt fails on any finding by default (`failOnSeverity = Error`); never lower it, set `ignoreFailures` or `@Suppress`: fix the cause, or ask the user.
- detekt must match the project's Kotlin: 1.23.8 is built for Kotlin 2.0.21; Kotlin 2.4 needs the 2.0.0 alphas (prereleases; alpha.5 needs Gradle 9.5+ and JDK 25). Check the compatibility table at detekt.dev before changing either version.

## Code

- `explicitApi()` enforces visibility and return types on the public API; let locals and lambda parameters infer when the type is obvious.
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
