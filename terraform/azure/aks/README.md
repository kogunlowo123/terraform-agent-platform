# azure/aks

Private AKS cluster with TAP security posture:

- `private_cluster_enabled = true`, local accounts disabled, Entra ID **Azure RBAC**.
- **Workload identity + OIDC issuer** enabled (no pod credentials).
- Azure CNI with network policy (azure/calico/cilium), standard LB.
- **Key Vault secrets provider** with rotation.
- System pool pinned to critical addons; user pools (spot-capable) via map.
- Container Insights + diagnostic settings to Log Analytics; Azure Policy addon on.

## Usage

```hcl
module "aks" {
  source = "../../terraform/azure/aks"

  name                = "${module.naming.prefix}-aks"
  resource_group_name = module.landing_zone.resource_group_names["ai"]
  location            = "westeurope"
  vnet_subnet_id      = azurerm_subnet.aks.id

  admin_group_object_ids     = ["00000000-0000-0000-0000-000000000000"]
  log_analytics_workspace_id = module.landing_zone.log_analytics_workspace_id

  user_node_pools = {
    runners = {
      vm_size      = "Standard_D8s_v5"
      min_count    = 0
      max_count    = 20
      spot_enabled = true
      node_labels  = { "tap.dev/role" = "runner" }
    }
  }

  tags = module.tags.tags
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `string` | — | Cluster name. |
| `resource_group_name`, `location` | `string` | — | Placement. |
| `kubernetes_version` | `string` | `null` | Null = regional default. |
| `private_cluster_enabled` | `bool` | `true` | Private API server. |
| `vnet_subnet_id` | `string` | — | Node subnet (Azure CNI). |
| `network_policy` | `string` | `"azure"` | azure/calico/cilium. |
| `service_cidr` / `dns_service_ip` | `string` | `172.20.0.0/16` / `.0.10` | Service network. |
| `system_node_pool` | `object` | D4s_v5, 2–4, zones 1-3 | System pool. |
| `user_node_pools` | `map(object)` | one `workload` pool | User pools. |
| `admin_group_object_ids` | `list(string)` | `[]` | Entra admin groups. |
| `log_analytics_workspace_id` | `string` | `null` | Insights + diagnostics. |
| `sku_tier` | `string` | `"Standard"` | Uptime SLA tier. |
| `tags` | `map(string)` | `{}` | Tags. |

## Outputs

| Name | Description |
|---|---|
| `cluster_id`, `cluster_name`, `private_fqdn` | Cluster identifiers. |
| `oidc_issuer_url` | Workload identity federation issuer. |
| `kubelet_identity_object_id`, `cluster_identity_principal_id` | Managed identities. |
| `key_vault_secrets_provider_identity_client_id` | For SecretProviderClass. |
| `node_resource_group` | Node RG. |
| `user_node_pool_ids` | Pool map. |
