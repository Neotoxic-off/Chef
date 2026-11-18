# HTTP API design (REST, OpenAPI)

Checked November 2026 against OpenAPI 3.2.0, RFC 9110, RFC 9457, RFC 9745 and the IETF drafts named below.

## Contract first

- One source of truth: a committed OpenAPI document (3.1 or 3.2), or one generated from typed code. Never maintain both by hand.
- Check that your generators and linters support 3.2 before you move to it. 3.2 adds the `QUERY` method, the `querystring` parameter and `itemSchema` for streams.
- Lint the document in CI and fail on warnings: `redocly lint openapi.yaml` or `spectral lint openapi.yaml`.
- Fail CI on breaking changes: `oasdiff breaking --fail-on ERR base/openapi.yaml openapi.yaml`.

## Resources and methods

- Plural nouns, kebab-case: `/orders/{orderId}/line-items`. Nest one level at most.
- Follow RFC 9110: `GET` is safe; `PUT` and `DELETE` are idempotent; `POST` is neither. `PATCH` with `application/merge-patch+json` (RFC 7396).
- Status codes: `201` with `Location` on create, `204` without a body, `400` malformed, `401` not authenticated, `403` not allowed, `404`, `409` state conflict, `422` failed validation, `429` with `Retry-After`.
- Optimistic concurrency: send `ETag`, require `If-Match` on writes, answer `412` on mismatch and `428` when it is missing.
- Validate every request against the schema at the boundary. Inputs set `additionalProperties: false`; clients ignore unknown response fields.
- Timestamps in RFC 3339 UTC. Money as integer minor units or a decimal string, with an ISO 4217 currency. IDs are opaque strings.

## Errors: RFC 9457

Every error is `application/problem+json` (RFC 9457 obsoletes RFC 7807):

```json
{
  "type": "https://api.example.com/problems/insufficient-stock",
  "title": "Insufficient stock",
  "status": 409,
  "detail": "Only 2 items of SKU-123 are left.",
  "instance": "/orders/8f14e45f"
}
```

- `type` is a stable, documented URI. Clients branch on `type`, never on `detail`.
- No stack traces, SQL or internal hostnames in the body. Log them server-side with a correlation ID.

## Pagination

- Cursor pagination for large or changing collections: `?limit=50&cursor=<opaque>`, next page in the body (`nextCursor`) or `Link: <...>; rel="next"` (RFC 8288).
- Offset pagination only for small, stable sets.
- Sort on a unique key (`createdAt, id`) so pages never skip or repeat rows.
- Put the maximum `limit` in a named constant; reject larger values with `400`.

## Idempotency keys

- Accept an `Idempotency-Key` header on `POST`/`PATCH` that create or charge. The header comes from IETF draft `draft-ietf-httpapi-idempotency-key-header` (-07, Oct 2025, not an RFC).
- Store key, request fingerprint and response in the same transaction as the effect, with a TTL. Same key and body: replay the stored response. Same key, other body: `422`. First request still running: `409`.

## Versioning and deprecation

- Only breaking changes get a new major version (`/v2`, or a media-type version; one scheme per API). New optional fields and new endpoints do not.
- Announce removals with `Deprecation` (RFC 9745) and `Sunset` (RFC 8594) headers plus a `Link` with `rel="deprecation"`.
- Rate limits: `429` with `Retry-After`. The `RateLimit`/`RateLimit-Policy` headers are still an IETF draft (-11, May 2026).

## Tests

- Fuzz the running app against its schema in CI: `schemathesis run openapi.yaml --url http://localhost:8080`.
- Consumer-driven contract tests (Pact) when other teams own the clients.
- Integration tests assert status, headers and problem `type` per error path: `create order with reused idempotency key and different body returns 422`.
