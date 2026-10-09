variable "owner" {
  description = "Team or individual accountable for the resources (e.g. \"platform-engineering\")."
  type        = string

  validation {
    condition     = length(trimspace(var.owner)) > 0
    error_message = "owner must not be empty."
  }
}

variable "cost_center" {
  description = "Cost center or billing code the resources are charged to."
  type        = string

  validation {
    condition     = length(trimspace(var.cost_center)) > 0
    error_message = "cost_center must not be empty."
  }
}

variable "environment" {
  description = "Deployment environment the resources belong to."
  type        = string

  validation {
    condition = contains(
      ["dev", "development", "test", "staging", "stage", "prod", "production", "sandbox"],
      lower(var.environment)
    )
    error_message = "environment must be one of: dev, development, test, staging, stage, prod, production, sandbox."
  }
}

variable "data_class" {
  description = "Data classification of workloads on these resources."
  type        = string

  validation {
    condition     = contains(["public", "internal", "confidential", "restricted"], lower(var.data_class))
    error_message = "data_class must be one of: public, internal, confidential, restricted."
  }
}

variable "extra_tags" {
  description = "Additional tags merged in. Required-tag keys always win over extra_tags."
  type        = map(string)
  default     = {}

  validation {
    condition = length(setintersection(
      keys(var.extra_tags),
      ["owner", "cost_center", "data_class"]
    )) == 0
    error_message = "extra_tags must not redefine owner, cost_center, or data_class. (environment/managed_by are tolerated — the enforced values win in the merge.)"
  }
}
