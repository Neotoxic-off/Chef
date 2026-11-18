# GitOps: Argo CD and Flux

Verified Nov 2026: Argo CD 3.x (minor release every 3 months), Flux 2.8.x (v1beta2 Source and Kustomization APIs removed; run `flux migrate` before upgrading). Check current versions with `gh release list -R argoproj/argo-cd -L 1` and `gh release list -R fluxcd/flux2 -L 1`.

## Lint and validate

- Render every app in CI and validate the output: `kustomize build overlays/prod | kubeconform -strict -summary -ignore-missing-schemas=false`.
- Helm: `helm lint` and `helm template ... | kubeconform -strict`.
- Scan rendered manifests: `trivy config .`, `checkov -d .` or `kube-linter lint`. Fail CI on HIGH/CRITICAL.
- Show the cluster diff on PRs: `argocd app diff <app> --local <path>` or `flux diff kustomization <name> --path <path>`.
- Flux: `flux check --pre` before install; `flux build kustomization` to render locally.

## Practices

- Git is the source of truth. No `kubectl apply` or `kubectl edit` on GitOps-managed resources.
- Separate the app source repo from the environment config repo, or use one repo with one directory per environment.
- Promote between environments by PR (bump the image tag or digest), not by branch merges.
- Pin images by digest or immutable tag; pin Helm chart versions and Git sources to tags or commits, never a branch head in prod.
- Enable pruning and drift correction: Argo CD `syncPolicy.automated` with `prune: true`, `selfHeal: true`; Flux `prune: true`.
- Order dependencies: Argo CD sync waves; Flux `dependsOn`, `wait: true` and `healthChecks`.
- Generate per-environment or per-cluster apps with Argo CD ApplicationSets or Flux Kustomization overlays, not copy-paste.
- Manage the GitOps controller itself through GitOps (app-of-apps, `flux bootstrap`).

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata: { name: api, namespace: team-api }
spec:
  interval: 10m
  path: ./deploy/prod
  prune: true
  wait: true
  serviceAccountName: team-api-reconciler
  sourceRef: { kind: GitRepository, name: api }
  decryption: { provider: sops, secretRef: { name: sops-age } }
```

## Security

- Argo CD: never use the `default` project for apps. Each AppProject restricts `sourceRepos`, `destinations` and `clusterResourceWhitelist`.
- Argo CD: SSO with RBAC groups; disable the local `admin` user after setup.
- Flux multi-tenancy: reconcile with a namespaced service account (`serviceAccountName`), and run controllers with `--no-cross-namespace-refs` and `--default-service-account`.
- The controller pulls from Git with a read-only deploy key or GitHub App; CI never holds cluster credentials.
- Verify artifacts: Flux `verify` with cosign on OCI sources; Argo CD GPG commit verification where needed.
- No plain secrets in Git. Use SOPS-encrypted files or External Secrets (see `secrets.md`).
- A scanner finding is fixed, or you ask the user. Never add inline skip annotations on your own.

## Tests

- CI renders and validates every environment on every PR; a broken overlay fails the build.
- Run policy tests on rendered manifests (Kyverno CLI `kyverno apply` or Conftest) against the same policies the cluster enforces.
- Spin up an ephemeral cluster (kind) in CI for critical changes: install the controller, sync, wait for health.
