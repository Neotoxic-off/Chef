# OpenTelemetry

Written for OpenTelemetry Collector 0.165.0 (contrib 0.165.1), semantic conventions 1.45.0 (Nov 2026), not benchmarked. Look up current versions on the language's OTel page or GitHub releases; never guess one.

## Setup

- Signal status per SDK (opentelemetry.io/docs/languages): traces are Stable everywhere except Rust (Beta). Metrics and logs vary: logs are Stable in Java, .NET, C++, PHP and Rust, a release candidate in Go, and still in development in Python and JavaScript. Check the table before you rely on a signal.
- Start with zero-code instrumentation where it exists (Java agent, .NET auto-instrumentation, Python `opentelemetry-instrument`, Node `@opentelemetry/auto-instrumentations-node`, Go eBPF). Add manual spans only for business operations the libraries cannot see.
- Configure through the standard env vars, not hard-coded values:

```sh
OTEL_SERVICE_NAME=checkout
OTEL_RESOURCE_ATTRIBUTES=service.version=1.4.2,deployment.environment.name=production
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1
```

- OTLP defaults: gRPC on `4317`, HTTP on `4318`. The spec's default protocol is `http/protobuf`.
- Declarative config (`OTEL_CONFIG_FILE`): the schema is stable, but SDK support is still experimental. Use env vars unless your SDK documents support.

## Practices

- Always set `service.name`, `service.version` and `deployment.environment.name` (the old `deployment.environment` was renamed).
- Follow the semantic conventions (opentelemetry.io/docs/specs/semconv) for attribute names. HTTP and database conventions are stable; GenAI conventions are still in development.
- Migrating old HTTP instrumentation: set `OTEL_SEMCONV_STABILITY_OPT_IN=http/dup` to emit both, update dashboards, then switch to `http`.
- Create one tracer or meter per library or module, named after it. Never one per request.
- Record errors on the span (`RecordException`/`record_exception` plus status `Error`) and still return or rethrow them. Never drop them.
- Send to a local Collector, not straight to a vendor: the app stays vendor-neutral and the Collector handles retries, batching and redaction.

## Collector

```yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: "${env:POD_IP}:4317" }
      http: { endpoint: "${env:POD_IP}:4318" }
processors:
  memory_limiter: { check_interval: 1s, limit_percentage: 80, spike_limit_percentage: 20 }
exporters:
  otlp_grpc:
    endpoint: tempo:4317
    sending_queue: { batch: {} }
service:
  pipelines:
    traces: { receivers: [otlp], processors: [memory_limiter], exporters: [otlp_grpc] }
```

- `memory_limiter` comes first in every pipeline.
- The exporter type is now `otlp_grpc` (`otlp` is a deprecated alias); HTTP is `otlp_http`. Batch in the exporter (`sending_queue.batch`). The `batch` processor is deprecated (removal planned for v0.177.0); do not add it. The Collector warns when both are present.
- Use the `contrib` or `k8s` distribution only if you need its components. Otherwise build your own with `ocb` and only the components you use.
- Validate config in CI: `otelcol validate --config=config.yaml` (use your distribution's binary name).

## Sampling

- Default is `parentbased_always_on`. Keep parent-based sampling so a trace is never cut in half.
- Head sampling (`traceidratio`) is cheap but cannot keep "all traces with an error".
- For that use tail sampling (contrib `tail_sampling` processor, beta). All spans of a trace must reach the same Collector, so put a `loadbalancing` exporter tier in front of it.

## Security

- Since Collector v0.110.0, servers bind to `localhost` by default. Bind to a specific interface (the pod IP) rather than `0.0.0.0`.
- Use TLS and authentication on any OTLP endpoint that leaves the host.
- Never put secrets or personal data in attributes, span names or baggage. Baggage is sent to every downstream service, third parties included.
- Strip or hash sensitive attributes in the Collector (`attributes`/`transform`/`redaction` processors) as a second line of defense.

## Tests

- Unit-test custom spans with the SDK's in-memory exporter: assert name, kind, key attributes and status.
- Smoke-test in CI with a Collector using the `debug` exporter, then check that spans arrive with the right `service.name`.
