output "resource_group_ids" {
  description = "Map of resource group key => ID."
  value       = { for k, rg in azurerm_resource_group.this : k => rg.id }
}

output "resource_group_names" {
  description = "Map of resource group key => name."
  value       = { for k, rg in azurerm_resource_group.this : k => rg.name }
}

output "resource_group_locations" {
  description = "Map of resource group key => location."
  value       = { for k, rg in azurerm_resource_group.this : k => rg.location }
}

output "log_analytics_workspace_id" {
  description = "Resource ID of the central Log Analytics workspace."
  value       = azurerm_log_analytics_workspace.this.id
}

output "log_analytics_workspace_name" {
  description = "Name of the central Log Analytics workspace."
  value       = azurerm_log_analytics_workspace.this.name
}

output "policy_assignment_ids" {
  description = "IDs of all policy assignments created by this module."
  value = concat(
    [for a in azurerm_subscription_policy_assignment.allowed_locations : a.id],
    [for a in values(azurerm_subscription_policy_assignment.require_tags) : a.id]
  )
}
