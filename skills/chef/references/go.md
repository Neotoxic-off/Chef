# Go

Verified against Go 1.27.4, golangci-lint 2.15.0, gofumpt 0.12, testcontainers-go 0.45 (Nov 2026).

## Lint and format: golangci-lint v2

`.golangci.yml`:

```yaml
version: "2"
run:
  timeout: 5m  # v2 has no default timeout
linters:
  default: standard
  enable:
    - bodyclose
    - errorlint
    - gocyclo
    - gosec
    - revive
    - unparam
    - wrapcheck
  settings:
    revive:
      enable-default-rules: true  # needs golangci-lint v2.12+; check with `golangci-lint config verify`
      rules:
        - name: exported  # doc comments only on a library's public API
          disabled: true
        - name: package-comments  # same reason as `exported`
          disabled: true
formatters:
  enable:
    - gofumpt
    - goimports
```

Upgrade an old v1 config with `golangci-lint migrate`.

golangci-lint not installed: run the pinned official image (`MSYS_NO_PATHCONV=1` and `cygpath -m` stop Git Bash on Windows from rewriting the paths): `export MSYS_NO_PATHCONV=1; src=$PWD; command -v cygpath >/dev/null && src=$(cygpath -m "$PWD"); docker run --rm -v "$src:/app" -w /app golangci/golangci-lint:v2.15.0 golangci-lint run`. No Docker either: fall back to `go vet` plus gofmt, and tell the user golangci-lint did not run: `rc=0; go vet ./... || rc=1; files=$(gofmt -l .) || rc=1; [ -z "$files" ] || { printf '%s\n' "$files"; rc=1; }; [ "$rc" -eq 0 ]`.

## Code

- `:=` for locals, as Go expects; explicit types on exported identifiers, struct fields and function signatures.
- Always check errors. Wrap with context: `fmt.Errorf("load user %d: %w", id, err)`. Compare with `errors.Is` / `errors.As`.
- Accept interfaces, return structs. Define interfaces where they are used, keep them small.
- Pass `context.Context` as the first parameter of anything that does I/O.
- No package-level mutable state. No `init()` with side effects.

## Tests

- Table-driven tests with `t.Run`; `t.Parallel()` where safe. The loop over cases is the Go idiom and the allowed exception to "no loops in tests".
- Run with the race detector: `go test -race -coverprofile=cover.out -covermode=atomic ./...`. `-race` needs cgo and a C compiler: when `go env CGO_ENABLED` prints `0` or no C compiler is installed (`go: -race requires cgo`), run the same command without `-race` and tell the user the race detector did not run.
- Gate coverage in CI (e.g. `go tool cover -func=cover.out` and fail under 90%).
- Integration tests behind a build tag (`//go:build integration`) using `testcontainers-go`.
- Fuzz parsers with native `go test -fuzz`.
