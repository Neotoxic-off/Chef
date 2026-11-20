# Dart / Flutter

Written for Dart 3.14.1, Flutter 3.50, very_good_analysis 11.0, coverage 1.16, very_good_cli 1.7, mocktail 1.0.5, mutation_test 1.8 (Nov 2026), not benchmarked.

## Lint and format: analyzer + very_good_analysis

`analysis_options.yaml` (add `very_good_analysis` as a dev dependency; plain Dart or a lighter set: `package:lints/recommended.yaml` or `package:flutter_lints/flutter.yaml`):

```yaml
include: package:very_good_analysis/analysis_options.yaml

analyzer:
  language:
    strict-casts: true
    strict-inference: true
    strict-raw-types: true
  exclude:
    - "**/*.g.dart"        # generated
    - "**/*.freezed.dart"  # generated
```

- very_good_analysis already sets the three strict language modes; keep them in the file so a switch to another rule set does not drop them.
- CI fails on every diagnostic: `dart analyze --fatal-infos` (warnings are fatal by default). Flutter: `flutter analyze` (fails on infos by default).
- Format: `dart format .`; CI: `dart format --output=none --set-exit-if-changed .`.

## Code

- Type public APIs and signatures (`Future<User> load(String id) async`); omit local variable types (`final count = 0;`).
- No `dynamic`. Decode JSON into `Map<String, Object?>` and narrow it right away with patterns or a typed `fromJson`.
- Sound null safety: no `!` unless a check right above proves non-null. Prefer `if (x case final T v)` and `switch` patterns.
- Immutable models: `final` fields, `const` constructors, `sealed class` for closed hierarchies with exhaustive `switch`.
- Flutter: widgets stay thin. State and logic live in a testable layer (Bloc/Cubit, Riverpod, or `ChangeNotifier`) that gets repositories through its constructor.
- Prefer `StatelessWidget` and `const` widgets. No logic in `build`.

## Tests

- Dart: `package:test`. Flutter: `flutter_test` with `testWidgets` and `WidgetTester`. Golden tests for key screens.
- Mock boundaries with `mocktail`. Do not mock the class under test.
- Integration tests: `integration_test` (from the Flutter SDK) in `integration_test/`, run with `flutter test integration_test`. Pure Dart: tag with `@Tags(['integration'])` and run with `dart test -t integration`.
- Coverage, Dart (`coverage` package, line gate):
  ```sh
  dart run coverage:test_with_coverage --branch-coverage --fail-under=90
  ```
- Coverage, Flutter: `flutter test --coverage --branch-coverage` writes `coverage/lcov.info`. Gate lines with `very_good test --coverage --min-coverage 90` (very_good_cli) or an lcov check. Gate branches from the `BRF`/`BRH` totals:
  ```sh
  awk -F: '/^BRF/{t+=$2}/^BRH/{h+=$2}END{exit !(t==0 || h*100/t>=90)}' coverage/lcov.info
  ```
- Exclude generated files from coverage with `// coverage:ignore-file` only in generated code.
- Mutation testing: `mutation_test` (`dart run mutation_test`) on critical logic.

Order before done: `dart format .` then `dart analyze --fatal-infos` (or `flutter analyze`) then `dart test` / `flutter test --coverage`.
