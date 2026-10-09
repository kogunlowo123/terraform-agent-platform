# azure/key-vault

Hardened Key Vault:

- **RBAC authorization** only (no access policies).
- **Purge protection** on, 90-day soft delete.
- Public network access **off** by default with a deny-all firewall
  (`bypass = AzureServices`); optional private endpoint + DNS zone group.
- Audit diagnostics to Log Analytics.

## Usage

```hcl
module "key_vault" {
  source = "../../terraform/azure/key-vault"

  name                = "${module.naming.prefix}-kv"
  resource_group_name = module.landing_zone.resource_group_names["ai"]
  location            = "westeurope"

  private_endpoint = {
    subnet_id            = azurerm_subnet.endpoints.id
    private_dns_zone_ids = [azurerm_private_dns_zone.kv.id]
  }

  log_analytics_workspace_id = module.landing_zone.log_analytics_workspace_id

  tags = module.tags.tags
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `string` | — | Vault name (3-24 chars, globally unique). |
| `resource_group_name`, `location` | `string` | — | Placement. |
| `sku_name` | `string` | `"standard"` | Or `premium` (HSM). |
| `soft_delete_retention_days` | `number` | `90` | 7–90. |
| `public_network_access_enabled` | `bool` | `false` | Keep false. |
| `allowed_ip_rules` / `allowed_subnet_ids` | `list` | `[]` | Firewall exceptions. |
| `private_endpoint` | `object` | `null` | Subnet + DNS zones. |
| `log_analytics_workspace_id` | `string` | `null` | Audit diagnostics. |
| `enabled_for_deployment` / `enabled_for_disk_encryption` | `bool` | `false` | Azure service access. |
| `tags` | `map(string)` | `{}` | Tags. |

## Outputs

| Name | Description |
|---|---|
| `key_vault_id`, `key_vault_name`, `key_vault_uri` | Vault identifiers. |
| `private_endpoint_id`, `private_endpoint_ip` | Private endpoint details. |
