variable "name" {
  description = "AKS cluster name (typically \"<prefix>-aks\")."
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9][a-zA-Z0-9-_]{0,61}[a-zA-Z0-9]$", var.name))
    error_message = "name must be 2-63 alphanumeric/hyphen/underscore characters."
  }
}

variable "resource_group_name" {
  description = "Resource group to deploy into."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version (null lets AKS pick the default for the region)."
  type        = string
  default     = null
}

variable "private_cluster_enabled" {
  description = "Private API server (no public endpoint). Default true."
  type        = bool
  default     = true
}

variable "vnet_subnet_id" {
  description = "Subnet ID for node pools (Azure CNI)."
  type        = string
}

variable "network_policy" {
  description = "Network policy engine: azure, calico, or cilium."
  type        = string
  default     = "azure"

  validation {
    condition     = contains(["azure", "calico", "cilium"], var.network_policy)
    error_message = "network_policy must be azure, calico, or cilium."
  }
}

variable "service_cidr" {
  description = "CIDR for Kubernetes services (must not overlap the VNet)."
  type        = string
  default     = "172.20.0.0/16"
}

variable "dns_service_ip" {
  description = "IP within service_cidr for cluster DNS."
  type        = string
  default     = "172.20.0.10"
}

variable "system_node_pool" {
  description = "System node pool (CriticalAddonsOnly) configuration."
  type = object({
    vm_size   = optional(string, "Standard_D4s_v5")
    min_count = optional(number, 2)
    max_count = optional(number, 4)
    zones     = optional(list(string), ["1", "2", "3"])
  })
  default = {}
}

variable "user_node_pools" {
  description = "User node pools keyed by pool name (1-12 lowercase alphanumerics)."
  type = map(object({
    vm_size      = optional(string, "Standard_D8s_v5")
    min_count    = optional(number, 1)
    max_count    = optional(number, 10)
    zones        = optional(list(string), ["1", "2", "3"])
    os_disk_type = optional(string, "Managed")
    node_labels  = optional(map(string), {})
    node_taints  = optional(list(string), [])
    spot_enabled = optional(bool, false)
  }))
  default = {
    workload = {}
  }

  validation {
    condition     = alltrue([for k in keys(var.user_node_pools) : can(regex("^[a-z][a-z0-9]{0,11}$", k))])
    error_message = "user node pool names must be 1-12 lowercase alphanumeric characters starting with a letter."
  }
}

variable "admin_group_object_ids" {
  description = "Entra ID group object IDs granted cluster-admin via Azure RBAC."
  type        = list(string)
  default     = []
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace for Container Insights and diagnostic settings. Null disables both."
  type        = string
  default     = null
}

variable "sku_tier" {
  description = "AKS SKU tier (Free or Standard; Standard gives the uptime SLA)."
  type        = string
  default     = "Standard"

  validation {
    condition     = contains(["Free", "Standard"], var.sku_tier)
    error_message = "sku_tier must be Free or Standard."
  }
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default     = {}
}
