# Google Cloud

Written in Nov 2026 (not benchmarked): `google-github-actions/auth` supports Direct Workload Identity Federation (v2+). Check the current release with `gh release list -R google-github-actions/auth -L 1` before you pin.

## Lint and validate

- Scan Terraform with `trivy config .` or `checkov -d .`. Fail CI on HIGH/CRITICAL. Terraform rules: see `terraform.md`.
- Review IAM recommendations for unused permissions: `gcloud recommender recommendations list --recommender=google.iam.policy.Recommender --project=<id> --location=global`.
- Check why a principal has or lacks access: `gcloud policy-troubleshoot iam <resource> --principal-email=<sa> --permission=<perm>`.

## Practices

- Organize with folders; one project per workload and environment.
- Set organization policy constraints at the org or folder level:
  - `iam.disableServiceAccountKeyCreation`
  - `iam.automaticIamGrantsForDefaultServiceAccounts`
  - `storage.uniformBucketLevelAccess`
  - `storage.publicAccessPrevention`
  - `compute.requireOsLogin`
- Never use the default compute service account. One dedicated service account per workload.
- Label every resource (`owner`, `env`, `cost-center`).
- Use VPC Service Controls around projects that hold sensitive data.

## Security

- CI authenticates with Direct Workload Identity Federation. No service account keys.

```yaml
permissions:
  id-token: write
  contents: read
steps:
  - uses: google-github-actions/auth@<sha> # v2.x+; current: gh release list -R google-github-actions/auth -L 1
    with:
      workload_identity_provider: projects/123456789/locations/global/workloadIdentityPools/github/providers/acme
```

- Add an `attribute_condition` on the provider that limits it to your org and repo (`assertion.repository == 'acme/api'`).
- Grant roles to the `principalSet://` of that repo, at the narrowest resource, not the whole project.
- Least privilege: predefined or custom roles. Never basic roles (`roles/owner`, `roles/editor`, `roles/viewer`) for workloads or CI.
- GKE workloads use Workload Identity Federation for GKE. No key files mounted as secrets.
- Humans use groups and short-lived privileged access (Privileged Access Manager or approval flow), not standing admin roles.
- Secrets live in Secret Manager; grant `roles/secretmanager.secretAccessor` per secret, not per project.
- Turn on Data Access audit logs for sensitive services and route logs to a locked logging project. Use Security Command Center.
- A scanner finding is fixed, or you ask the user. Never add inline skips or org policy exceptions on your own.

## Tests

- Deploy to an ephemeral sandbox project in CI; delete it after the run.
- After deploy, smoke-test with the workload's own service account identity.
- Dry-run new org policies (`dryRunSpec`) and review violations before you enforce them.
