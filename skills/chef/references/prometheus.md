# Prometheus

Verified against Prometheus 3.16.0, Alertmanager 0.35.0 (Nov 2026). Look up the current release on github.com/prometheus/prometheus/releases; never guess one.

## Lint and validate

- `promtool check config prometheus.yml` and `promtool check rules rules/*.yml` in CI. Both fail the build on error.
- `amtool check-config alertmanager.yml` for Alertmanager.
- Unit-test every alerting and recording rule with `promtool test rules tests/*.yml`.

## Metric types and naming

- Counter: only goes up (requests, errors, bytes sent). Query with `rate()`/`increase()`, never the raw value.
- Gauge: goes up and down (queue depth, memory in use, temperature).
- Histogram: latency and sizes. Prefer it over Summary, because histograms aggregate across instances and summaries do not.
- Native histograms are stable since v3.8 but opt-in: set `scrape_native_histograms: true`. Since v3.9 the old feature flag does nothing. Remote write needs `send_native_histograms`.
- Name metrics `<namespace>_<what>_<unit>` in snake_case: `http_server_request_duration_seconds`, `orders_processed_total`.
- Use base units: seconds, bytes, ratios 0-1. Never milliseconds or megabytes. Put the unit in the name; counters end in `_total`.
- One metric holds one unit and one quantity. Never mix request size and duration in one metric.

## Labels and cardinality

- Every label value creates a new series. Never use user IDs, emails, request IDs, full URLs or other unbounded values as labels.
- Use the route template (`/users/{id}`), not the raw path. Use the status class or code, not the error message.
- Keep the number of series per metric bounded and known. Alert on `prometheus_tsdb_head_series` growth.
- Put trace IDs in exemplars, not labels (see `tracing.md`).

## What to measure

- RED for every request-serving service: Rate, Errors, Duration.
- USE for every resource (CPU, memory, disk, pool, queue): Utilization, Saturation, Errors.
- Expose `/metrics` from the client library; do not hand-write the exposition format.

## Rules

```yaml
groups:
  - name: checkout.rules
    rules:
      - record: job:http_requests:rate5m
        expr: sum by (job) (rate(http_server_request_duration_seconds_count[5m]))
      - alert: CheckoutHighErrorRate
        expr: |
          sum(rate(http_server_request_duration_seconds_count{job="checkout",http_response_status_code=~"5.."}[5m]))
            / sum(rate(http_server_request_duration_seconds_count{job="checkout"}[5m])) > 0.05
        for: 10m
        labels:
          severity: page
        annotations:
          summary: "Checkout 5xx ratio above 5% for 10m"
          runbook_url: "https://runbooks.example.com/checkout/high-error-rate"
```

- Name recording rules `level:metric:operations` (as above).
- Precompute expensive queries used by dashboards and alerts as recording rules.

## Alert design

- Alert on symptoms users feel: error rate, latency, availability. Do not page on causes like high CPU. Show causes on dashboards.
- Every page must need human action now. If nobody has to act, make it a ticket or a dashboard. Do not delete the signal.
- Use `for:` to avoid flapping. Never raise thresholds or silence alerts just to stop noise: fix the cause or the alert.
- Every alert has `summary`, a `severity` label and a `runbook_url`. `runbook_url` is a common convention, not a Prometheus requirement.
- Prefer SLO burn-rate alerts for services (see `slo.md`).

## Security

- Protect `/metrics` and the Prometheus UI: they leak internals. Use the web config file (`--web.config.file`) for TLS and basic auth, or keep them on an internal network.
- Never put secrets or personal data in label values. Labels are stored and shown everywhere.

## Tests

```yaml
rule_files: [../rules/checkout.yml]
evaluation_interval: 1m
tests:
  - interval: 1m
    input_series:
      - series: 'http_server_request_duration_seconds_count{job="checkout",http_response_status_code="500"}'
        values: '0+10x20'
      - series: 'http_server_request_duration_seconds_count{job="checkout",http_response_status_code="200"}'
        values: '0+10x20'
    alert_rule_test:
      - eval_time: 5m
        alertname: CheckoutHighErrorRate
        exp_alerts: []
      - eval_time: 15m
        alertname: CheckoutHighErrorRate
        exp_alerts:
          - exp_labels: { severity: page }
            exp_annotations:
              summary: "Checkout 5xx ratio above 5% for 10m"
              runbook_url: "https://runbooks.example.com/checkout/high-error-rate"
```

- Test that each alert fires on bad data and stays quiet on good data.
