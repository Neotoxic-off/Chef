# Grafana

Verified against Grafana 13.3.1, gcx 1.8.0 (Nov 2026). Look up the current release on github.com/grafana/grafana/releases; never guess one.

## Dashboards as code

- Every production dashboard lives in Git and is deployed by a pipeline. Pick one tool per Grafana instance:
  - File provisioning (`provisioning/dashboards/*.yaml` plus JSON files) for self-hosted instances.
  - Foundation SDK (Go, TypeScript, Python, Java, PHP) to generate dashboards in code. Grafana marks it "public preview". Push the output with `gcx`, Terraform or provisioning.
  - Terraform (`grafana` provider) or the Grafana Operator (Kubernetes CRs) when the rest of the stack already uses them.
  - Git Sync (GA since Grafana 13) syncs a Git repository with Grafana and allows edits as pull requests. Check the docs for availability on your edition.
- Grafonnet is not officially supported by Grafana. Do not start new work with it; use the Foundation SDK.
- Never hand-edit a provisioned dashboard in prod. Change the code, review it, deploy it. Lock the UI:

```yaml
apiVersion: 1
providers:
  - name: services
    type: file
    folderUid: services
    disableDeletion: true
    allowUiUpdates: false
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: true
```

- To change a dashboard, edit it in a dev instance, export the JSON (or port the change to SDK code), and commit it.

## Practices

- One dashboard per service with the same layout everywhere: RED row at the top, then saturation (USE), then dependencies.
- Give every dashboard and folder a fixed `uid` so links and alerts survive redeploys.
- Use variables for `datasource`, `environment`, `cluster` and `service`. Never hard-code a datasource UID or an environment in queries.
- Keep variable queries cheap and bounded (`label_values(up{job=~"$job"}, instance)`), never over a high-cardinality label.
- Use recording rules for heavy panel queries (see `prometheus.md`).
- Set units, thresholds and a description on every panel. A graph without units is not finished.
- Link panels to logs and traces through data links and exemplars (see `tracing.md`).

## Folders and permissions

- One folder per team or domain, provisioned as code with its permissions.
- Grant access to teams, not to individual users. Viewers by default, editors only on non-provisioned scratch folders.
- Admin rights stay with the platform team and the deploy pipeline's service account.

## Alerting

- Provision alert rules, contact points, notification policies and mute timings as code (files, Terraform or the alerting provisioning API). A resource stays managed by the source that created it: you cannot edit file-provisioned resources in the UI or in Terraform.
- Follow the alert design rules in `prometheus.md` and `slo.md`: symptom-based, actionable, with a runbook link and a severity label.
- If Prometheus or Mimir rules already exist, keep alert rules there and use Grafana only for routing. Do not define the same alert twice.
- Never mute or delete a noisy alert to make it quiet. Fix the threshold or the cause, with review.

## Security

- No secrets in dashboard JSON or provisioning files. In provisioning YAML, read them from the environment (`secureJsonData: { password: ${DB_PASSWORD} }`); in `grafana.ini`, use `$__file{/run/secrets/...}`. Escape a literal `$` as `$$`.
- Disable anonymous access and public dashboards unless explicitly needed, and review what any public dashboard shows.
- Datasources use least-privilege, read-only credentials.

## Tests

- Validate generated JSON in CI. At minimum, the build must produce it without errors and every dashboard must have a `uid` and a `title`.
- Deploy to a staging Grafana first and check that every panel returns data.
- Diff the rendered JSON in pull requests so reviewers can see what changed.
