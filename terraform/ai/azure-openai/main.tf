# terraform/ai/azure-openai — Azure OpenAI cognitive account with model
# deployments, private endpoint, optional CMK, Entra-only auth by default,
# and per-deployment content filter (RAI) policy references.

locals {
  tags = merge(var.tags, { managed_by = "tap" })

  custom_subdomain = coalesce(var.custom_subdomain_name, lower(var.name))
}

resource "azurerm_cognitive_account" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  kind                = "OpenAI"
  sku_name            = var.sku_name

  custom_subdomain_name = local.custom_subdomain

  public_network_access_enabled      = var.public_network_access_enabled
  local_auth_enabled                 = var.local_auth_enabled
  outbound_network_access_restricted = true

  dynamic "identity" {
    for_each = var.customer_managed_key != null ? [1] : []

    content {
      type         = "UserAssigned"
      identity_ids = [var.customer_managed_key.identity_id]
    }
  }

  dynamic "identity" {
    for_each = var.customer_managed_key == null ? [1] : []

    content {
      type = "SystemAssigned"
    }
  }

  dynamic "customer_managed_key" {
    for_each = var.customer_managed_key != null ? [var.customer_managed_key] : []

    content {
      key_vault_key_id   = customer_managed_key.value.key_vault_key_id
      identity_client_id = customer_managed_key.value.identity_client_id
    }
  }

  network_acls {
    default_action = "Deny"
  }

  tags = local.tags
}

# ---------------------------------------------------------------------------
# Model deployments
# ---------------------------------------------------------------------------

resource "azurerm_cognitive_deployment" "this" {
  for_each = var.deployments

  name                 = each.key
  cognitive_account_id = azurerm_cognitive_account.this.id

  model {
    format  = "OpenAI"
    name    = each.value.model
    version = each.value.version
  }

  sku {
    name     = each.value.sku_name
    capacity = each.value.capacity
  }

  rai_policy_name        = each.value.rai_policy_name
  version_upgrade_option = "OnceNewDefaultVersionAvailable"
}

# ---------------------------------------------------------------------------
# Private endpoint
# ---------------------------------------------------------------------------

resource "azurerm_private_endpoint" "this" {
  count = var.private_endpoint != null ? 1 : 0

  name                = "${var.name}-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint.subnet_id

  private_service_connection {
    name                           = "${var.name}-psc"
    private_connection_resource_id = azurerm_cognitive_account.this.id
    subresource_names              = ["account"]
    is_manual_connection           = false
  }

  dynamic "private_dns_zone_group" {
    for_each = length(var.private_endpoint.private_dns_zone_ids) > 0 ? [1] : []

    content {
      name                 = "${var.name}-dns"
      private_dns_zone_ids = var.private_endpoint.private_dns_zone_ids
    }
  }

  tags = local.tags
}

# ---------------------------------------------------------------------------
# Diagnostic settings → Log Analytics
# ---------------------------------------------------------------------------

resource "azurerm_monitor_diagnostic_setting" "this" {
  count = var.log_analytics_workspace_id != null ? 1 : 0

  name                       = "${var.name}-diag"
  target_resource_id         = azurerm_cognitive_account.this.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "Audit"
  }

  enabled_log {
    category = "RequestResponse"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
