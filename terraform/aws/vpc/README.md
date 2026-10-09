# aws/vpc

Multi-AZ VPC with three subnet tiers carved via `cidrsubnet`:

- **public** — internet-facing (IGW); no auto public IPs.
- **private** — egress via NAT (single or per-AZ).
- **intra** — no internet route at all (databases, vector stores).

Secure defaults: VPC flow logs to CloudWatch, default security group stripped
of all rules, S3/DynamoDB gateway endpoints so data-plane traffic bypasses NAT.

## Usage

```hcl
module "vpc" {
  source = "../../terraform/aws/vpc"

  name             = module.naming.prefix
  vpc_cidr         = "10.40.0.0/16"
  azs              = ["us-east-1a", "us-east-1b", "us-east-1c"]
  nat_gateway_mode = "per_az"

  tags = module.tags.tags
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `string` | — | Resource name prefix. |
| `vpc_cidr` | `string` | — | VPC IPv4 CIDR. |
| `azs` | `list(string)` | — | 2–4 availability zones. |
| `subnet_newbits` | `number` | `4` | Bits added per subnet (`/16` → `/20`). |
| `nat_gateway_mode` | `string` | `"single"` | `single`, `per_az`, or `none`. |
| `enable_gateway_endpoints` | `bool` | `true` | S3 + DynamoDB gateway endpoints. |
| `flow_logs_enabled` | `bool` | `true` | VPC flow logs to CloudWatch. |
| `flow_logs_retention_days` | `number` | `90` | Log retention. |
| `flow_logs_kms_key_arn` | `string` | `null` | Optional CMK for the log group. |
| `tags` | `map(string)` | `{}` | Tags for all resources. |

## Outputs

| Name | Description |
|---|---|
| `vpc_id`, `vpc_cidr_block` | VPC identifiers. |
| `public_subnet_ids`, `private_subnet_ids`, `intra_subnet_ids` | Subnet IDs per tier. |
| `nat_gateway_ids`, `nat_public_ips` | NAT gateway details. |
| `public_route_table_id`, `private_route_table_ids`, `intra_route_table_id` | Route tables. |
| `flow_log_group_name` | CloudWatch flow log group. |
| `azs` | AZ list, index-aligned with subnets. |
