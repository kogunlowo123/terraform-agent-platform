output "tags" {
  description = "Full tag map: extra_tags overlaid by the enforced required tags."
  value       = local.tags
}

output "required_tags" {
  description = "Only the enforced required tags (owner, cost_center, environment, data_class, managed_by)."
  value       = local.required_tags
}

output "required_tag_keys" {
  description = "Keys TAP policy gates assert on every resource."
  value       = keys(local.required_tags)
}
