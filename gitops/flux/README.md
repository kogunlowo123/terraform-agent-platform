# Flux Alternative Wiring

TAP's reference GitOps delivery uses ArgoCD
([`../platform/`](../platform/)). For estates standardized on Flux, the same
topology maps onto `Kustomization` + `HelmRelease` objects. This directory is
a sketch, not a maintained parallel install — keep one of the two per cluster.

## Topology

```
flux-system
└── GitRepository: tap (this repo, branch main)
    ├── Kustomization: tap-infra        (auto, prune, selfHeal-equivalent)
    │     ├── HelmRelease: temporal
    │     ├── HelmRelease: tap-opa
    │     ├── HelmRelease: tap-observability
    │     └── HelmRelease: tap-runners
    └── Kustomization: tap-control-plane (suspended by default = manual)
          └── HelmRelease: tap-control-plane
```

ArgoCD's "manual sync" for the control plane maps to `spec.suspend: true` on
its Kustomization; a release is promoted with
`flux resume kustomization tap-control-plane` after review.

## Source

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: tap
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/example-org/terraform-agent-platform
  ref:
    branch: main
```

## Infra Kustomization (automated, pruning)

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: tap-infra
  namespace: flux-system
spec:
  interval: 5m
  prune: true          # ~ ArgoCD automated.prune
  wait: true
  timeout: 5m
  sourceRef:
    kind: GitRepository
    name: tap
  path: ./gitops/flux/infra
```

Drift is reverted on every reconcile interval — the Flux equivalent of
ArgoCD `selfHeal`.

## HelmRelease sketch (Temporal)

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: temporal
  namespace: tap-temporal
spec:
  interval: 10m
  chart:
    spec:
      chart: temporal
      version: "0.50.0"
      sourceRef:
        kind: HelmRepository
        name: temporal
        namespace: flux-system
  values:
    server:
      replicaCount: 3
    cassandra: { enabled: false }
    postgresql: { enabled: false }   # external HA Postgres
  install:
    remediation: { retries: 3 }
  upgrade:
    remediation: { retries: 3, remediateLastFailure: true }
```

## Control plane Kustomization (manual promotion)

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: tap-control-plane
  namespace: flux-system
spec:
  suspend: true        # resume to promote a release
  interval: 10m
  prune: true
  sourceRef:
    kind: GitRepository
    name: tap
  path: ./gitops/flux/control-plane
```

## Image automation (optional)

Flux's `ImageUpdateAutomation` can bump runner image tags on signed releases;
restrict it with an `ImagePolicy` that only accepts semver tags matching the
cosign-verified release stream, mirroring the marketplace verification rules
in [`../../docs/architecture/ARCHITECTURE.md`](../../docs/architecture/ARCHITECTURE.md) §12.
