# SLOs and error budgets

Checked Nov 2026 on sre.google (SRE Workbook, "Alerting on SLOs") and the Sloth and Pyrra repositories. Look up tool versions on their GitHub releases pages; never guess one.

## Definitions

- SLI: a ratio of good events to valid events, measured where users feel it (load balancer, API gateway, or server-side request metrics). Example: non-5xx responses / all responses, or requests under 300 ms / all requests.
- SLO: the target for an SLI over a rolling window, usually 28 or 30 days. Example: 99.9% of requests succeed over 30 days.
- Error budget: `1 - SLO`. At 99.9% over 30 days, that is 0.1% of requests, or about 43 minutes of full outage.
- Burn rate: how fast you spend the budget. A burn rate of 1 uses it up exactly at the end of the window; 14.4 uses 2% of a 30-day budget in 1 hour.

## Practices

- Start with 1-3 SLOs per user-facing service: availability and latency. Add correctness or freshness for pipelines.
- Pick the target from what users need and what the service did historically. Never pick 100%.
- Count events, not uptime minutes, where you can: request-based SLIs handle low and high traffic better.
- Exclude only what is not the service's fault (for example, 4xx caused by clients), and write the exclusion down.
- Write an error budget policy agreed by the team and product owner: what happens when the budget is spent (freeze risky releases, prioritize reliability work).
- Keep SLO definitions in Git, next to the service, reviewed like code.

## Burn-rate alerts

Use multiwindow, multi-burn-rate alerts (SRE Workbook, 30-day SLO):

| Budget spent | Long window | Short window | Burn rate | Action |
|---|---|---|---|---|
| 2% | 1h | 5m | 14.4 | Page |
| 5% | 6h | 30m | 6 | Page |
| 10% | 3d | 6h | 1 | Ticket |

- The short window is 1/12 of the long one. It makes the alert stop soon after the burn stops.
- Both windows must exceed `burn_rate * (1 - SLO)` for the alert to fire.
- Replace cause-based pages (CPU, pod restarts) with SLO burn alerts. Keep the cause signals on dashboards. Never delete a signal just to cut noise.
- Each alert links to a runbook and to the SLO dashboard (remaining budget, burn rate over time).

## Tools

- Do not hand-write the dozens of recording rules and alerts an SLO needs. Generate them:
  - Sloth (github.com/slok/sloth): a spec file generates Prometheus recording rules and multiwindow multi-burn-rate alerts. CLI `sloth generate`, a Kubernetes controller, and a Go library since v0.16.0 (Apr 2026). Actively maintained per its README.
  - Pyrra (github.com/pyrra-dev/pyrra): a `ServiceLevelObjective` resource (Kubernetes, Docker or filesystem) generates rules and 4 multi-burn-rate alerts, plus a web UI. Its README says it is mostly maintained in the authors' free time.
- Pick one tool per organization. Commit the generated rules or generate them in CI; never edit generated output by hand.

```yaml
version: "prometheus/v1"
service: "checkout"
labels:
  owner: "payments-team"
slos:
  - name: "requests-availability"
    objective: 99.9
    sli:
      events:
        error_query: sum(rate(http_server_request_duration_seconds_count{job="checkout",http_response_status_code=~"5.."}[{{.window}}]))
        total_query: sum(rate(http_server_request_duration_seconds_count{job="checkout"}[{{.window}}]))
    alerting:
      name: "CheckoutHighErrorBudgetBurn"
      annotations:
        runbook_url: "https://runbooks.example.com/checkout/error-budget"
      page_alert:
        labels: { severity: page }
      ticket_alert:
        labels: { severity: ticket }
```

## Tests

- Run the generator in CI, then `promtool check rules` on its output.
- Unit-test the generated burn-rate alerts with `promtool test rules`: feed an error ratio above 14.4x the budget and assert the page fires; feed a ratio below 1x and assert nothing fires.
- Review SLOs every quarter against real incidents. An outage with no burn alert, or a page with no user impact, means the SLI is wrong.
