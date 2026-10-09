# shared/naming

Locals-only module producing the TAP naming prefix and base tag map. Every TAP
root module calls this first and threads `prefix` / `tags_base` into all other
modules so names and tags stay consistent across clouds.

## Usage

```hcl
module "naming" {
  source = "../../terraform/shared/naming"

  org         = "acme"
  environment = "prod"
  region      = "us-east-1"
  name        = "platform"
}

# module.naming.prefix    => "acme-prd-use1-platform"
# module.naming.tags_base => { organization = "acme", environment = "prod", ... }
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `org` | `string` | — | Short org code (2-12 lowercase alphanumerics). |
| `environment` | `string` | — | One of dev/development/test/stage/staging/prod/production/sandbox. |
| `region` | `string` | — | Cloud region (AWS/Azure/GCP) used for the short code. |
| `name` | `string` | `""` | Optional workload segment appended to the prefix. |
| `delimiter` | `string` | `"-"` | `-`, `_`, or `""` between segments. |
| `additional_tags` | `map(string)` | `{}` | Extra tags merged into `tags_base`. |

## Outputs

| Name | Description |
|---|---|
| `prefix` | Deterministic name prefix. |
| `tags_base` | Base tag map including `managed_by = "tap"`. |
| `env_short` | Environment short code. |
| `region_short` | Region short code. |
| `delimiter` | Delimiter in use. |
