# Bash, sh

Target `bash` unless the script must run on a minimal image; then write POSIX `sh` and lint it as `sh`.

## Lint and format: ShellCheck + shfmt

`.shellcheckrc` at the repo root:

```ini
shell=bash
enable=all              # include the optional checks too
external-sources=true   # follow `source` paths
```

ShellCheck exits non-zero on any finding, style included: that is the warnings-as-errors gate. Run `shellcheck **/*.sh` in CI.

shfmt reads `.editorconfig`:

```ini
[*.{sh,bash,bats}]
indent_style = space
indent_size = 2
switch_case_indent = true
binary_next_line = true
```

CI: `shfmt --diff .` (fails on any diff). Locally: `shfmt --write .`.

## Code

- Start every script with:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  shopt -s inherit_errexit
  ```
- Quote every expansion: `"$var"`, `"${array[@]}"`, `"$(cmd)"`. Unquoted only where splitting is the goal, with a comment.
- Bash has no static types: declare intent instead (see SKILL.md). `local -i count=0`, `local -r name="$1"`, `local -a files=()`, `local -A by_id=()`, `readonly MAX_RETRIES=3`.
- Every variable inside a function is `local`. Name parameters at the top: `local -r path="$1"`.
- `[[ ... ]]` over `[ ... ]` in bash; `$(...)` over backticks; `printf` over `echo` for data.
- Arrays for argument lists, never a string you split later.
- Clean up with `trap 'rm -rf "$tmp_dir"' EXIT` after `tmp_dir="$(mktemp -d)"`.
- Errors go to stderr with a non-zero exit: `die() { printf '%s\n' "$*" >&2; exit 1; }`.
- Wrap the body in `main() { ... }` and end with `main "$@"`, so tests can `source` the file without running it:
  ```bash
  if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
  ```
- Past about 200 lines or with real data structures, move to Python or Go.

## Tests

- bats-core with `bats-support` and `bats-assert` (git submodules or a pinned package).
  ```bash
  setup() { source "${BATS_TEST_DIRNAME}/../src/deploy.sh"; }

  @test "parse_version rejects an empty string" {
    run parse_version ""
    assert_failure
    assert_output --partial "empty version"
  }
  ```
- Unit-test functions by sourcing the script; integration-test the whole script with `run ./script.sh args` in a temp dir (`BATS_TEST_TMPDIR`).
- Stub external commands with a fake earlier on `PATH`, not by editing the script.
- Coverage: bashcov (line coverage, uses SimpleCov). Gate in `.simplecov`:
  ```ruby
  SimpleCov.minimum_coverage line: 90
  ```
  Run `bashcov -- bats test/`. Shell has no branch coverage tool; cover each branch with a test.
- No mutation testing tool exists for shell.

Order before done: `shfmt --write .` then `shellcheck` then `bats test/`.
