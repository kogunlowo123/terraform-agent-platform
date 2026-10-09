# terraform/azure/landing-zone — resource group set with management locks,
# a central Log Analytics workspace, subscription activity log diagnostics,
# and guardrail policy assignments (allowed locations, required tags).

data "azurerm_subscription" "current" {}

locals {
  tags = merge(var.tags, { managed_by = "tap" })

  # Built-in policy definition IDs (Azure global constants).
  policy_allowed_locations = "/providers/Microsoft.Authorization/policyDefinitions/e56962a6-4747-49cd-b67b-bf8b01975c4c"
  policy_require_tag       = "/providers/Microsoft.Authorization/policyDefinitions/871b6d14-10aa-478d-b590-94f262ecfa99"
}

# ---------------------------------------------------------------------------
# Resource groups + locks
# ---------------------------------------------------------------------------

resource "azurerm_resource_group" "this" {
  for_each = var.resource_groups

  name     = "${var.name}-${each.key}-rg"
  location = coalesce(each.value.location, var.location)

  tags = merge(local.tags, each.value.tags)
}

resource "azurerm_management_lock" "this" {
  for_each = var.enable_locks ? var.resource_groups : {}

  name       = "${var.name}-${each.key}-lock"
  scope      = azurerm_resource_group.this[each.key].id
  lock_level = var.lock_level
  notes      = "TAP landing zone lock — remove through a governed TAP run only."
}

# ---------------------------------------------------------------------------
# Log Analytics workspace (central destination for diagnostic settings)
# ---------------------------------------------------------------------------

resource "azurerm_log_analytics_workspace" "this" {
  name                = "${var.name}-law"
  location            = azurerm_resource_group.this[var.management_group_key].location
  resource_group_name = azurerm_resource_group.this[var.management_group_key].name

  sku               = "PerGB2018"
  retention_in_days = var.log_analytics_retention_days

  internet_ingestion_enabled = true
  internet_query_enabled     = true

  tags = local.tags

  lifecycle {
    precondition {
      condition     = contains(keys(var.resource_groups), var.management_group_key)
      error_message = "management_group_key must be a key of resource_groups."
    }
  }
}

# ---------------------------------------------------------------------------
# Subscription activity log → Log Analytics
# ---------------------------------------------------------------------------

resource "azurerm_monitor_diagnostic_setting" "activity_log" {
  count = var.enable_activity_log_diagnostics ? 1 : 0

  name                       = "${var.name}-activity-log"
  target_resource_id         = data.azurerm_subscription.current.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  dynamic "enabled_log" {
    for_each = toset(["Administrative", "Security", "Policy", "Alert", "Recommendation", "ResourceHealth"])

    content {
      category = enabled_log.value
    }
  }
}

# ---------------------------------------------------------------------------
# Policy assignments (subscription scope)
# ---------------------------------------------------------------------------

resource "azurerm_subscription_policy_assignment" "allowed_locations" {
  count = length(var.allowed_locations) > 0 ? 1 : 0

  name                 = "${var.name}-allowed-locations"
  display_name         = "TAP: allowed locations"
  subscription_id      = data.azurerm_subscription.current.id
  policy_definition_id = local.policy_allowed_locations
  enforce              = var.policy_enforcement_mode == "Default"

  parameters = jsonencode({
    listOfAllowedLocations = {
      value = var.allowed_locations
    }
  })
}

resource "azurerm_subscription_policy_assignment" "require_tags" {
  for_each = toset(var.required_tag_keys)

  name                 = "${var.name}-require-tag-${each.value}"
  display_name         = "TAP: require tag '${each.value}' on resources"
  subscription_id      = data.azurerm_subscription.current.id
  policy_definition_id = local.policy_require_tag
  enforce              = var.policy_enforcement_mode == "Default"

  parameters = jsonencode({
    tagName = {
      value = each.value
    }
  })
}
