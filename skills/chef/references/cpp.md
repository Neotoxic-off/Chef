# C++

Build with CMake and `CMakePresets.json` (committed). Target C++20 or later. Every CI job uses a preset. Written for CMake 4.5, LLVM (clang-tidy, clang-format) 23.1, gcovr 8.8, GoogleTest 1.18, Catch2 3.16, Mull 0.39 (Nov 2026), not benchmarked.

## Lint and format: clang-tidy, clang-format

`.clang-tidy`:

```yaml
Checks: >
  -*, bugprone-*, cert-*, clang-analyzer-*, concurrency-*, cppcoreguidelines-*,
  misc-*, modernize-*, performance-*, portability-*, readability-*,
  -modernize-use-trailing-return-type
WarningsAsErrors: '*'
HeaderFilterRegex: '^(src|include)/'
CheckOptions:
  readability-function-cognitive-complexity.Threshold: 10
```

`.clang-format`: `BasedOnStyle: Google` (or the project's style), `ColumnLimit: 100`. CI runs `clang-format --dry-run --Werror` and `clang-tidy -p build`.

## Warnings as errors: CMake presets

```json
{
  "version": 6,
  "configurePresets": [
    { "name": "dev", "binaryDir": "build/${presetName}",
      "cacheVariables": { "CMAKE_CXX_STANDARD": "20", "CMAKE_EXPORT_COMPILE_COMMANDS": "ON",
                          "CMAKE_COMPILE_WARNING_AS_ERROR": "ON" } },
    { "name": "asan", "inherits": "dev",
      "cacheVariables": { "CMAKE_CXX_FLAGS": "-fsanitize=address,undefined -fno-omit-frame-pointer" } },
    { "name": "coverage", "inherits": "dev", "cacheVariables": { "CMAKE_CXX_FLAGS": "--coverage" } }
  ]
}
```

- Warnings per target: `-Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow` (GCC/Clang), `/W4 /permissive-` (MSVC). `CMAKE_COMPILE_WARNING_AS_ERROR` adds `-Werror` / `/WX` (CMake 3.24+).
- Run the test suite under ASan+UBSan in CI; add a TSan job for threaded code.

## Code

- `auto` when the type is spelled on the right side or cannot be named (lambdas, iterators, structured bindings); explicit types otherwise.
- RAII for every resource. No raw `new`/`delete`: `std::unique_ptr`, `std::make_unique`, containers.
- `const` and `constexpr` by default. Pass large inputs by `const&`, sinks by value then `std::move`.
- No C casts, no `using namespace` in headers, no macros for constants (`constexpr`).
- Errors: exceptions or `std::expected` (C++23), one policy per project. Mark result-returning functions `[[nodiscard]]`.
- Inject I/O and time through abstract interfaces or template parameters.

## Tests

- GoogleTest (with GoogleMock) or Catch2 v3, registered with CTest (`gtest_discover_tests` / `catch_discover_tests`).
- Integration tests in a separate CTest label (`LABELS integration`); run with `ctest --preset dev -L integration`.
- Coverage on the `coverage` preset with gcovr (GCC gcov or `--gcov-executable "llvm-cov gcov"` for Clang):
  ```sh
  gcovr --root . --filter src/ --fail-under-line 90 --fail-under-branch 90
  ```
- Branch numbers from gcov include compiler-generated exception branches; add `--exclude-throw-branches` rather than lower the gate.
- Mutation testing: Mull (LLVM-based, the Mull build must match your Clang major version).
- Fuzz parsers with libFuzzer (`-fsanitize=fuzzer,address`).

Order before done: `clang-format` then `clang-tidy` then build (`dev` preset) then `ctest` on `asan` and `coverage` presets.

No compiler or LLVM tools installed: there is no official clang image; `silkeh/clang:22` has clang, clang-format and clang-tidy 22 with CMake 3.31 (1.8 GB). One call, `--user` so the build is not owned by root: `MSYS_NO_PATHCONV=1 docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/w" -w /w silkeh/clang:22 sh -c 'rc=0; f=$(find src include tests -name "*.[ch]pp"); clang-format --dry-run --Werror $f || rc=1; { cmake --preset asan && cmake --build --preset asan && ctest --preset asan; } || rc=1; clang-tidy -p build/asan --quiet $f || rc=1; exit $rc'`. Its LLVM is 22, not 23: CI must use the same major, or clang-format output differs.
