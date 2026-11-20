# Service mesh (Istio ambient, Linkerd, Cilium)

Written for Istio 1.32.0, Linkerd 2.20 (edge-26.11.2), Cilium 1.20.5 (Nov 2026), not benchmarked.

## When not to use one

- Few services, one team, no zero-trust or compliance need: skip the mesh. Use NetworkPolicy, TLS at the ingress and app-level retries.
- Only need encryption between nodes: Cilium WireGuard or IPsec (strict mode drops unencrypted traffic) is simpler than a mesh.
- No one owns its upgrades, certificates and debugging: a mesh you cannot operate is a new outage source.
- Adopt one when you need workload identity, mTLS everywhere, L7 policy or uniform traffic metrics across many services. Write the reason in an ADR.

## Lint and validate

- Istio: `istioctl x precheck` before install or upgrade; `istioctl analyze -A` in CI on rendered manifests and against the cluster.
- Linkerd: `linkerd check --pre`, then `linkerd check` and `linkerd check --proxy` after install and every upgrade.
- Cilium: `cilium status --wait`, then `cilium connectivity test`.
- Validate mesh CRDs with kubeconform plus their schemas (see `kubernetes.md`).

## Practices

- Look up current versions on istio.io/latest/docs/releases/supported-releases, linkerd.io/releases, github.com/cilium/cilium/releases.
- Istio: prefer ambient mode (GA since 1.24): `istioctl install --set profile=ambient`, enroll namespaces with label `istio.io/dataplane-mode=ambient`. Add a waypoint only for namespaces that need L7 policy.
- Linkerd: the project publishes edge releases; stable releases come from Buoyant (Buoyant Enterprise for Linkerd). Pick a channel on purpose.
- Cilium: ztunnel mTLS is beta (since 1.19, still beta in 1.20); its older mutual-auth feature is off by default. Enroll a namespace with label `io.cilium/mtls-enabled=true`.
- Upgrade one minor at a time, within the supported Kubernetes range of each release.
- Install with Helm or the vendor CLI from Git, pinned; never `kubectl apply` from a URL.

## Security

- Enforce mTLS, not just enable it. Istio: mesh-wide `PeerAuthentication` with `mtls.mode: STRICT`.

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
```

- Default-deny authorization, then allow by workload identity: Istio empty `AuthorizationPolicy` per namespace plus explicit `ALLOW` rules; Linkerd `config.linkerd.io/default-inbound-policy: deny` plus `Server` and `AuthorizationPolicy`.
- Keep Kubernetes `NetworkPolicy` too: the mesh is not your only wall.
- Production CA: Linkerd needs a trust anchor and issuer you manage (cert-manager rotates the issuer). Istio: plug in your own CA instead of the self-signed root.
- Restrict who can edit mesh policy CRDs with RBAC.

## Tests

- After install and each upgrade, run the vendor check (`linkerd check`, `istioctl analyze`, `cilium connectivity test`) in CI against a kind cluster.
- Assert policy: a pod without an allowed identity gets denied; plaintext traffic to a STRICT workload fails.
- Watch golden metrics (success rate, latency, RPS) during canary upgrades; roll back on regression.
