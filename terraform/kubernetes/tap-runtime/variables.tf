variable "namespace" {
  description = "Namespace for the TAP runner runtime."
  type        = string
  default     = "tap-runtime"

  validation {
    condition     = can(regex("^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$", var.namespace))
    error_message = "namespace must be a valid DNS-1123 label."
  }
}

variable "service_account_name" {
  description = "ServiceAccount used by TAP runner pods (token auto-mount disabled)."
  type        = string
  default     = "tap-runner"
}

variable "pod_security_level" {
  description = "Pod Security Standards enforcement level for the namespace."
  type        = string
  default     = "restricted"

  validation {
    condition     = contains(["privileged", "baseline", "restricted"], var.pod_security_level)
    error_message = "pod_security_level must be privileged, baseline, or restricted."
  }
}

variable "resource_quota" {
  description = "Namespace ResourceQuota hard limits."
  type = object({
    requests_cpu    = optional(string, "8")
    requests_memory = optional(string, "16Gi")
    limits_cpu      = optional(string, "16")
    limits_memory   = optional(string, "32Gi")
    pods            = optional(string, "50")
  })
  default = {}
}

variable "container_limits" {
  description = "LimitRange defaults applied to containers without explicit resources."
  type = object({
    default_cpu            = optional(string, "500m")
    default_memory         = optional(string, "512Mi")
    default_request_cpu    = optional(string, "100m")
    default_request_memory = optional(string, "128Mi")
    max_cpu                = optional(string, "4")
    max_memory             = optional(string, "8Gi")
  })
  default = {}
}

variable "egress_cidrs" {
  description = "CIDRs runner pods may reach on 443 (cloud provider APIs). Default: anywhere except RFC1918 + link-local."
  type = list(object({
    cidr   = string
    except = optional(list(string), [])
  }))
  default = [{
    cidr   = "0.0.0.0/0"
    except = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.169.254/32"]
  }]
}

variable "opa_endpoints" {
  description = "In-cluster OPA policy service endpoints runners may reach: namespace label selector + port."
  type = object({
    namespace_labels = optional(map(string), { "kubernetes.io/metadata.name" = "tap-system" })
    port             = optional(number, 8181)
  })
  default = {}
}

variable "labels" {
  description = "Extra labels applied to every object."
  type        = map(string)
  default     = {}
}
