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
      "cacheVariables": { "CMAKE_CXX_STANDARD": "20", "CMAKE_EXPORT_COMPILE_COMMANDS": "ON" } },
    { "name": "asan", "inherits": "dev",
      "cacheVariables": { "CMAKE_CXX_FLAGS": "-fsanitize=address,undefined -fno-omit-frame-pointer" } },
    { "name": "coverage", "inherits": "dev", "cacheVariables": { "CMAKE_CXX_FLAGS": "--coverage" } }
  ]
}
```

- Warnings per target: `-Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow` (GCC/Clang), `/W4 /permissive-` (MSVC). Make them errors on your own targets: `set_target_properties(app PROPERTIES COMPILE_WARNING_AS_ERROR ON)` (CMake 3.24+, adds `-Werror` / `/WX`). Not the global `CMAKE_COMPILE_WARNING_AS_ERROR`: it also reaches FetchContent dependencies, whose warnings you cannot fix (GoogleTest 1.17 does not build with it under Clang 22).
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

## Pitfalls

- A class whose members point into each other (a `std::list` plus a map of its iterators, a pointer into its own buffer) cannot follow the rule of zero: the default copy points into the source. Define copy and move and test a copy, or `= delete` them.
- Strong exception guarantee: do every step that can throw (allocation, copying a key) before the first change to the object's state.
- FetchContent: pin `URL` with `URL_HASH SHA256=...`, or `GIT_TAG` with a commit SHA. Add tests only `if(PROJECT_IS_TOP_LEVEL)` (CMake 3.21+), so a project that consumes the library neither downloads nor builds them.

Order before done: `clang-format` then `clang-tidy` then build (`dev` preset) then `ctest` on `asan` and `coverage` presets.

No compiler or LLVM tools installed: there is no official clang image; `silkeh/clang:22` has clang, clang-format and clang-tidy 22 with CMake 3.31 (1.8 GB). One call, `--user` so the build is not owned by root: `export MSYS_NO_PATHCONV=1; src=$PWD; command -v cygpath >/dev/null && src=$(cygpath -m "$PWD"); docker run --rm --user "$(id -u):$(id -g)" -v "$src:/w" -w /w silkeh/clang:22 sh -c 'rc=0; f=$(find src include tests \( -name "*.[ch]pp" -o -name "*.h" -o -name "*.cc" \)); clang-format --dry-run --Werror $f || rc=1; { cmake --preset asan && cmake --build --preset asan && ctest --preset asan; } || rc=1; clang-tidy -p build/asan --quiet $f || rc=1; exit $rc'`. Its LLVM is 22, not 23: CI must use the same major, or clang-format output differs.
