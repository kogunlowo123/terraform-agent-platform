# terraform/shared/tags — required-tag enforcement for TAP.
# Centralizes the mandatory tag set that TAP OPA policies assert on every
# resource. Modules merge `module.tags.tags` into their provider tags.

locals {
  required_tags = {
    owner       = var.owner
    cost_center = var.cost_center
    environment = lower(var.environment)
    data_class  = lower(var.data_class)
    managed_by  = "tap"
  }

  # Required tags take precedence over any extras.
  tags = merge(var.extra_tags, local.required_tags)
}
