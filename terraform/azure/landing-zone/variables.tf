variable "name" {
  description = "Name prefix for landing zone resources (typically module.naming.prefix)."
  type        = string

  validation {
    condition     = length(var.name) > 0
    error_message = "name must not be empty."
  }
}

variable "location" {
  description = "Default Azure region for resource groups."
  type        = string
}

variable "resource_groups" {
  description = "Resource groups to create, keyed by short name (appended to the prefix)."
  type = map(object({
    location = optional(string) # defaults to var.location
    tags     = optional(map(string), {})
  }))

  validation {
    condition     = length(var.resource_groups) > 0
    error_message = "Provide at least one resource group."
  }
}

variable "enable_locks" {
  description = "Place management locks on every resource group."
  type        = bool
  default     = true
}

variable "lock_level" {
  description = "Lock level applied to resource groups."
  type        = string
  default     = "CanNotDelete"

  validation {
    condition     = contains(["CanNotDelete", "ReadOnly"], var.lock_level)
    error_message = "lock_level must be CanNotDelete or ReadOnly."
  }
}

variable "management_group_key" {
  description = "Key of the resource group (from resource_groups) that hosts the Log Analytics workspace."
  type        = string
}

variable "log_analytics_retention_days" {
  description = "Log Analytics data retention in days."
  type        = number
  default     = 90

  validation {
    condition     = var.log_analytics_retention_days >= 30 && var.log_analytics_retention_days <= 730
    error_message = "log_analytics_retention_days must be between 30 and 730."
  }
}

variable "enable_activity_log_diagnostics" {
  description = "Ship the subscription activity log to the Log Analytics workspace."
  type        = bool
  default     = true
}

variable "allowed_locations" {
  description = "Regions permitted by the allowed-locations policy assignment. Empty list disables the assignment."
  type        = list(string)
  default     = []
}

variable "required_tag_keys" {
  description = "Tag keys enforced on resources via policy assignment (one assignment per key). Empty disables."
  type        = list(string)
  default     = ["owner", "cost_center", "environment", "data_class"]
}

variable "policy_enforcement_mode" {
  description = "Policy assignment enforcement: \"Default\" enforces, \"DoNotEnforce\" audits only."
  type        = string
  default     = "Default"

  validation {
    condition     = contains(["Default", "DoNotEnforce"], var.policy_enforcement_mode)
    error_message = "policy_enforcement_mode must be Default or DoNotEnforce."
  }
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default     = {}
}
