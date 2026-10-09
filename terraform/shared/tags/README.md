# shared/tags

Required-tag enforcement module. Produces the mandatory TAP tag set
(`owner`, `cost_center`, `environment`, `data_class`, `managed_by = "tap"`)
that OPA policy gates assert at plan time. Merge its `tags` output into every
resource/provider `tags`/`labels` argument.

## Usage

```hcl
module "tags" {
  source = "../../terraform/shared/tags"

  owner       = "platform-engineering"
  cost_center = "CC-1042"
  environment = "prod"
  data_class  = "confidential"

  extra_tags = {
    application = "tap"
  }
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `owner` | `string` | — | Accountable team/individual. |
| `cost_center` | `string` | — | Billing code. |
| `environment` | `string` | — | dev/test/stage/staging/prod/... |
| `data_class` | `string` | — | public, internal, confidential, restricted. |
| `extra_tags` | `map(string)` | `{}` | Extras; cannot override required keys. |

## Outputs

| Name | Description |
|---|---|
| `tags` | Merged tag map (required keys win). |
| `required_tags` | Only the enforced tags. |
| `required_tag_keys` | Keys asserted by TAP policies. |
