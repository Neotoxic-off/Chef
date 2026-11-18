# Go

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
formatters:
  enable:
    - gofumpt
    - goimports
```

Upgrade an old v1 config with `golangci-lint migrate`.

## Code

- Explicit types: `var n int = 0`, not `n := 0` (see SKILL.md).
- Always check errors. Wrap with context: `fmt.Errorf("load user %d: %w", id, err)`. Compare with `errors.Is` / `errors.As`.
- Accept interfaces, return structs. Define interfaces where they are used, keep them small.
- Pass `context.Context` as the first parameter of anything that does I/O.
- No package-level mutable state. No `init()` with side effects.

## Tests

- Table-driven tests with `t.Run`; `t.Parallel()` where safe.
- Always run with the race detector: `go test -race -coverprofile=cover.out -covermode=atomic ./...`.
- Gate coverage in CI (e.g. `go tool cover -func=cover.out` and fail under 90%).
- Integration tests behind a build tag (`//go:build integration`) using `testcontainers-go`.
- Fuzz parsers with native `go test -fuzz`.
