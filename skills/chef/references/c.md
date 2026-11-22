# C

Build with CMake and `CMakePresets.json` (committed). Target C17, or C23 where all compilers support it. Written for CMake 4.5, LLVM (clang-tidy, clang-format) 23.1, cppcheck 2.22, gcovr 8.8, Mull 0.39 (Nov 2026), not benchmarked.

## Lint and format: clang-tidy, clang-format

`.clang-tidy`:

```yaml
Checks: >
  -*, bugprone-*, cert-*, clang-analyzer-*, misc-*, performance-*,
  portability-*, readability-*,
  -clang-analyzer-security.insecureAPI.DeprecatedOrUnsafeBufferHandling
WarningsAsErrors: '*'
HeaderFilterRegex: '^(src|include)/'
CheckOptions:
  readability-function-cognitive-complexity.Threshold: 10
```

`.clang-format`: `BasedOnStyle: LLVM` (or the project's style), `ColumnLimit: 100`. CI runs `clang-format --dry-run --Werror` and `clang-tidy -p build`. Add `cppcheck --enable=warning,style,performance --error-exitcode=1` as a second opinion.

## Warnings as errors

In `CMakePresets.json`, set `"CMAKE_EXPORT_COMPILE_COMMANDS": "ON"` in the base preset. Per own target, `set_target_properties(app PROPERTIES COMPILE_WARNING_AS_ERROR ON)` (CMake 3.24+; not the global `CMAKE_COMPILE_WARNING_AS_ERROR`, which also reaches FetchContent dependencies) and:

```cmake
target_compile_options(app PRIVATE
  $<$<C_COMPILER_ID:GNU,Clang,AppleClang>:-Wall -Wextra -Wpedantic -Wconversion -Wshadow
    -Wstrict-prototypes -Wmissing-prototypes -Wformat=2 -Wnull-dereference>
  $<$<C_COMPILER_ID:MSVC>:/W4>)
```

Add an `asan` preset with `-fsanitize=address,undefined -fno-omit-frame-pointer` and run the tests under it in CI.

## Code

- Explicit types on every declaration: `size_t count = 0;` `uint32_t flags = 0U;`. Never C23 `auto` inference.
- Fixed-width types (`<stdint.h>`) for data with a size contract; `size_t` for sizes and indexes; `bool` from `<stdbool.h>`.
- Every function has a full prototype: `void f(void)`, never `void f()`. `static` for everything not in a header.
- Check every return value. Return error codes (an `enum`), output through pointer parameters.
- One owner per allocation. Free in the reverse order of acquisition, with a single cleanup path (`goto cleanup`).
- Pass buffers with their length. No `strcpy`, `sprintf`, `gets`; use `snprintf` and bounded copies.
- `const` on every pointer parameter you do not write through. No magic numbers: `enum` or `static const`.
- Inject I/O and time through function-pointer structs so tests can replace them.

## Tests

- Unity (ThrowTheSwitch) with CMock for mocks, registered with CTest. Integration tests under a separate CTest label.
- Coverage with gcovr on a `--coverage` preset:
  ```sh
  gcovr --root . --filter src/ --fail-under-line 90 --fail-under-branch 90
  ```
- Mutation testing: Mull (works on LLVM IR, so it handles C; match the Mull build to your Clang major version).
- Fuzz parsers with libFuzzer (`-fsanitize=fuzzer,address`).

## Pitfalls

- FetchContent: pin `URL` with `URL_HASH SHA256=...`, or `GIT_TAG` with a commit SHA. Add tests only `if(PROJECT_IS_TOP_LEVEL)` (CMake 3.21+), so a project that consumes the library neither downloads nor builds them.
- A struct that points into itself (a buffer and a cursor into it) is broken by plain assignment: copy it through a function that fixes the pointer, and test the copy.

Order before done: `clang-format` then `clang-tidy` then build then `ctest` on the `asan` and coverage presets.

No compiler or LLVM tools installed: there is no official clang image; `silkeh/clang:22` has clang, clang-format and clang-tidy 22 with CMake 3.31 (1.8 GB). One call, `--user` so the build is not owned by root: `export MSYS_NO_PATHCONV=1; src=$PWD; command -v cygpath >/dev/null && src=$(cygpath -m "$PWD"); docker run --rm --user "$(id -u):$(id -g)" -v "$src:/w" -w /w silkeh/clang:22 sh -c 'rc=0; f=$(find src include tests -name "*.[ch]"); clang-format -i $f || rc=1; { cmake --preset asan && cmake --build --preset asan && ctest --preset asan; } || rc=1; clang-tidy -p build/asan --quiet $f || rc=1; exit $rc'`. Its LLVM is 22, not 23: CI must use the same major, or clang-format output differs.
