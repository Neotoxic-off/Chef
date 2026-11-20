# Distributed tracing (Tempo, Jaeger)

Written for Tempo 3.1.1, Jaeger 2.23.0 (Nov 2026), not benchmarked. Instrument with OpenTelemetry (see `opentelemetry.md`). Look up backend versions on their GitHub releases pages; never guess one.

## Backends

- Grafana Tempo: object-storage backed, queried with TraceQL, integrated with Grafana, Loki and Prometheus. Tempo 3 removed the ingester write path and has no downgrade to 2.x: follow the 3.0 migration guide.
- Jaeger: v1 reached end of life on December 31, 2025 and gets no more updates. Use Jaeger v2: one binary built on the OpenTelemetry Collector, configured with Collector-style YAML, taking OTLP on `4317`/`4318`. The Jaeger client libraries and agent are gone: use OTel SDKs.
- Send OTLP from apps to an OTel Collector, and from the Collector to the backend. Switching backends then means changing only the Collector.

## Context propagation

- Use W3C Trace Context (`traceparent`, `tracestate`; W3C Recommendation). OTel's default propagators are `tracecontext,baggage`. Keep them unless a peer only speaks B3 or Jaeger; then add that propagator, do not replace W3C.
- `traceparent` is `00-<32 hex trace-id>-<16 hex parent-id>-<2 hex flags>`. Never build or parse it by hand: use the propagator API.
- Propagate across every hop: HTTP and gRPC (auto-instrumented), and message queues (inject into message headers on publish, extract on consume, use span links for batches).
- Background jobs and async tasks: carry the context explicitly into the task, or start a new trace and link it to the old one.
- At the edge, decide whether to trust an incoming `traceparent` from the internet. For public endpoints, start a new trace and link the incoming one.
- Baggage goes to every downstream service. Never put secrets, tokens or personal data in it.

## Span names and attributes

- Span names are low cardinality: `GET /users/{id}`, `SELECT orders`, `checkout.place_order`. Never `GET /users/314159`.
- HTTP spans are `{method} {http.route}` on servers. Instrumentation must not fall back to the raw URL path.
- Set the right span kind: `SERVER`, `CLIENT`, `PRODUCER`, `CONSUMER`, `INTERNAL`.
- Use semantic convention attributes (`http.request.method`, `http.response.status_code`, `db.system.name`, `messaging.system`) before inventing your own. Prefix custom ones with your domain (`shop.order.items`).
- Put IDs (order ID, tenant ID) in attributes, not names. Never put passwords, tokens, raw request bodies or personal data in them.
- On failure, set status `Error`, record the exception, then handle or rethrow it as usual.

## Linking signals

- Logs: write `trace_id` and `span_id` into every log line (see `logging.md`). OTel log bridges do this automatically. In Loki, store them as structured metadata, not labels.
- In Grafana, configure the Tempo datasource's "Trace to logs" and "Trace to metrics", and a Loki derived field that turns `trace_id` into a Tempo link.
- Metrics: attach exemplars (a trace ID on a histogram sample) so a latency spike links to a real trace. The OTel spec makes `TraceBased` the default exemplar filter: SDKs attach exemplars only for sampled spans.
- Prometheus stores exemplars only with `--enable-feature=exemplar-storage` (still a feature flag in 3.x). Turn on exemplars in the Grafana Prometheus datasource and point them to Tempo.
- The Tempo metrics-generator can derive RED span metrics and service graphs from traces. Use it if apps do not export their own RED metrics; never put trace IDs in metric labels.

## Security

- Spans often hold SQL, URLs and headers. Turn off or sanitize statement and header capture in instrumentation options. Redact in the Collector as a second line.
- Restrict who can query traces. They show internal topology and request data.

## Tests

- Unit-test custom spans with an in-memory exporter: name, kind, attributes, status, parent-child links.
- Integration test: call service A, which calls B, and assert both spans share one trace ID.
