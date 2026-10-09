# aws/iam

OIDC federation role for TAP runners — **zero static credentials**. The role
trusts GitHub Actions OIDC and/or the TAP platform issuer, always conditioned
on explicit `sub`/`aud` claims (bare wildcards are rejected by validation).
Supports permission boundaries and least-privilege inline/managed policies.

## Usage

```hcl
module "runner_role" {
  source = "../../terraform/aws/iam"

  role_name = "${module.naming.prefix}-tap-runner"

  enable_github_oidc = true
  github_subjects    = ["repo:acme/infra-live:environment:prod"]

  tap_oidc_issuer_url  = "https://oidc.tap.example.com"
  tap_oidc_audience    = "tap-runner"
  tap_oidc_thumbprints = ["0123456789abcdef0123456789abcdef01234567"]
  tap_subjects         = ["workspace:acme/prod/*"]

  permissions_boundary_arn = "arn:aws:iam::123456789012:policy/tap-runner-boundary"

  inline_policies = {
    state-access = data.aws_iam_policy_document.state.json
  }

  tags = module.tags.tags
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `role_name` | `string` | — | IAM role name. |
| `enable_github_oidc` | `bool` | `false` | Trust GitHub Actions. |
| `github_oidc_provider_arn` | `string` | `null` | Reuse existing provider; null creates one. |
| `github_subjects` | `list(string)` | `[]` | Allowed `repo:...` sub claims. |
| `tap_oidc_provider_arn` | `string` | `null` | Reuse existing TAP provider. |
| `tap_oidc_issuer_url` | `string` | `null` | TAP issuer; null disables TAP trust. |
| `tap_oidc_audience` | `string` | `"tap-runner"` | Expected aud claim. |
| `tap_oidc_thumbprints` | `list(string)` | `[]` | Issuer thumbprints (create path). |
| `tap_subjects` | `list(string)` | `[]` | Allowed TAP sub claims. |
| `policy_arns` | `list(string)` | `[]` | Managed policies. |
| `inline_policies` | `map(string)` | `{}` | name => JSON document. |
| `permissions_boundary_arn` | `string` | `null` | Permission boundary. |
| `max_session_duration` | `number` | `3600` | Seconds (900–43200). |
| `tags` | `map(string)` | `{}` | Tags. |

## Outputs

| Name | Description |
|---|---|
| `role_arn`, `role_name` | The federated role. |
| `github_oidc_provider_arn` | GitHub provider in use. |
| `tap_oidc_provider_arn` | TAP provider in use. |
