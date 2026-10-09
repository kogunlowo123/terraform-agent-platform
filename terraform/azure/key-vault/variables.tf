variable "name" {
  description = "Key Vault name (3-24 alphanumerics/hyphens, globally unique)."
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9-]{1,22}[a-zA-Z0-9]$", var.name))
    error_message = "name must be 3-24 alphanumeric/hyphen characters starting with a letter."
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

variable "sku_name" {
  description = "Vault SKU: standard or premium (HSM-backed keys)."
  type        = string
  default     = "standard"

  validation {
    condition     = contains(["standard", "premium"], var.sku_name)
    error_message = "sku_name must be standard or premium."
  }
}

variable "soft_delete_retention_days" {
  description = "Soft-delete retention (7-90 days)."
  type        = number
  default     = 90

  validation {
    condition     = var.soft_delete_retention_days >= 7 && var.soft_delete_retention_days <= 90
    error_message = "soft_delete_retention_days must be between 7 and 90."
  }
}

variable "public_network_access_enabled" {
  description = "Allow access from public networks. Default false — use the private endpoint."
  type        = bool
  default     = false
}

variable "allowed_ip_rules" {
  description = "Public IP CIDRs allowed through the vault firewall (only relevant when public access is on)."
  type        = list(string)
  default     = []
}

variable "allowed_subnet_ids" {
  description = "VNet subnet IDs allowed through the vault firewall (service endpoints)."
  type        = list(string)
  default     = []
}

variable "private_endpoint" {
  description = "Private endpoint config. Null skips creation."
  type = object({
    subnet_id            = string
    private_dns_zone_ids = optional(list(string), [])
  })
  default = null
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace for diagnostic settings (audit events). Null disables."
  type        = string
  default     = null
}

variable "enabled_for_deployment" {
  description = "Allow Azure VMs to retrieve certificates from the vault."
  type        = bool
  default     = false
}

variable "enabled_for_disk_encryption" {
  description = "Allow Azure Disk Encryption to retrieve secrets/unwrap keys."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default     = {}
}
