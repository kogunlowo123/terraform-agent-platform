# terraform/azure/aks — private AKS with system/user node pools, Azure CNI,
# workload identity + OIDC issuer, Key Vault secrets provider, Entra ID Azure
# RBAC, local accounts disabled, and diagnostics to Log Analytics.

locals {
  tags = merge(var.tags, { managed_by = "tap" })
}

resource "azurerm_kubernetes_cluster" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = var.name
  kubernetes_version  = var.kubernetes_version
  sku_tier            = var.sku_tier

  private_cluster_enabled = var.private_cluster_enabled
  local_account_disabled  = true
  azure_policy_enabled    = true

  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  role_based_access_control_enabled = true

  azure_active_directory_role_based_access_control {
    azure_rbac_enabled     = true
    admin_group_object_ids = var.admin_group_object_ids
  }

  identity {
    type = "SystemAssigned"
  }

  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }

  default_node_pool {
    name                 = "system"
    vm_size              = var.system_node_pool.vm_size
    vnet_subnet_id       = var.vnet_subnet_id
    zones                = var.system_node_pool.zones
    auto_scaling_enabled = true
    min_count            = var.system_node_pool.min_count
    max_count            = var.system_node_pool.max_count
    os_disk_type         = "Managed"

    only_critical_addons_enabled = true

    upgrade_settings {
      max_surge = "33%"
    }

    tags = local.tags
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = var.network_policy
    load_balancer_sku = "standard"
    outbound_type     = "loadBalancer"
    service_cidr      = var.service_cidr
    dns_service_ip    = var.dns_service_ip
  }

  dynamic "oms_agent" {
    for_each = var.log_analytics_workspace_id != null ? [1] : []

    content {
      log_analytics_workspace_id      = var.log_analytics_workspace_id
      msi_auth_for_monitoring_enabled = true
    }
  }

  maintenance_window_auto_upgrade {
    frequency   = "Weekly"
    interval    = 1
    duration    = 4
    day_of_week = "Sunday"
    start_time  = "02:00"
    utc_offset  = "+00:00"
  }

  automatic_upgrade_channel = "patch"

  tags = local.tags

  lifecycle {
    ignore_changes = [default_node_pool[0].node_count] # autoscaler owns it
  }
}

# ---------------------------------------------------------------------------
# User node pools
# ---------------------------------------------------------------------------

resource "azurerm_kubernetes_cluster_node_pool" "user" {
  for_each = var.user_node_pools

  name                  = each.key
  kubernetes_cluster_id = azurerm_kubernetes_cluster.this.id
  mode                  = "User"

  vm_size              = each.value.vm_size
  vnet_subnet_id       = var.vnet_subnet_id
  zones                = each.value.zones
  auto_scaling_enabled = true
  min_count            = each.value.min_count
  max_count            = each.value.max_count
  os_disk_type         = each.value.os_disk_type

  node_labels = each.value.node_labels
  node_taints = each.value.node_taints

  priority        = each.value.spot_enabled ? "Spot" : "Regular"
  eviction_policy = each.value.spot_enabled ? "Delete" : null
  spot_max_price  = each.value.spot_enabled ? -1 : null

  upgrade_settings {
    max_surge = "33%"
  }

  tags = local.tags

  lifecycle {
    ignore_changes = [node_count]
  }
}

# ---------------------------------------------------------------------------
# Diagnostic settings → Log Analytics
# ---------------------------------------------------------------------------

resource "azurerm_monitor_diagnostic_setting" "this" {
  count = var.log_analytics_workspace_id != null ? 1 : 0

  name                       = "${var.name}-diag"
  target_resource_id         = azurerm_kubernetes_cluster.this.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  dynamic "enabled_log" {
    for_each = toset([
      "kube-apiserver",
      "kube-audit-admin",
      "kube-controller-manager",
      "kube-scheduler",
      "cluster-autoscaler",
      "guard",
    ])

    content {
      category = enabled_log.value
    }
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
