# Swift / SwiftUI

Use `swift-tools-version: 6.2` or later so the package builds in the Swift 6 language mode, where data-race checks are errors. Verified against Swift 6.4.2, Xcode 27.2, SwiftLint 0.65.1, swift-format 604.0 (Nov 2026).

## Lint and format: SwiftLint + swift-format

`.swiftlint.yml`:

```yaml
strict: true  # warnings fail the run
opt_in_rules:
  - explicit_type_interface
  - force_unwrapping
  - implicitly_unwrapped_optional
  - empty_count
  - first_where
  - sorted_first_last
disabled_rules:
  - redundant_void_return  # contradicts the house rule: explicit return types (`-> Void`)
explicit_type_interface:
  allow_redundancy: true  # also require `let u: User = User()`
```

- Do not enable `redundant_type_annotation`: it fights `explicit_type_interface`.
- Run SwiftLint through `SwiftLintBuildToolPlugin` (package `SimplyDanny/SwiftLintPlugins`) or `swiftlint lint --strict` in CI.
- Format with swift-format, bundled with the toolchain since Swift 6: `swift format --in-place --recursive Sources Tests`; CI: `swift format lint --strict --recursive Sources Tests`. Turn on `NeverForceUnwrap`, `NeverUseForceTry` and `NeverUseImplicitlyUnwrappedOptionals` in `.swift-format`, and turn off `NoVoidReturnOnFunctionSignature` (it strips the explicit `-> Void` the house rules require; JSON has no comments, so say why in the README).

## Warnings as errors

```swift
swiftSettings: [.treatAllWarnings(as: .error)]  // SwiftPM 6.2+
```

Xcode: `SWIFT_TREAT_WARNINGS_AS_ERRORS = YES` and `GCC_TREAT_WARNINGS_AS_ERRORS = YES`. SwiftPM ignores these flags for remote dependencies.

## Code

- Explicit types: `let count: Int = 0`, `var names: [String] = []`, `func load(id: UUID) async throws -> User`.
- Value types (`struct`, `enum`) by default. Use `final class` only for identity or shared mutable state.
- No `!` force unwraps, `try!` or `as!` outside tests. Use `guard let ... else { throw ... }`.
- Concurrency: `async`/`await` and actors, not completion handlers or `DispatchQueue`. Mark UI types `@MainActor`. App targets: `.defaultIsolation(MainActor.self)`. Types crossing actors are `Sendable`. No `@unchecked Sendable` or `nonisolated(unsafe)` without a comment saying why.
- SwiftUI: views stay thin. Logic lives in `@Observable` models that take their services through `init` with protocol types.
- Errors are typed `enum`s conforming to `Error`. Never swallow them with `try?` when the failure matters.

## Tests

- Swift Testing (`import Testing`, `@Test`, `#expect`, `#require`) for new unit and integration tests. Use `@Test(arguments:)` for table cases and `.tags(.integration)` to split slow tests.
- Keep XCTest for UI tests (XCUITest) and performance tests. Do not mix both APIs in one test.
- Integration tests in their own test target, against real local services (Docker) or `URLProtocol` stubs at the network edge.
- Coverage: `swift test --enable-code-coverage`, then gate the JSON from `swift test --show-codecov-path`:
  ```sh
  jq -e '.data[0].totals.lines.percent >= 90' "$(swift test --show-codecov-path)"
  ```
  Xcode: `xcodebuild test -enableCodeCoverage YES -resultBundlePath R.xcresult`, then `xcrun xccov view --report --json R.xcresult` and fail when `lineCoverage < 0.9`.
- Swift coverage reports lines and regions, not true branches. Cover every `if`/`guard`/`switch` path with a test anyway.
- Mutation testing: Muter (`muter`) on critical logic.

Order before done: `swift format` then `swiftlint lint --strict` then `swift build` then `swift test --enable-code-coverage`.
