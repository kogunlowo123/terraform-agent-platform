# terraform/aws/route53 — hosted zone (public or private) plus a typed record
# map supporting standard and alias records.

locals {
  tags = merge(var.tags, { managed_by = "tap" })
}

resource "aws_route53_zone" "this" {
  name          = var.zone_name
  comment       = var.comment
  force_destroy = var.force_destroy

  dynamic "vpc" {
    for_each = var.private_zone ? toset(var.vpc_ids) : []

    content {
      vpc_id = vpc.value
    }
  }

  tags = local.tags

  lifecycle {
    precondition {
      condition     = !var.private_zone || length(var.vpc_ids) > 0
      error_message = "private_zone = true requires at least one entry in vpc_ids."
    }
  }
}

resource "aws_route53_record" "this" {
  for_each = var.records

  zone_id = aws_route53_zone.this.zone_id
  name    = each.value.name
  type    = each.value.type

  # TTL and records only apply to non-alias entries.
  ttl     = each.value.alias == null ? each.value.ttl : null
  records = each.value.alias == null ? each.value.records : null

  dynamic "alias" {
    for_each = each.value.alias != null ? [each.value.alias] : []

    content {
      name                   = alias.value.name
      zone_id                = alias.value.zone_id
      evaluate_target_health = alias.value.evaluate_target_health
    }
  }
}
