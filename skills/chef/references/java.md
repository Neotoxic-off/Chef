# Java

Build with Gradle (Kotlin DSL) and the wrapper committed. Use the project's LTS JDK through a toolchain (`java { toolchain { languageVersion = JavaLanguageVersion.of(25) } }`). Maven projects use the same tools through their Maven plugins.

## Lint and format: Spotless, Error Prone, NullAway, PMD

```kotlin
plugins {
    java
    jacoco
    id("com.diffplug.spotless") version "8.11.0"
    id("net.ltgt.errorprone") version "5.2.0"
    pmd
}

spotless { java { googleJavaFormat(); formatAnnotations() } }

dependencies {
    errorprone("com.google.errorprone:error_prone_core:2.53.0")
    errorprone("com.uber.nullaway:nullaway:0.14.4")
}

tasks.withType<JavaCompile>().configureEach {
    options.compilerArgs.addAll(listOf("-Xlint:all", "-Werror"))
    options.errorprone.error("NullAway")
    options.errorprone.option("NullAway:AnnotatedPackages", "com.example")
}

pmd { isConsoleOutput = true; ruleSetFiles = files("config/pmd.xml"); ruleSets = listOf() }
```

- `-Xlint:all -Werror` makes javac and Error Prone warnings fail the build.
- `config/pmd.xml` includes `category/java/codestyle.xml/UseExplicitTypes` to reject `var`, plus `bestpractices`, `errorprone` and `design` categories.
- CI runs `./gradlew spotlessCheck check`.

## Code

- Explicit types, never `var`: `List<String> names = new ArrayList<String>();` and typed lambda parameters `(String name) -> name.length()` (see SKILL.md).
- Nullness: annotate with JSpecify (`@NullMarked` packages, `@Nullable` where null is allowed). Return `Optional` instead of null from lookups; never `Optional` fields or parameters.
- Immutable data: `record`. Closed hierarchies: `sealed` interfaces with pattern-matching `switch`.
- `final` fields, constructor injection, no field injection, no static mutable state.
- Checked exceptions only where the caller can recover; wrap with context, never catch `Exception` to ignore it.
- `try`-with-resources for every `AutoCloseable`. `java.time` with an injected `Clock`.

## Tests

- JUnit (Jupiter) with AssertJ; Mockito only at boundaries.
- Integration tests in a separate source set or tagged `@Tag("integration")`, using Testcontainers.
- Coverage gate with JaCoCo:
  ```kotlin
  tasks.jacocoTestCoverageVerification {
      violationRules { rule {
          limit { counter = "LINE"; minimum = "0.90".toBigDecimal() }
          limit { counter = "BRANCH"; minimum = "0.90".toBigDecimal() }
      } }
  }
  tasks.check { dependsOn(tasks.jacocoTestCoverageVerification) }
  ```
- Mutation testing: PIT (`id("info.solidsoft.pitest")`, `junit5PluginVersion`, `mutationThreshold`) on critical packages.

Order before done: `./gradlew spotlessApply` then `./gradlew check` (compile with Error Prone, PMD, tests, coverage gate).
