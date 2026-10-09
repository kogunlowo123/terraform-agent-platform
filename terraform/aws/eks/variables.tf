variable "name" {
  description = "EKS cluster name (typically module.naming.prefix)."
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9-_]{0,99}$", var.name))
    error_message = "name must be 1-100 alphanumeric/hyphen/underscore characters starting with a letter."
  }
}

variable "kubernetes_version" {
  description = "Kubernetes minor version for the control plane (e.g. \"1.30\")."
  type        = string
  default     = "1.30"

  validation {
    condition     = can(regex("^1\\.(2[7-9]|3[0-9])$", var.kubernetes_version))
    error_message = "kubernetes_version must look like 1.27–1.39."
  }
}

variable "subnet_ids" {
  description = "Private subnet IDs for the control plane ENIs and node groups (>= 2 AZs)."
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "Provide at least two subnet IDs across different AZs."
  }
}

variable "endpoint_public_access" {
  description = "Expose the API server publicly. Default false: private endpoint only."
  type        = bool
  default     = false
}

variable "endpoint_public_access_cidrs" {
  description = "CIDRs allowed to reach the public endpoint when endpoint_public_access = true."
  type        = list(string)
  default     = []
}

variable "kms_key_arn" {
  description = "KMS key ARN for Kubernetes secrets envelope encryption. Null creates a dedicated rotated key."
  type        = string
  default     = null
}

variable "enabled_log_types" {
  description = "Control plane log types shipped to CloudWatch."
  type        = list(string)
  default     = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
}

variable "enable_irsa" {
  description = "Create the IAM OIDC provider for IAM Roles for Service Accounts."
  type        = bool
  default     = true
}

variable "node_groups" {
  description = "Managed node groups keyed by name."
  type = map(object({
    instance_types = optional(list(string), ["m6i.large"])
    min_size       = optional(number, 2)
    max_size       = optional(number, 6)
    desired_size   = optional(number, 2)
    capacity_type  = optional(string, "ON_DEMAND") # ON_DEMAND | SPOT
    disk_size_gb   = optional(number, 50)
    labels         = optional(map(string), {})
    taints = optional(list(object({
      key    = string
      value  = optional(string)
      effect = string # NO_SCHEDULE | PREFER_NO_SCHEDULE | NO_EXECUTE
    })), [])
  }))
  default = {
    default = {}
  }

  validation {
    condition     = alltrue([for ng in values(var.node_groups) : contains(["ON_DEMAND", "SPOT"], ng.capacity_type)])
    error_message = "capacity_type must be ON_DEMAND or SPOT."
  }
}

variable "access_entries" {
  description = "EKS access entries (authentication_mode API) keyed by a friendly name."
  type = map(object({
    principal_arn = string
    policy_arn    = optional(string, "arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy")
    access_scope  = optional(string, "cluster") # cluster | namespace
    namespaces    = optional(list(string), [])
  }))
  default = {}

  validation {
    condition     = alltrue([for e in values(var.access_entries) : contains(["cluster", "namespace"], e.access_scope)])
    error_message = "access_scope must be cluster or namespace."
  }
}

variable "addons" {
  description = "EKS managed addons keyed by addon name; null version = latest default for the cluster version."
  type = map(object({
    version = optional(string)
  }))
  default = {
    vpc-cni            = {}
    coredns            = {}
    kube-proxy         = {}
    aws-ebs-csi-driver = {}
  }
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default     = {}
}
