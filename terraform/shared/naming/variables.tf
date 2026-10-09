variable "org" {
  description = "Short organization code used as the first segment of every resource name (e.g. \"acme\")."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9]{1,11}$", var.org))
    error_message = "org must be 2-12 lowercase alphanumeric characters and start with a letter."
  }
}

variable "environment" {
  description = "Deployment environment. Mapped to a short code (dev/stg/prd/sbx/tst) in the prefix."
  type        = string

  validation {
    condition = contains(
      ["dev", "development", "test", "staging", "stage", "prod", "production", "sandbox"],
      lower(var.environment)
    )
    error_message = "environment must be one of: dev, development, test, staging, stage, prod, production, sandbox."
  }
}

variable "region" {
  description = "Cloud region (AWS, Azure, or GCP) used to derive the region short code."
  type        = string

  validation {
    condition     = length(var.region) > 0
    error_message = "region must not be empty."
  }
}

variable "name" {
  description = "Optional workload or component name appended as the last segment of the prefix."
  type        = string
  default     = ""

  validation {
    condition     = var.name == "" || can(regex("^[a-z][a-z0-9-]{0,23}$", var.name))
    error_message = "name must be 1-24 lowercase alphanumeric/hyphen characters starting with a letter, or empty."
  }
}

variable "delimiter" {
  description = "Delimiter between name segments. Use \"\" for services that forbid separators (e.g. S3-compatible, storage accounts)."
  type        = string
  default     = "-"

  validation {
    condition     = contains(["-", "_", ""], var.delimiter)
    error_message = "delimiter must be \"-\", \"_\", or \"\"."
  }
}

variable "additional_tags" {
  description = "Extra tags merged into tags_base (caller values win over nothing; base keys are not overridable)."
  type        = map(string)
  default     = {}
}
