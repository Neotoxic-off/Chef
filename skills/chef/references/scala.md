# Scala

Scala 3 with sbt (or Mill). Pin plugin versions in `project/plugins.sbt`.

## Lint and format: scalafmt + scalafix

`.scalafmt.conf`:

```hocon
version = "3.11.5"
runner.dialect = scala3
maxColumn = 100
rewrite.rules = [RedundantBraces, RedundantParens, SortModifiers, Imports]
rewrite.imports.sort = scalastyle
```

`.scalafix.conf`:

```hocon
rules = [ExplicitResultTypes, RemoveUnused, OrganizeImports, DisableSyntax, NoValInForComprehension]
DisableSyntax.noVars = true
DisableSyntax.noNulls = true
DisableSyntax.noReturns = true
DisableSyntax.noThrows = true
```

`build.sbt`:

```scala
ThisBuild / semanticdbEnabled := true
scalacOptions ++= Seq("-deprecation", "-feature", "-unchecked", "-Wunused:all", "-Wvalue-discard")
scalacOptions ++= (if (insideCI.value) Seq("-Werror") else Nil)  // scalafix must run without -Werror locally
```

`-Werror` replaces the deprecated `-Xfatal-warnings`. CI runs `sbt scalafmtCheckAll scalafmtSbtCheck "scalafixAll --check"`.

## Code

- Explicit types (see SKILL.md): `val count: Int = 0`, `def find(id: UserId): Option[User]`, `(x: Int) => x + 1`. Scalafix `ExplicitResultTypes` adds missing result types.
- `val` only, no `var`. Immutable collections. No `null`: use `Option`.
- Errors as values: `Either[DomainError, A]` or the effect's error channel. Throw only for bugs.
- Model data with `case class` and closed hierarchies with `enum` or `sealed trait`. Match exhaustively.
- Opaque types for IDs and units: `opaque type UserId = Long`.
- Inject dependencies through constructor parameters (traits as ports). No global `object` holding state.
- `given`/`using` for type classes and context, not for hiding ordinary dependencies.

## Tests

- munit (or ScalaTest `AnyFunSuite`). Property tests with ScalaCheck (`munit-scalacheck`).
- Integration tests in a separate sbt config or subproject, with testcontainers-scala.
- Coverage: sbt-scoverage, line and branch gate:
  ```scala
  coverageMinimumStmtTotal := 90
  coverageMinimumBranchTotal := 90
  coverageFailOnMinimum := true
  ```
  Run `sbt clean coverage test coverageReport`.
- Mutation testing: stryker4s (`sbt-stryker4s`, run `sbt stryker`). Fail on a low score: `strykerThresholdsBreak := 80`.

Order before done: `sbt scalafmtAll scalafixAll` then `sbt compile` then `sbt coverage test coverageReport`.
