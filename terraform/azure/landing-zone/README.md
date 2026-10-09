# azure/landing-zone

Subscription-level landing zone:

- Resource group set (keyed map) with `CanNotDelete` management locks.
- Central Log Analytics workspace; subscription activity log shipped to it.
- Guardrail policy assignments: **allowed locations** and **require tag**
  (one assignment per required tag key), enforce or audit-only.

## Usage

```hcl
module "landing_zone" {
  source = "../../terraform/azure/landing-zone"

  name     = module.naming.prefix
  location = "westeurope"

  resource_groups = {
    mgmt = {}
    ai   = {}
    data = { location = "northeurope" }
  }

  management_group_key = "mgmt"
  allowed_locations    = ["westeurope", "northeurope"]
  required_tag_keys    = ["owner", "cost_center", "environment", "data_class"]

  tags = module.tags.tags
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `string` | — | Prefix for all resources. |
| `location` | `string` | — | Default region. |
| `resource_groups` | `map(object)` | — | RG set keyed by short name. |
| `enable_locks` | `bool` | `true` | Management locks on RGs. |
| `lock_level` | `string` | `"CanNotDelete"` | Or `ReadOnly`. |
| `management_group_key` | `string` | — | RG key hosting Log Analytics. |
| `log_analytics_retention_days` | `number` | `90` | 30–730. |
| `enable_activity_log_diagnostics` | `bool` | `true` | Activity log → LAW. |
| `allowed_locations` | `list(string)` | `[]` | Policy; empty disables. |
| `required_tag_keys` | `list(string)` | owner, cost_center, environment, data_class | Require-tag policies. |
| `policy_enforcement_mode` | `string` | `"Default"` | Or `DoNotEnforce` (audit). |
| `tags` | `map(string)` | `{}` | Tags. |

## Outputs

| Name | Description |
|---|---|
| `resource_group_ids` / `resource_group_names` / `resource_group_locations` | RG maps. |
| `log_analytics_workspace_id` / `log_analytics_workspace_name` | Central LAW. |
| `policy_assignment_ids` | All policy assignments. |
