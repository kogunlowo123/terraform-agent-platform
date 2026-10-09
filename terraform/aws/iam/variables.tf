variable "role_name" {
  description = "Name of the federated IAM role (e.g. \"<prefix>-tap-runner\")."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9+=,.@_-]{1,64}$", var.role_name))
    error_message = "role_name must be 1-64 valid IAM role name characters."
  }
}

variable "enable_github_oidc" {
  description = "Trust GitHub Actions OIDC (token.actions.githubusercontent.com)."
  type        = bool
  default     = false
}

variable "github_oidc_provider_arn" {
  description = "Existing GitHub OIDC provider ARN. Null (with enable_github_oidc) creates one in this account."
  type        = string
  default     = null
}

variable "github_subjects" {
  description = "Allowed GitHub sub claims, e.g. [\"repo:acme/infra:ref:refs/heads/main\", \"repo:acme/infra:environment:prod\"]."
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([for s in var.github_subjects : startswith(s, "repo:")])
    error_message = "Every github_subjects entry must start with \"repo:\" — never use a bare wildcard."
  }
}

variable "tap_oidc_provider_arn" {
  description = "Existing IAM OIDC provider ARN for the TAP platform issuer. Null (with tap_oidc_issuer_url set) creates one."
  type        = string
  default     = null
}

variable "tap_oidc_issuer_url" {
  description = "TAP platform OIDC issuer URL (https://...). Null disables TAP trust."
  type        = string
  default     = null

  validation {
    condition     = var.tap_oidc_issuer_url == null || can(regex("^https://", coalesce(var.tap_oidc_issuer_url, "https://unset")))
    error_message = "tap_oidc_issuer_url must start with https://."
  }
}

variable "tap_oidc_audience" {
  description = "Expected aud claim on TAP runner tokens."
  type        = string
  default     = "tap-runner"
}

variable "tap_oidc_thumbprints" {
  description = "TLS thumbprints for the TAP issuer (only used when creating the provider)."
  type        = list(string)
  default     = []
}

variable "tap_subjects" {
  description = "Allowed TAP sub claims, e.g. [\"workspace:acme/prod/network\"]."
  type        = list(string)
  default     = []
}

variable "policy_arns" {
  description = "Managed policy ARNs to attach (keep least-privilege; prefer inline scoped policies)."
  type        = list(string)
  default     = []
}

variable "inline_policies" {
  description = "Map of inline policy name => JSON policy document."
  type        = map(string)
  default     = {}
}

variable "permissions_boundary_arn" {
  description = "Permission boundary policy ARN applied to the role (strongly recommended for runner roles)."
  type        = string
  default     = null
}

variable "max_session_duration" {
  description = "Maximum session duration in seconds (runner tokens should stay short-lived)."
  type        = number
  default     = 3600

  validation {
    condition     = var.max_session_duration >= 900 && var.max_session_duration <= 43200
    error_message = "max_session_duration must be between 900 and 43200 seconds."
  }
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default     = {}
}
