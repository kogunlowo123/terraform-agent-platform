# ai/qdrant

Qdrant vector database on Kubernetes via the official `qdrant/qdrant` Helm
chart. TAP's default semantic-memory backend.

- **API key required** (>= 16 chars, passed via `set_sensitive`, stored by the
  chart in a Kubernetes Secret) — no unauthenticated vector stores.
- Persistence on (sized PVCs), bounded resources, restricted-PSS-compatible
  security contexts (non-root, read-only rootfs, no capabilities).
- `atomic` + `cleanup_on_fail` installs; chart version pinned.

## Usage

```hcl
module "qdrant" {
  source = "../../terraform/ai/qdrant"

  namespace        = "vector"
  replicas         = 3
  persistence_size = "100Gi"
  api_key          = var.qdrant_api_key # from TAP secret store, never hardcoded
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `release_name` | `string` | `"qdrant"` | Helm release. |
| `namespace` | `string` | `"vector"` | Created if missing. |
| `chart_version` | `string` | `"1.13.1"` | Pinned chart version. |
| `replicas` | `number` | `3` | Qdrant replicas. |
| `api_key` | `string` (sensitive) | — | Required, >= 16 chars. |
| `persistence_size` | `string` | `"50Gi"` | PVC per replica. |
| `storage_class` | `string` | `null` | Default class when null. |
| `resources` | `object` | 500m/1Gi – 2/4Gi | Requests/limits. |
| `extra_values` | `any` | `{}` | Merged-last Helm values. |

## Outputs

| Name | Description |
|---|---|
| `release_name`, `namespace` | Release coordinates. |
| `service_host` | In-cluster DNS name. |
| `http_port` / `grpc_port` | 6333 / 6334. |
