# Azure

Written in Nov 2026 (not benchmarked): `azure/login` v3 is the recommended major. Check the current release with `gh release list -R Azure/login -L 1` before you pin. IaC rules: see `bicep.md` or `terraform.md`.

## Lint and validate

- Lint Bicep with the built-in linter (`bicep lint main.bicep`) and PSRule for Azure. Fail CI on warnings.
- Scan Terraform or ARM with `trivy config .` or `checkov -d .`. Fail CI on HIGH/CRITICAL.
- Preview every change: `az deployment group what-if` on PRs. Post the result for review.
- Check policy compliance after deploy: `az policy state summarize --resource-group <rg>`.

## Practices

- Organize with management groups; one subscription per workload and environment.
- Assign Azure Policy at management-group scope: allowed regions, required tags, deny public network access, require encryption.
- Prefer Azure Verified Modules over hand-written modules for common resources.
- Use private endpoints for PaaS data services in production; disable public network access.
- Tag every resource (`owner`, `env`, `costCenter`); enforce with a policy.
- Lock production resource groups or use deployment stacks with deny settings.

## Security

- CI logs in with OIDC: a federated identity credential on a user-assigned managed identity or app registration. No client secrets.

```yaml
permissions:
  id-token: write
  contents: read
steps:
  - uses: azure/login@<sha> # v3.x; current: gh release list -R Azure/login -L 1
    with:
      client-id: ${{ vars.AZURE_CLIENT_ID }}
      tenant-id: ${{ vars.AZURE_TENANT_ID }}
      subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
```

- Scope the federated credential subject to one repo and environment (`repo:acme/api:environment:prod`).
- Least privilege RBAC at the narrowest scope (resource group or resource). Avoid `Owner` and `Contributor` for CI; use built-in data-plane roles or a custom role.
- Humans get roles through Entra ID PIM (just-in-time). No standing `Owner`.
- Workloads use managed identities. Disable key-based auth where the service allows it: `allowSharedKeyAccess: false` on storage, `disableLocalAuth: true` on Service Bus, Event Hubs, Cosmos DB, App Configuration.
- Key Vault: RBAC authorization mode, soft delete and purge protection on, private endpoint in prod.
- Turn on Microsoft Defender for Cloud plans for the services you run; send activity logs to a central Log Analytics workspace.
- A scanner or policy finding is fixed, or you ask the user. Never add inline suppressions or policy exemptions on your own.

## Tests

- Deploy to an ephemeral resource group in a sandbox subscription in CI; delete it after the run.
- After deploy, smoke-test the real endpoint with the managed identity, not a key.
- Test policy assignments in `DoNotEnforce` mode first; check compliance results before you enforce.
