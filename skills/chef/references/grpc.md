# gRPC and Protocol Buffers

Verified against Buf CLI 1.75 (`buf.yaml` v2), @bufbuild/protovalidate 1.3 (Nov 2026).

## Buf: lint, format, breaking

`buf.yaml`:

```yaml
version: v2
modules:
  - path: proto
lint:
  use:
    - STANDARD
breaking:
  use:
    - FILE
```

- CI fails on any finding from `buf format --diff --exit-code`, `buf lint` and `buf breaking --against '.git#branch=main'`.
- `STANDARD` and `FILE` are the strictest built-in categories. Use `WIRE_JSON` only for a published API where you accept source-level breaks in generated code.
- Fix lint findings. No `// buf:lint:ignore` comments, no `except` or `ignore` entries to hide them.
- Generate code with `buf generate` from a committed `buf.gen.yaml`; pin plugin versions.

## Schema design

```proto
syntax = "proto3";

package acme.orders.v1;

import "buf/validate/validate.proto";

service OrderService {
  rpc GetOrder(GetOrderRequest) returns (GetOrderResponse);
}

enum OrderStatus {
  ORDER_STATUS_UNSPECIFIED = 0;
  ORDER_STATUS_PLACED = 1;
}

message GetOrderRequest {
  string order_id = 1 [(buf.validate.field).string.uuid = true];
}
```

- Versioned packages (`acme.orders.v1`). A breaking change means a new `v2` package.
- One request and one response message per RPC, named after it.
- Enums start with `<ENUM>_UNSPECIFIED = 0`.
- Never reuse or renumber a field. Mark removed numbers and names `reserved`.
- Well-known types: `Timestamp`, `Duration`, `FieldMask` for partial updates. Follow Google AIPs (aip.dev) for resource-oriented APIs.

## Runtime

- Validate every request with protovalidate rules in a server interceptor, at the boundary.
- Clients always set a deadline. Servers pass the incoming context to downstream calls and stop work on cancellation.
- Map domain errors to canonical codes: `INVALID_ARGUMENT`, `NOT_FOUND`, `ALREADY_EXISTS`, `FAILED_PRECONDITION`, `PERMISSION_DENIED`, `UNAUTHENTICATED`. Put details in `google.rpc.Status` (`BadRequest`, `ErrorInfo`).
- Retry only idempotent methods, on `UNAVAILABLE`, through the service config retry policy.
- Serve `grpc.health.v1.Health`. Turn server reflection off in production or put it behind auth.
- TLS on every connection; mTLS between services.
- Browsers: Connect protocol or gRPC-Web through a proxy.

## Tests

- In-process server (Go `bufconn`, .NET `WebApplicationFactory`, Java in-process transport) with real interceptors. Assert codes and details: `GetOrder with unknown id returns NOT_FOUND`.
- `buf breaking` in CI is the contract test for the wire format.
