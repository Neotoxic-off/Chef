# Docker

Verified against Docker Engine 29.9, Buildx 0.39, Compose 5.8, hadolint 2.15, Trivy 0.76, Grype 0.122 (Nov 2026).

## Lint and validate

- Lint every Dockerfile with hadolint in CI; fail on warnings: `hadolint --failure-threshold warning Dockerfile`.
- Lint shell inside `RUN` too: hadolint runs ShellCheck on it. Fix, do not ignore.
- Validate Compose files: `docker compose config --quiet`.
- Check in one call, hadolint from its image when it is not installed (the mount lets it read `.hadolint.yaml`; name every Dockerfile; add the compose check only when a compose file exists): `rc=0; docker run --rm -v "$PWD:/w" -w /w hadolint/hadolint:<tag> hadolint Dockerfile || rc=1; docker compose config --quiet || rc=1; [ "$rc" -eq 0 ]`.

`.hadolint.yaml`:

```yaml
failure-threshold: warning
trustedRegistries:
  - docker.io
  - ghcr.io
```

## Practices

- Multi-stage builds: build in one stage, copy only the artifact into a small runtime stage (distroless, `-slim`, alpine or a hardened image).
- Pin the base image by digest, keep the tag for humans: `FROM python:3.13-slim@sha256:<digest>`. Let Dependabot or Renovate bump it.
- Get the real digest, never invent one, for all images in one call: `for image in python:3.13-slim nginx:1.29-alpine; do printf '%s ' "$image"; docker buildx imagetools inspect "$image" --format '{{.Manifest.Digest}}'; done` (or `crane digest <image>`). If no tool can reach the registry, leave the tag, and tell the user the digest is still to pin.
- Never `:latest`. Pin OS packages where the package manager allows it.
- Order layers from least to most often changed: dependency manifests and install first, source code last.
- Use `COPY`, not `ADD`, unless you need tar extraction.
- Clean package caches in the same `RUN` (`rm -rf /var/lib/apt/lists/*`) or use `RUN --mount=type=cache`.
- Exec form for `CMD`/`ENTRYPOINT` (`["app", "--flag"]`) so signals reach the process.
- Add a `HEALTHCHECK` (or a probe in the orchestrator) that hits a real readiness endpoint.
- Keep a `.dockerignore` that excludes `.git`, `node_modules`, build output, `.env*` and local secrets.
- Compose: no top-level `version:` key (obsolete); use `name:` for the project name. Use `depends_on` with `condition: service_healthy`.

```dockerfile
FROM golang:1.27@sha256:<digest> AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /out/app ./cmd/app

FROM gcr.io/distroless/static-debian13:nonroot@sha256:<digest>
COPY --from=build /out/app /app
USER nonroot:nonroot
ENTRYPOINT ["/app"]
```

## Security

- Run as a non-root user (`USER 10001` or the image's `nonroot`). Never run as root in the final stage.
- No secrets in the image: no `ENV`/`ARG` secrets, no copied `.env`. Use `RUN --mount=type=secret,id=...` at build time.
- Scan every image in CI and fail on fixable HIGH/CRITICAL: `trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed <image>` or `grype <image> --fail-on high`.
- Pin the scanner itself (action by SHA, binary by version and checksum): scanners are supply-chain targets too.
- Generate an SBOM (`docker buildx build --sbom=true` or `syft`) and sign release images (`cosign`).
- Compose and runtime: `read_only: true`, `cap_drop: [ALL]`, `security_opt: ["no-new-privileges:true"]` where the app allows it.

## Tests

- Build the image in CI on every PR; a broken Dockerfile fails the build.
- Smoke-test the built image: start it, wait for the healthcheck, hit one endpoint, check the exit code.
- Use the same image in integration tests (Testcontainers) that you ship.
- Optionally assert image structure with `container-structure-test` (user, entrypoint, files present).
