# Objective-C

ARC on (`CLANG_ENABLE_OBJC_ARC = YES`). New code in an Apple project is usually Swift (see `swift.md`); write Objective-C only where the project already does. Check the toolchain with `xcodebuild -version` and `clang --version`. Verified against Xcode 27.2, clang-format 23.1 (Nov 2026).

## Lint and format: clang-format, Clang Static Analyzer, clang-tidy

`.clang-format`:

```yaml
---
Language: ObjC
BasedOnStyle: Google
ColumnLimit: 100
ObjCBlockIndentWidth: 4
```

CI: `clang-format --dry-run --Werror` on every `.h`/`.m`.

Build settings (`.xcconfig`, committed):

```
GCC_TREAT_WARNINGS_AS_ERRORS = YES
CLANG_WARN_OBJC_IMPLICIT_RETAIN_SELF = YES
RUN_CLANG_STATIC_ANALYZER = YES
WARNING_CFLAGS = -Wall -Wextra -Wshadow -Wconversion -Wnullable-to-nonnull-conversion
```

CI also runs `xcodebuild analyze` (Clang Static Analyzer) and fails on any finding. If the build has a compilation database (CMake), add clang-tidy with `objc-*`, `bugprone-*`, `clang-analyzer-*`. Never `#pragma clang diagnostic ignored`.

## Code

- Explicit types on declarations, as ObjC code is written: `NSInteger count = 0;`. Never `__auto_type`.
- Lightweight generics on every collection: `NSArray<NSString *> *names`, `NSDictionary<NSString *, NSNumber *> *totals`.
- Wrap every header in `NS_ASSUME_NONNULL_BEGIN` / `NS_ASSUME_NONNULL_END`; mark the exceptions `nullable`.
- `id` only for truly untyped values; prefer `id<Protocol>`.
- Properties: `copy` for `NSString`, blocks and value collections; `weak` for delegates; `nonatomic` unless you need atomic access.
- `weakSelf`/`strongSelf` in blocks that self retains.
- Name constants: `static const NSTimeInterval kRequestTimeout = 30.0;` or `NS_ENUM` / `NS_OPTIONS`.
- Errors: return `BOOL` or `nil` and fill an `NSError **` out parameter; callers check the return value, not the error. `@throw` only for programmer errors; never `@try`/`@catch` for control flow.
- Inject dependencies (network session, clock, file manager) through the initializer.
- Prefix classes with a three-letter project prefix.
- Doc comments (`///`) only on a framework's public headers used by other projects.

## Tests

- XCTest. Method names start with `test` and state the behavior:
  ```objc
  - (void)testWithdrawWithInsufficientFundsReturnsError {
      NSError *error = nil;
      BOOL success = [self.account withdraw:kOverdraftAmount error:&error];
      XCTAssertFalse(success);
      XCTAssertEqual(error.code, AccountErrorInsufficientFunds);
  }
  ```
- Fakes through protocols you own; OCMock only if the project already uses it.
- Coverage: `xcodebuild test -enableCodeCoverage YES -resultBundlePath build/Tests.xcresult`, then `xcrun xccov view --report --json build/Tests.xcresult`. Fail CI when `lineCoverage` is under 0.9. xccov reports line coverage only.
- Run tests under Address and Undefined Behavior Sanitizers in a CI scheme.

Order before done: `clang-format` then build (warnings are errors) then `xcodebuild analyze` then `xcodebuild test`.
