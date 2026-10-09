variable "identifier" {
  description = "DB instance identifier (typically \"<prefix>-pg\")."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,62}$", var.identifier))
    error_message = "identifier must be 1-63 lowercase alphanumeric/hyphen characters starting with a letter."
  }
}

variable "engine_version" {
  description = "PostgreSQL engine version (e.g. \"16.4\"). The parameter group family is derived from the major version."
  type        = string
  default     = "16.4"

  validation {
    condition     = can(regex("^[0-9]{2}(\\.[0-9]+)?$", var.engine_version))
    error_message = "engine_version must look like \"16\" or \"16.4\"."
  }
}

variable "instance_class" {
  description = "DB instance class."
  type        = string
  default     = "db.m6i.large"
}

variable "allocated_storage" {
  description = "Initial storage (GiB)."
  type        = number
  default     = 100

  validation {
    condition     = var.allocated_storage >= 20
    error_message = "allocated_storage must be at least 20 GiB."
  }
}

variable "max_allocated_storage" {
  description = "Storage autoscaling ceiling (GiB). 0 disables autoscaling."
  type        = number
  default     = 500
}

variable "db_name" {
  description = "Initial database name."
  type        = string
  default     = "tap"

  validation {
    condition     = can(regex("^[a-zA-Z_][a-zA-Z0-9_]{0,62}$", var.db_name))
    error_message = "db_name must be a valid PostgreSQL identifier."
  }
}

variable "username" {
  description = "Master username."
  type        = string
  default     = "tap_admin"

  validation {
    condition     = !contains(["postgres", "admin", "root", "rdsadmin"], lower(var.username))
    error_message = "username must not be a reserved/obvious name (postgres, admin, root, rdsadmin)."
  }
}

variable "multi_az" {
  description = "Deploy a synchronous standby in another AZ."
  type        = bool
  default     = true
}

variable "vpc_id" {
  description = "VPC the instance lives in (for the security group)."
  type        = string
}

variable "subnet_ids" {
  description = "Private/intra subnet IDs for the DB subnet group (>= 2 AZs)."
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "Provide at least two subnet IDs across different AZs."
  }
}

variable "allowed_security_group_ids" {
  description = "Security groups allowed to connect on 5432."
  type        = list(string)
  default     = []
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to connect on 5432 (prefer security groups)."
  type        = list(string)
  default     = []
}

variable "kms_key_arn" {
  description = "KMS key for storage, Performance Insights, and the secret. Null creates a dedicated rotated key."
  type        = string
  default     = null
}

variable "parameters" {
  description = "Extra parameter group entries: name => { value, apply_method }."
  type = map(object({
    value        = string
    apply_method = optional(string, "pending-reboot")
  }))
  default = {}
}

variable "backup_retention_period" {
  description = "Automated backup retention in days."
  type        = number
  default     = 14

  validation {
    condition     = var.backup_retention_period >= 7 && var.backup_retention_period <= 35
    error_message = "backup_retention_period must be between 7 and 35 days."
  }
}

variable "monitoring_interval" {
  description = "Enhanced monitoring granularity in seconds (0 disables)."
  type        = number
  default     = 60

  validation {
    condition     = contains([0, 1, 5, 10, 15, 30, 60], var.monitoring_interval)
    error_message = "monitoring_interval must be one of 0, 1, 5, 10, 15, 30, 60."
  }
}

variable "performance_insights_enabled" {
  description = "Enable Performance Insights (KMS-encrypted)."
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "Protect the instance from deletion. Keep true outside sandboxes."
  type        = bool
  default     = true
}

variable "apply_immediately" {
  description = "Apply modifications immediately instead of in the maintenance window."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default     = {}
}
