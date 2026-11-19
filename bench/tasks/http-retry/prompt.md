Every time the billing API deploys, our checkout service logs a burst of failed calls: the API answers 503 for a few seconds, or the connection drops. The client in this folder gives up on the first failure. Please add retry with exponential backoff to `HttpClient`.

- New client option `retry`, an object `{ maxAttempts, baseDelayMs, maxDelayMs }` (all optional). Defaults: 3 attempts in total, 250 ms, 10000 ms. `retry: false` turns retrying off. Settings that make no sense (fewer than 1 attempt, negative delays) are rejected when the client is created.
- Retry when the request gets no answer, or the API answers 408, 429, 500, 502, 503 or 504. Never on any other status.
- The first retry waits `baseDelayMs`, then the wait doubles each time (250, 500, 1000, ...), never more than `maxDelayMs`.
- When a 429 or 503 response has a `Retry-After` header (seconds, or an HTTP date), wait what it says instead, also capped at `maxDelayMs`. If the header is missing or unreadable, use the normal backoff.
- Like the rate limiter, the retry must wait through the client's `Scheduler`.
- Only retry requests that are safe to send twice: GET, HEAD, PUT, DELETE and OPTIONS, plus POST and PATCH when they carry an `Idempotency-Key` header. Creating an invoice with an idempotency key must be retried; voiding an invoice must never be sent twice, because the customer gets an email each time.
- When the attempts run out, throw the same error the client throws today for the last failure.

Work autonomously: nobody will answer questions.
