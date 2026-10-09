# kubernetes/tap-runtime

Namespace-scoped runtime where TAP's ephemeral runner pods execute:

- Namespace labeled **Pod Security `restricted`** (enforce + audit + warn).
- Runner **ServiceAccount with `automount_service_account_token = false`** —
  runners get cloud access via short-lived OIDC exchange only.
- **ResourceQuota** and **LimitRange** so runaway plans can't starve the node.
- **NetworkPolicy**: default deny ingress+egress, then explicit allows for
  DNS, HTTPS to cloud APIs (metadata endpoint excluded by default), and the
  in-cluster OPA policy service.

## Usage

```hcl
module "tap_runtime" {
  source = "../../terraform/kubernetes/tap-runtime"

  namespace            = "tap-runtime"
  service_account_name = "tap-runner"

  resource_quota = {
    requests_cpu = "16"
    pods         = "100"
  }

  labels = module.tags.tags
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `namespace` | `string` | `"tap-runtime"` | Runtime namespace. |
| `service_account_name` | `string` | `"tap-runner"` | Runner SA. |
| `pod_security_level` | `string` | `"restricted"` | PSS enforce level. |
| `resource_quota` | `object` | 8 CPU / 16Gi req, 50 pods | Quota hard limits. |
| `container_limits` | `object` | 500m/512Mi default | LimitRange values. |
| `egress_cidrs` | `list(object)` | all minus RFC1918 + metadata | HTTPS egress allow. |
| `opa_endpoints` | `object` | ns `tap-system`, port 8181 | OPA egress allow. |
| `labels` | `map(string)` | `{}` | Extra labels. |

## Outputs

| Name | Description |
|---|---|
| `namespace` | Namespace name. |
| `service_account_name` | Runner SA name. |
| `network_policy_names` | Policies created. |
