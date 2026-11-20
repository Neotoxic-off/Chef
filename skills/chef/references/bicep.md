# Bicep

Written for the Bicep CLI current in Nov 2026 (no version pinned here), not benchmarked. Check yours with `az bicep version` (latest: `gh release list -R Azure/bicep -L 1`). Upgrade with `az bicep upgrade`. Azure-wide rules: see `azure.md`.

## Lint and validate

- Build and lint in CI: `bicep build main.bicep` and `bicep lint main.bicep`. Fail on warnings.
- Raise linter rules to `error` in `bicepconfig.json`; never set a rule to `off` to pass CI.

```json
{
  "analyzers": {
    "core": {
      "enabled": true,
      "rules": {
        "no-hardcoded-env-urls": { "level": "error" },
        "outputs-should-not-contain-secrets": { "level": "error" },
        "secure-secrets-in-params": { "level": "error" },
        "use-recent-api-versions": { "level": "warning" }
      }
    }
  }
}
```

- Scan with PSRule for Azure (`microsoft/ps-rule` action, module `PSRule.Rules.Azure`); it expands `.bicep` files itself. Upload SARIF to code scanning.
- Preview on PRs: `az deployment group what-if --template-file main.bicep --parameters main.prod.bicepparam`.

## Practices

- Use `.bicepparam` files per environment, not JSON parameter files.
- Every parameter has a type and `@description`; add `@allowed`, `@minLength`, `@maxValue` at trust boundaries.
- Use user-defined types for object parameters; no untyped `object` or `array`.

```bicep
@description('Storage account settings.')
type storageConfig = {
  name: string
  sku: 'Standard_LRS' | 'Standard_ZRS'
}

param config storageConfig
param location string = resourceGroup().location
```

- Prefer Azure Verified Modules (`br/public:avm/...`) and pin the module version tag.
- Small modules with one job; reference existing resources with `existing`, not hard-coded IDs.
- Use the `parent` property or nested syntax instead of building names with `/`.
- Pin recent, non-preview API versions; update them on purpose.
- Use deployment stacks (`az stack group create`) to manage lifecycle and clean up removed resources, with `--deny-settings-mode` in prod.

## Security

- Mark secret params `@secure()`. Never output secrets. Read secrets from Key Vault with `getSecret()` in `.bicepparam` or `keyVault.getSecret()` in module calls.
- Assign RBAC to managed identities in the template, at the narrowest scope and with the narrowest built-in role.
- Set secure defaults in the template: `publicNetworkAccess: 'Disabled'`, `minimumTlsVersion`, `allowSharedKeyAccess: false`, `disableLocalAuth: true` where supported.
- CI deploys with OIDC (`azure/login`); the deploy identity has only the roles the deployment needs.
- A PSRule or linter finding is fixed, or you ask the user. Never add `#disable-next-line` or rule exclusions on your own.

## Tests

- Run `what-if` in CI and fail the job on unexpected `Delete` changes.
- Deploy to an ephemeral resource group in a sandbox subscription; smoke-test; delete the group.
- PSRule rules act as unit tests for security properties; add custom rules for house conventions.
