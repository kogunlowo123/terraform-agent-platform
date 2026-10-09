variable "name" {
  description = "Cognitive account name (typically \"<prefix>-aoai\")."
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9][a-zA-Z0-9-]{1,62}$", var.name))
    error_message = "name must be 2-63 alphanumeric/hyphen characters."
  }
}

variable "resource_group_name" {
  description = "Resource group to deploy into."
  type        = string
}

variable "location" {
  description = "Azure region with Azure OpenAI capacity."
  type        = string
}

variable "custom_subdomain_name" {
  description = "Custom subdomain (required for private endpoints and Entra auth). Null defaults to name."
  type        = string
  default     = null
}

variable "sku_name" {
  description = "Cognitive account SKU."
  type        = string
  default     = "S0"
}

variable "public_network_access_enabled" {
  description = "Allow public network access. Default false — use the private endpoint."
  type        = bool
  default     = false
}

variable "local_auth_enabled" {
  description = "Allow API-key auth. Default false: Entra ID (RBAC) only."
  type        = bool
  default     = false
}

variable "deployments" {
  description = "Model deployments keyed by deployment name."
  type = map(object({
    model           = string                       # e.g. "gpt-4o"
    version         = string                       # e.g. "2024-08-06"
    capacity        = number                       # TPM units (thousands)
    sku_name        = optional(string, "Standard") # Standard | GlobalStandard | ProvisionedManaged | ...
    rai_policy_name = optional(string)             # content filter policy reference
  }))
  default = {}

  validation {
    condition     = alltrue([for d in values(var.deployments) : d.capacity > 0])
    error_message = "deployment capacity must be a positive number."
  }
}

variable "customer_managed_key" {
  description = "CMK config: Key Vault key ID + user-assigned identity with wrap/unwrap on it. Null uses Microsoft-managed keys."
  type = object({
    key_vault_key_id   = string
    identity_client_id = string
    identity_id        = string # full resource ID of the user-assigned identity
  })
  default = null
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
  description = "Log Analytics workspace for diagnostic settings. Null disables."
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default     = {}
}
