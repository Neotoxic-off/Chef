# Java and Spring Boot upgrade with OpenRewrite

Builds on `java.md` (and `spring-boot.md` for Spring code). Verified against the OpenRewrite docs ("Migrate to Java 21/25", "Migrate to Spring Boot 3.x", plugin references), the Spring Boot 4.0 migration guide, OpenJDK JEPs, and Maven Central: rewrite-maven-plugin 6.46.1, Gradle plugin `org.openrewrite.rewrite` 7.41.0, rewrite-migrate-java 3.42.1, rewrite-spring 6.37.1 (Nov 2026).

## When it applies

- Java 8, 11 or 17 code moving to 21 or 25 (both LTS), or a Spring Boot major (2.x to 3.x, 3.x to 4.0).
- Spring Boot 3 needs Java 17+; Spring Boot 4.0 needs Java 17+, Jakarta EE 11 and Spring Framework 7. Upgrade Java first, then Spring Boot.

## Access: ask the user first

New OpenRewrite releases (plugins included) are published to the Code Genome Project repository (`https://artifacts.codegenomeproject.org/maven`), which needs a sign-in and a download token. `rewrite-migrate-java` and `rewrite-spring` are under the Moderne Source Available License, the Maven Central releases too; current binaries need a Moderne subscription. Earlier releases stay on Maven Central; the newest there are the versions above (Aug 2026), and they contain every recipe below. For Spring recipes, swap the coordinates to `org.openrewrite.recipe:rewrite-spring:6.37.1`. Ask the user which source and license fits before running anything.

## Recipes

| Goal | Recipe | Module |
|---|---|---|
| Java 17 / 21 / 25 | `org.openrewrite.java.migrate.UpgradeToJava17` / `UpgradeToJava21` / `UpgradeToJava25` | `rewrite-migrate-java` |
| Spring Boot 3.5 | `org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_5` | `rewrite-spring` |
| Spring Boot 4.0 | `org.openrewrite.java.spring.boot4.UpgradeSpringBoot_4_0` | `rewrite-spring` |

The recipes are composites: they also bump build plugins, dependencies and deprecated APIs. List what a version holds with `mvn rewrite:discover` / `gradle rewriteDiscover`.

Maven, without editing the POM:

```sh
mvn -U org.openrewrite.maven:rewrite-maven-plugin:6.46.1:dryRun \
  -Drewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-migrate-java:3.42.1 \
  -Drewrite.activeRecipes=org.openrewrite.java.migrate.UpgradeToJava21
```

Read `target/rewrite/rewrite.patch` (Gradle: `build/reports/rewrite/rewrite.patch`), then run the same command with `:run`. Gradle: plugin `id("org.openrewrite.rewrite")`, `rewrite { activeRecipe("...") }`, `dependencies { rewrite("org.openrewrite.recipe:rewrite-migrate-java:3.42.1") }`, then `./gradlew rewriteDryRun` and `./gradlew rewriteRun`.

## Steps, one batch per commit

1. Baseline on the old JDK: `./gradlew check` (or `mvn verify`) run, failures and coverage recorded.
2. Upgrade build tools and plugins that the new JDK needs (Gradle, JaCoCo, Error Prone, Lombok, Mockito) on the old JDK.
3. One Java LTS per batch (8 to 11 to 17 to 21 to 25): dry run, read the patch, run, build and test on the new JDK, set the toolchain version.
4. Spring Boot: first the latest 3.5.x, then `UpgradeSpringBoot_4_0`. One module per batch in a multi-module build if the patch is large.
5. After the recipe, fix the remaining compile errors and test failures by hand.

Validation per batch: `./gradlew spotlessCheck check` (or `mvn verify`) on the target JDK; the coverage gate stays at 90%.

## Pitfalls

- Java 11 removed the Java EE and CORBA modules (JEP 320): add JAXB, JAX-WS, `javax.annotation` as dependencies (new dependencies: ask the user first).
- Java 17 strongly encapsulates JDK internals (JEP 403): `--illegal-access` no longer works; libraries using reflection on internals need upgrades.
- Java 24 permanently disables the Security Manager (JEP 486) and warns on `sun.misc.Unsafe` memory access (JEP 498).
- Spring Boot 3: `javax.*` to `jakarta.*`. Spring Boot 4: modular starters, Jackson 3 (`com.fasterxml.jackson` to `tools.jackson`, except `jackson-annotations`), Spock integration removed.
- Read the patch before `run`: revert any change the migration does not need (unrelated formatting, extra cleanups), so the diff holds only the migration.

## Leave for the user

- Repository access, token and license for OpenRewrite artifacts.
- Target choice (21 vs 25, Boot 3.5 vs 4.0) and libraries with no compatible version.
- `--add-opens` flags: report the library that needs one; do not add them silently.
