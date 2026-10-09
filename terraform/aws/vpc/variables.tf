variable "name" {
  description = "Name prefix for all VPC resources (typically module.naming.prefix)."
  type        = string

  validation {
    condition     = length(var.name) > 0
    error_message = "name must not be empty."
  }
}

variable "vpc_cidr" {
  description = "IPv4 CIDR block of the VPC. Must leave room for 3 subnet tiers across all AZs at subnet_newbits."
  type        = string

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block."
  }
}

variable "azs" {
  description = "Availability zones to spread subnets across (e.g. [\"us-east-1a\", \"us-east-1b\", \"us-east-1c\"])."
  type        = list(string)

  validation {
    condition     = length(var.azs) >= 2 && length(var.azs) <= 4
    error_message = "Provide between 2 and 4 availability zones for multi-AZ resilience."
  }
}

variable "subnet_newbits" {
  description = "Additional bits for cidrsubnet when carving subnets out of vpc_cidr (4 => /20s from a /16)."
  type        = number
  default     = 4

  validation {
    condition     = var.subnet_newbits >= 2 && var.subnet_newbits <= 12
    error_message = "subnet_newbits must be between 2 and 12."
  }
}

variable "nat_gateway_mode" {
  description = "NAT gateway topology: \"single\" (one shared, cost-optimized), \"per_az\" (HA), or \"none\"."
  type        = string
  default     = "single"

  validation {
    condition     = contains(["single", "per_az", "none"], var.nat_gateway_mode)
    error_message = "nat_gateway_mode must be one of: single, per_az, none."
  }
}

variable "enable_gateway_endpoints" {
  description = "Create S3 and DynamoDB gateway VPC endpoints attached to private and intra route tables."
  type        = bool
  default     = true
}

variable "flow_logs_enabled" {
  description = "Enable VPC flow logs to CloudWatch Logs."
  type        = bool
  default     = true
}

variable "flow_logs_retention_days" {
  description = "CloudWatch retention (days) for VPC flow logs."
  type        = number
  default     = 90

  validation {
    condition = contains(
      [1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653],
      var.flow_logs_retention_days
    )
    error_message = "flow_logs_retention_days must be a valid CloudWatch Logs retention value."
  }
}

variable "flow_logs_kms_key_arn" {
  description = "Optional KMS key ARN to encrypt the flow log group. Null uses the CloudWatch default encryption."
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags applied to every resource (merge of shared/naming tags_base and shared/tags tags)."
  type        = map(string)
  default     = {}
}
