# Secrets: Vault, cloud secret managers, SOPS, External Secrets

Verified Nov 2026: External Secrets Operator serves only `external-secrets.io/v1` (v1beta1 removed after v0.16.x); OpenBao 2.x (MPL-2.0 fork of Vault; Vault itself is BSL); SOPS 3.x recommends age over PGP. Check current versions with `gh release list -R <owner>/<repo> -L 1` (`external-secrets/external-secrets`, `openbao/openbao`, `getsops/sops`).

## Lint and validate

- Scan every commit for secrets: `gitleaks git` (or `trufflehog git file://.`) in pre-commit and CI. Turn on GitHub push protection.
- A detected secret is a leak: rotate it first, then remove it from history. Never add it to an allowlist to pass CI; ask the user.
- Check that SOPS files are encrypted before commit: every file matched by `.sops.yaml` must contain a `sops:` metadata block.

## Practices

- Pick one source of truth per environment: the cloud secret manager (AWS Secrets Manager, Azure Key Vault, Google Secret Manager) or Vault/OpenBao.
- Prefer short-lived, dynamic credentials (Vault database and cloud secrets engines, IAM auth to databases) over static passwords.
- Turn on rotation for every static secret; the app re-reads the secret instead of caching it forever.
- Keep secrets out of env files in the repo, Docker images, CI logs and IaC state outputs.
- Kubernetes: sync from the secret manager with External Secrets Operator; the app reads a normal `Secret`.

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata: { name: api-db, namespace: api }
spec:
  refreshInterval: 1h
  secretStoreRef: { kind: ClusterSecretStore, name: aws-secrets }
  target: { name: api-db }
  data:
    - secretKey: password
      remoteRef: { key: prod/api/db, property: password }
```

- Git-stored secrets (GitOps, config): SOPS with age or a cloud KMS key; encrypt only values.

```yaml
creation_rules:
  - path_regex: ^deploy/prod/.*\.ya?ml$
    encrypted_regex: ^(data|stringData)$
    kms: arn:aws:kms:eu-west-1:111122223333:key/<key-id>
```

## Security

- Auth to the secret store with workload identity, never a stored token: IRSA or EKS Pod Identity, Azure Workload Identity, GKE Workload Identity, Vault Kubernetes or JWT/OIDC auth.
- CI gets secrets through OIDC (Vault JWT auth bound to repo and environment, or the cloud OIDC login). No long-lived tokens in CI settings.
- Least privilege: one policy per app, read access to its own paths only (`prod/api/*`). No wildcard read on the whole store.
- ESO: prefer namespaced `SecretStore` per team; restrict `ClusterSecretStore` with `conditions` on namespaces.
- Vault/OpenBao: short token TTLs, no root token in daily use (revoke it after setup), audit device on, auto-unseal with a cloud KMS.
- Private age keys and KMS decrypt rights only for the people and controllers that need them.
- Enable Kubernetes Secret encryption at rest (KMS provider) and restrict `get`/`list` on `secrets` in RBAC.

## Tests

- Test the app's secret loading with a fake provider or a local Vault/OpenBao dev server, not real secrets.
- In CI, assert ESO `ExternalSecret` status is `Ready` after sync in an ephemeral cluster.
- Run a rotation drill: rotate a secret in staging and check the app picks it up without a redeploy.
