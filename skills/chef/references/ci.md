# CI/CD (GitHub Actions, GitLab CI)

Verified against actions/checkout 7.0.1, actionlint 1.7.12, zizmor 1.32, act 0.2.98 (Nov 2026).

## Lint and validate

- Lint workflows with actionlint (runs ShellCheck on `run:` blocks): `actionlint`.
- Audit workflow security with zizmor: `zizmor .github/workflows/`. Fail on findings; fix template injection, excessive permissions and unpinned actions.
- GitLab: validate `.gitlab-ci.yml` with the CI Lint API or `glab ci lint`.
- Check GitHub workflows in one call, failing if either fails: `rc=0; actionlint || rc=1; zizmor .github/workflows/ || rc=1; [ "$rc" -eq 0 ]`.

## Practices

Required checks on every PR, all blocking, in this order (fast first):

1. Format check
2. Lint (warnings are errors)
3. Type check
4. Tests with coverage; fail under 90% line and branch
5. Security: dependency audit, secret scan (gitleaks), SAST, image/IaC scan where relevant

- Mark these jobs as required status checks in branch protection or rulesets.
- Cache dependencies by lockfile hash (`actions/setup-*` with `cache:`, or `actions/cache` keyed on `hashFiles('**/lockfile')`).
- Set `timeout-minutes` on every job and `concurrency` with `cancel-in-progress: true` for PR workflows.
- Run the same commands locally and in CI (a `Makefile`/`justfile`/script), not logic only CI knows.
- Keep Dependabot or Renovate on for actions, base images and packages.

```yaml
name: ci
on: [pull_request]
permissions: {}
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@<full-sha> # v7.0.1
        with:
          persist-credentials: false
      - run: make fmt-check lint typecheck test
```

## Security

- Pin every third-party action to a full 40-char commit SHA with the tag in a comment. Tags are mutable: trivy-action tags were hijacked in March 2026. Enable the "require SHA pinning" policy in repo or org settings.
- Get the real SHA, never invent one: `gh api repos/actions/checkout/commits/v7.0.1 --jq .sha` (or `curl -s https://api.github.com/repos/actions/checkout/commits/v7.0.1`): it resolves annotated tags to the commit. Pin the exact release tag, not the moving major tag. If no tool can reach GitHub, keep the tag and tell the user the SHA is still to pin.
- `permissions: {}` at the top, then grant the least each job needs (`contents: read`, `id-token: write` only for deploy).
- Use OIDC to the cloud (`id-token: write` plus the cloud's federated role) instead of long-lived keys in secrets. GitLab: `id_tokens:` with an `aud`.
- Never use `pull_request_target` or `workflow_run` with a checkout of PR code. Never interpolate `${{ github.event.* }}` into `run:`; pass it through `env:`.
- `persist-credentials: false` on checkout unless the job pushes.
- Deploy jobs run in protected environments with required reviewers; secrets are scoped to those environments.
- GitLab: protected branches and variables, `rules:` instead of `only/except`, pin `include:` templates and images by SHA/digest.

## Tests

- Test the pipeline itself: run workflows on a PR before relying on them; use `act` for quick local runs.
- A coverage or security gate that never fails is broken: check it fails on a deliberate bad commit once.
- Upload test reports (JUnit) and coverage as artifacts so failures are readable.
