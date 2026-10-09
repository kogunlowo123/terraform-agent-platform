# ai/azure-openai

Azure OpenAI (Cognitive account, `kind = OpenAI`) with TAP security posture:

- Public network access **off**, deny-all network ACLs, optional **private endpoint**.
- **Entra-only auth** by default (`local_auth_enabled = false`).
- Model deployments as a typed map (model, version, capacity, SKU) with
  per-deployment **content filter policy** reference (`rai_policy_name`).
- Optional **customer-managed key** via user-assigned identity.
- Audit + request/response diagnostics to Log Analytics.

## Usage

```hcl
module "azure_openai" {
  source = "../../terraform/ai/azure-openai"

  name                = "${module.naming.prefix}-aoai"
  resource_group_name = module.landing_zone.resource_group_names["ai"]
  location            = "swedencentral"

  deployments = {
    gpt4o = {
      model    = "gpt-4o"
      version  = "2024-08-06"
      capacity = 50
    }
    embeddings = {
      model           = "text-embedding-3-large"
      version         = "1"
      capacity        = 120
      rai_policy_name = "Microsoft.Default"
    }
  }

  private_endpoint = {
    subnet_id            = azurerm_subnet.endpoints.id
    private_dns_zone_ids = [azurerm_private_dns_zone.openai.id]
  }

  log_analytics_workspace_id = module.landing_zone.log_analytics_workspace_id

  tags = module.tags.tags
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `name`, `resource_group_name`, `location` | `string` | — | Identity and placement. |
| `custom_subdomain_name` | `string` | `null` (= name) | Needed for PE/Entra auth. |
| `sku_name` | `string` | `"S0"` | Account SKU. |
| `public_network_access_enabled` | `bool` | `false` | Keep false. |
| `local_auth_enabled` | `bool` | `false` | API keys off by default. |
| `deployments` | `map(object)` | `{}` | model/version/capacity/sku/rai_policy_name. |
| `customer_managed_key` | `object` | `null` | KV key + UA identity. |
| `private_endpoint` | `object` | `null` | Subnet + DNS zones. |
| `log_analytics_workspace_id` | `string` | `null` | Diagnostics. |
| `tags` | `map(string)` | `{}` | Tags. |

## Outputs

| Name | Description |
|---|---|
| `account_id`, `account_name`, `endpoint`, `custom_subdomain_name` | Account identifiers. |
| `identity_principal_id` | System identity (RBAC grants). |
| `deployment_names` | Deployment map. |
| `private_endpoint_ip` | PE address. |
