# Loki

Written for Loki 3.7.10, Alloy 1.22.0 (Nov 2026), not benchmarked. Look up current releases on github.com/grafana/loki/releases and github.com/grafana/alloy/releases; never guess one.

## Shipping logs

- Promtail reached end of life on March 2, 2026 and gets no more updates. Do not add it. Use Grafana Alloy, or an OpenTelemetry Collector sending OTLP to Loki's `/otlp` endpoint. `lambda-promtail` is not part of this deprecation.
- Migrate an existing Promtail config: `alloy convert --source-format=promtail --output=config.alloy promtail.yaml`. Alloy's own metrics differ from Promtail's, so update the dashboards and alerts that watch the agent.
- Apps write JSON lines to stdout. The agent collects them; the app never pushes to Loki itself.

## Labels vs log fields

- Labels index streams. Keep them few, static and bounded: `cluster`, `namespace`, `service_name`, `env`. Loki rejects more than 15 label names per series by default (`max_label_names_per_series`).
- Never use as labels: user IDs, request or trace IDs, IPs, paths, status codes or anything unbounded. Each unique label set is a new stream and more chunks.
- Loki's own docs advise against a `level` label for low and medium volume apps: `{app="x"} |= "level=error"` is often just as fast and stores fewer chunks.
- Put high-cardinality metadata you query often (`trace_id`, `user_tier`, pod name) in structured metadata, not labels. It is on by default in Loki 3 (`allow_structured_metadata`), with a 64KB default limit per line.
- With OTLP ingestion, resource attributes become index labels (configurable list); the rest becomes structured metadata.
- Everything else stays in the JSON body and is parsed at query time.

## LogQL basics

```logql
{service_name="checkout", env="prod"} |= "timeout" | json | duration_ms > 500
{service_name="checkout"} | json | level="error" | line_format "{{.msg}} trace={{.trace_id}}"
sum by (service_name) (rate({env="prod"} | json | level="error" [5m]))
quantile_over_time(0.95, {service_name="checkout"} | json | unwrap duration_ms [5m]) by (route)
```

- Always start with the narrowest stream selector, then line filters (`|=`, `!=`, `|~`), then parsers (`json`, `logfmt`), then label filters. Filters before parsers are cheaper.
- Use metric queries (`rate`, `count_over_time`) for alerts in the Loki ruler, with the same alert rules as `prometheus.md`.

## Retention

- Retention is enforced by the compactor and is off by default: without it, logs live forever.

```yaml
compactor:
  retention_enabled: true
  delete_request_store: s3
limits_config:
  retention_period: 744h
  retention_stream:
    - selector: '{env="dev"}'
      priority: 1
      period: 168h
```

- Each `retention_stream` period must be at least 24h. An object-store lifecycle rule must be longer than the Loki retention.
- Set retention from legal and business needs (audit, privacy law), not from disk size alone.

## Security

- Never log secrets, tokens, passwords or personal data (see `logging.md`). Once ingested, data can only be removed with log deletion requests through the compactor. Never count on that as a cleanup step.
- Redact in the app first. Add an agent-side redaction stage (Alloy `loki.process` or an OTel `redaction`/`transform` processor) as a second line of defense.
- Enable multi-tenancy (`auth_enabled: true`) with an authenticating proxy in front; never expose Loki's push or query API publicly.

## Tests

- Check agent config in CI: `alloy fmt` (fails on syntax errors) or `otelcol validate --config=...`.
- Check label cardinality after a change: `logcli series '{env="prod"}' --analyze-labels`.
- Test Loki alert rules on a staging instance with known log lines before enabling paging.
