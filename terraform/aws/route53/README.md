# aws/route53

Hosted zone (public or private) + typed record map. Each record entry sets
exactly one of `records` (standard) or `alias` (ALB/CloudFront/etc.), enforced
by validation.

## Usage

```hcl
module "dns" {
  source = "../../terraform/aws/route53"

  zone_name    = "prod.tap.example.com"
  private_zone = true
  vpc_ids      = [module.vpc.vpc_id]

  records = {
    "api A-alias" = {
      name = "api.prod.tap.example.com"
      type = "A"
      alias = {
        name    = aws_lb.api.dns_name
        zone_id = aws_lb.api.zone_id
      }
    }
    "qdrant CNAME" = {
      name    = "qdrant.prod.tap.example.com"
      type    = "CNAME"
      ttl     = 60
      records = ["qdrant.vector.svc.cluster.local"]
    }
  }

  tags = module.tags.tags
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `zone_name` | `string` | — | DNS zone name. |
| `private_zone` | `bool` | `false` | Private hosted zone. |
| `vpc_ids` | `list(string)` | `[]` | Required when private. |
| `comment` | `string` | `"Managed by TAP"` | Zone comment. |
| `force_destroy` | `bool` | `false` | Allow destroy with records. |
| `records` | `map(object)` | `{}` | Standard or alias records. |
| `tags` | `map(string)` | `{}` | Zone tags. |

## Outputs

| Name | Description |
|---|---|
| `zone_id`, `zone_arn`, `zone_name` | Zone identifiers. |
| `name_servers` | Delegation NS set. |
| `record_fqdns` | key => FQDN map. |
