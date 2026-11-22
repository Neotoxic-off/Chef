# Kubernetes and Helm

Verified against Kubernetes 1.37, Helm 4.3, kubeconform 0.8, kube-linter 0.8 (Nov 2026).

## Lint and validate

- Validate manifests against the schemas of your target Kubernetes version: `kubeconform -strict -summary -kubernetes-version 1.37.0 manifests/`. Add CRD schemas with `-schema-location`.
- Lint for best practice with kube-linter (`kube-linter lint .`) or Polaris (`polaris audit --audit-path . --set-exit-code-on-danger`). Pick one; run it in CI.
- Helm: `helm lint --strict charts/<chart>`, then render and validate: `helm template charts/<chart> | kubeconform -strict -`.
- Chart repos: `ct lint` (chart-testing) also checks that the chart version was bumped.
- Tools not installed: one call from their images (kubeconform downloads schemas, so it needs network): `export MSYS_NO_PATHCONV=1; src=$PWD; command -v cygpath >/dev/null && src=$(cygpath -m "$PWD"); set -o pipefail; rc=0; docker run --rm -v "$src:/w" -w /w alpine/helm:4.3 lint --strict charts/<chart> || rc=1; docker run --rm -v "$src:/w" -w /w alpine/helm:4.3 template charts/<chart> | docker run --rm -i ghcr.io/yannh/kubeconform:v0.8.0 -strict -summary -kubernetes-version 1.37.0 - || rc=1; docker run --rm -v "$src:/w" -w /w stackrox/kube-linter:v0.8.3 lint . || rc=1; [ "$rc" -eq 0 ]`.
- Server-side check before apply: `kubectl apply --dry-run=server -f ...` and `kubectl diff`.

`.kube-linter.yaml`:

```yaml
checks:
  addAllBuiltIn: true
```

## Practices

- Never `:latest` or no tag. Pin images by tag and digest (`app:1.4.2@sha256:...`); `imagePullPolicy: IfNotPresent`.
- Every container sets `resources.requests` (CPU, memory) and `resources.limits.memory`. Add a CPU limit only if you have a reason.
- Every long-running container has `readinessProbe` and `livenessProbe`; add `startupProbe` for slow starters. Liveness must not depend on downstream services.
- Set labels `app.kubernetes.io/name`, `instance`, `version`, `part-of`, `managed-by`.
- `replicas >= 2`, a `PodDisruptionBudget` and `topologySpreadConstraints` for anything that must stay up.
- One concern per manifest file. Config in `ConfigMap`, secrets in `Secret` (from an external secret store), never in the image.
- Helm: keep `values.yaml` documented and minimal; add `values.schema.json` so bad values fail at install. Use `helm-docs` for the README.
- Helm 4 is current (Nov 2025); chart `apiVersion: v2` still works. Test charts with the Helm major your clusters use.

## Security

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
  seccompProfile:
    type: RuntimeDefault
```

- Apply the block above to every container. Enforce the `restricted` Pod Security Standard on namespaces (`pod-security.kubernetes.io/enforce: restricted`).
- Dedicated `ServiceAccount` per workload; `automountServiceAccountToken: false` unless it calls the API. Least-privilege RBAC, no `cluster-admin`.
- Default-deny `NetworkPolicy` per namespace, then allow what is needed.
- No `hostNetwork`, `hostPID`, `hostPath` or `privileged: true`.
- Scan manifests and charts: `trivy config .` or `checkov -d .`.

## Tests

- `ct lint-and-install` against a throwaway cluster (kind) on every chart PR; it installs and runs `helm test`.
- Write `helm test` hooks (a Job that calls the service) for each chart.
- Unit-test templates with the `helm-unittest` plugin: assert rendered fields for each important values combination.
- Policy-as-code (Kyverno or OPA/Conftest) for house rules, tested in CI like code.
