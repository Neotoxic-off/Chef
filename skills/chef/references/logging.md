# Logging in application code

Verified against pino 10.4.0, structlog 26.1.0, Microsoft.Extensions.Logging 11.0.0, tracing 0.1.44, tracing-subscriber 0.3.23 (Nov 2026). Rules follow the OWASP Logging Cheat Sheet. Look up current versions on each package registry; never guess one.

## Libraries

| Language | Use | Notes |
|---|---|---|
| C#/.NET | `Microsoft.Extensions.Logging` (`ILogger<T>`), optionally Serilog as provider | `[LoggerMessage]` source-generated methods on hot paths; `Microsoft.Extensions.Compliance.Redaction` for classified data |
| TypeScript/Node | `pino` | `redact: ['req.headers.authorization', '*.password']` |
| Python | `structlog` (or stdlib `logging` with a JSON formatter) | `structlog.contextvars.merge_contextvars` first in the processor chain |
| Go | `log/slog` (stdlib since Go 1.21) | `slog.NewJSONHandler(os.Stdout, nil)` |
| Rust | `tracing` + `tracing-subscriber` (feature `json`) | `#[instrument(skip(password))]` |

Use the language's standard or most common library. Do not write your own logger.

## Practices

- Log structured events, not formatted strings. Use a constant message plus fields: `logger.LogInformation("Order {OrderId} placed", orderId)`, not string interpolation. Interpolation breaks grouping and costs time even when the level is off.
- Write JSON to stdout in production; let the platform ship it (see `loki.md`). Use human-readable output only in local dev.
- Levels:
  - `ERROR`: an operation failed and someone may need to act.
  - `WARN`: something unexpected that the app recovered from.
  - `INFO`: business events and lifecycle (start, stop, config loaded).
  - `DEBUG`: diagnostic detail, off in prod by default.
  - Never log an expected client error (validation, 404) as `ERROR`.
- Log an error once, where it is handled, with the exception object and its stack trace. Do not log it and rethrow it at every layer.
- Never catch an exception just to log and swallow it. Log, then handle, rethrow or return the error.
- Fixed field names across services: `timestamp` (UTC, ISO 8601), `level`, `message`, `service`, `trace_id`, `span_id`, `request_id`. Follow OTel names when using OTel logs.
- Make the level configurable at runtime (env var or config) without a redeploy.

## Correlation

- Every log line in a request carries `trace_id` and `span_id`. Use the OTel log bridge or the library's context integration (`Activity` in .NET, `contextvars` in structlog, `context.Context` with an slog handler, `tracing` spans in Rust).
- Bind request-scoped fields once at the edge (middleware): request ID, route, tenant. Never pass them by hand through every call.
- Accept an incoming `X-Request-ID` only after validating its format and length; otherwise generate one.

## Never log

- Passwords, API keys, tokens, session IDs, cookies, `Authorization` headers, connection strings, encryption keys.
- Personal data: names, emails, phone numbers, addresses, government IDs, health or payment data. Log an internal user ID, or a hash if you must correlate.
- Full request or response bodies, and raw SQL with bound values.
- Redact by allow-list where you can: log the fields you chose, not whole objects. Add library redaction (pino `redact`, .NET redaction, a structlog processor) as a second line.
- Sanitize user input before logging: strip CR/LF and control characters to prevent log injection. Structured JSON output escapes them for you.
- Do log security events: authentication success and failure, authorization failures, input validation failures, admin actions. Leave the secrets out.

## Tests

- Assert important log events in unit tests with the library's test sink: `FakeLogger` (.NET), `structlog.testing.capture_logs`, a slog handler writing to a buffer, pino with a destination stream, `tracing-test`.
- Add a test that logs an object holding a secret and asserts the secret is not in the output.
