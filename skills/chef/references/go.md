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

## Code

- `:=` for locals, as Go expects; explicit types on exported identifiers, struct fields and function signatures.
- Always check errors. Wrap with context: `fmt.Errorf("load user %d: %w", id, err)`. Compare with `errors.Is` / `errors.As`.
- Accept interfaces, return structs. Define interfaces where they are used, keep them small.
- Pass `context.Context` as the first parameter of anything that does I/O.
- No package-level mutable state. No `init()` with side effects.

## Tests

- Table-driven tests with `t.Run`; `t.Parallel()` where safe. The loop over cases is the Go idiom and the allowed exception to "no loops in tests".
- Always run with the race detector: `go test -race -coverprofile=cover.out -covermode=atomic ./...`.
- Gate coverage in CI (e.g. `go tool cover -func=cover.out` and fail under 90%).
- Integration tests behind a build tag (`//go:build integration`) using `testcontainers-go`.
- Fuzz parsers with native `go test -fuzz`.
