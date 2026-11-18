# Monorepos (pnpm workspaces, Turborepo, Nx, Bazel, Gradle)

## Lint and validate

- Run every gate only on what changed, but run all of it: `turbo run lint test build --affected`, `nx affected -t lint test build`, `pnpm -r --filter "...[origin/main]" run test`.
- Nx: `nx sync:check` in CI fails when generated project config is stale.
- Turborepo: `turbo boundaries` checks package imports (experimental).
- Bazel: `buildifier --lint=warn --mode=check -r .`; `bazel mod tidy` keeps `MODULE.bazel` clean.
- Gradle: `./gradlew check --warning-mode=fail`; warnings are errors.
- Validate tool config against SchemaStore schemas (`turbo.json`, `pnpm-workspace.yaml`, see `config-files.md`).

## Practices

- Versions checked Nov 2026: pnpm 11 and 12, Turborepo 2.11, Nx 23, Bazel 9.3 (9.x LTS), Gradle 9.9. Check `<tool> --version` and each GitHub releases page or changelog.
- Pick the smallest tool that fits: pnpm workspaces alone for a few JS packages; add Turborepo or Nx for caching and task graphs; Bazel for large polyglot repos with hermetic builds; Gradle multi-project for JVM.
- Pin the tool: `packageManager` field in `package.json` (Corepack), `.bazelversion` (Bazelisk), Gradle wrapper with `distributionSha256Sum`.
- One lockfile at the root, committed. CI installs frozen: `pnpm install --frozen-lockfile`.
- Internal deps use `workspace:*`; shared versions in pnpm `catalog:` entries in `pnpm-workspace.yaml`.
- pnpm 11+: settings live in `pnpm-workspace.yaml`, `.npmrc` is for auth and registry only.
- Declare task inputs and outputs (`turbo.json` `tasks.<name>.outputs`, Nx `inputs`/`outputs`) so the cache is correct; a wrong cache hit is worse than a slow build.
- Enforce module boundaries: Nx `@nx/enforce-module-boundaries` lint rule with tags; Bazel `visibility`; Gradle `api` vs `implementation`.
- Bazel 9: Bzlmod only (`MODULE.bazel`); `WORKSPACE` support is removed. Load C++ rules from `@rules_cc`.
- Gradle: version catalog in `gradle/libs.versions.toml`, convention plugins in `build-logic` (not `allprojects {}`), configuration cache on (`org.gradle.configuration-cache=true`).

```yaml
packages:
  - "apps/*"
  - "packages/*"
catalog:
  typescript: <exact version from npm view typescript version>
minimumReleaseAge: 1440
```

## Security

- Remote cache is code execution: authenticate it, scope tokens to read-only for PRs from forks, and sign artifacts where supported (Turborepo `remoteCache.signature` with a 32-byte+ `TURBO_REMOTE_CACHE_SIGNATURE_KEY`).
- pnpm 11 waits 1440 minutes before installing a new release (`minimumReleaseAge`); keep it. Allow build scripts only for named packages (`allowBuilds`; pnpm 10: `onlyBuiltDependencies`); never `dangerouslyAllowAllBuilds`.
- Gradle: dependency verification (`./gradlew --write-verification-metadata sha256 help`, commit `gradle/verification-metadata.xml`).
- Bazel: pin every external dependency by version and integrity hash in `MODULE.bazel`.
- CODEOWNERS per package; secrets per app, never in a shared package.

## Tests

- CI runs affected `lint`, `test` and `build` on every PR, and the full set on `main` on a schedule to catch cache or graph mistakes.
- Each package has its own tests and runs alone (`pnpm --filter <pkg> test`, `bazel test //pkg/...`, `./gradlew :pkg:test`).
- Check the cache: a second CI run with no changes must be all cache hits.
