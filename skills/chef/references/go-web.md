# Go web: net/http, chi, Gin, Echo

Builds on `go.md`. Verified against Go 1.27.4, chi 5.5.0, Gin 1.12.0, Echo 5.4.6 (Nov 2026). Current versions: `curl -s 'https://go.dev/VERSION?m=text'` for Go, `go list -m -u all` for modules.

## Router choice

- New service: standard `http.ServeMux` with method and wildcard patterns (Go 1.22+): `"GET /orders/{id}"`, read with `r.PathValue("id")`.
- Add chi only for route groups and middleware stacks; its handlers stay plain `http.Handler`.
- Gin or Echo only where the project already uses them.

## Server

- Never bare `http.ListenAndServe`: build an `http.Server` with every timeout set (gosec flags a missing `ReadHeaderTimeout`).
- Graceful shutdown: `signal.NotifyContext` then `srv.Shutdown(ctx)` with a deadline.
- Middleware is `func(http.Handler) http.Handler`. Cookie-authenticated apps add `http.CrossOriginProtection` (Go 1.25+) against CSRF.

```go
const (
	readHeaderTimeout time.Duration = 5 * time.Second
	writeTimeout      time.Duration = 10 * time.Second
	idleTimeout       time.Duration = 60 * time.Second
	maxBodyBytes      int64         = 1 << 20
)

func newServer(addr string, orders *OrderHandler) *http.Server {
	var mux *http.ServeMux = http.NewServeMux()
	mux.HandleFunc("GET /orders/{id}", orders.Get)
	mux.HandleFunc("POST /orders", orders.Create)
	return &http.Server{Addr: addr, Handler: mux, ReadHeaderTimeout: readHeaderTimeout,
		WriteTimeout: writeTimeout, IdleTimeout: idleTimeout}
}
```

## Input and errors

- Limit and decode strictly, then validate into a domain type before any I/O:
  ```go
  r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
  var decoder *json.Decoder = json.NewDecoder(r.Body)
  decoder.DisallowUnknownFields()
  var request createOrderRequest
  var err error = decoder.Decode(&request)
  ```
- Map domain errors to status codes in one place (`errors.Is` / `errors.As`); never send `err.Error()` of an internal error to the client.
- Go 1.27 ships `encoding/json/v2`, and `encoding/json` now runs on the v2 implementation. Keep the `encoding/json` API unless the project has chosen v2.
- HTTP clients: always `defer resp.Body.Close()` (the `bodyclose` linter checks it); set `http.Client.Timeout`.

## Gin

- `gin.New()` with explicit middleware; set `GIN_MODE=release` in production.
- `c.ShouldBindJSON(&request)` with `binding:"required"` tags, and write the error yourself; `BindJSON` writes a plain-text 400 on its own.
- Call `SetTrustedProxies` with your proxy list; `ClientIP()` trusts forwarding headers otherwise.

## Echo v5

- Handlers are `func(c *echo.Context) error` (v5 changed `echo.Context` from interface to struct pointer). Return errors; one `HTTPErrorHandler` renders them.
- Since v5.1, `RealIP()` uses the direct peer address by default. Behind a proxy, set `IPExtractor` (e.g. `echo.ExtractIPFromXFFHeader` with explicit trust options).
- Echo v4 gets bug fixes until 2026-12-31 and security fixes until 2027-12-31: migrate (import path `echo/v5`, `*echo.Context`).

## Tests

- Handlers: `httptest.NewRecorder()` and `handler.ServeHTTP(recorder, request)`; table-driven cases per status.
- Outbound clients: `httptest.NewServer` as the fake remote.
- Integration: start the real server on `httptest.NewServer(mux)` with a Testcontainers database.
