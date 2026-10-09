variable "release_name" {
  description = "Helm release name."
  type        = string
  default     = "qdrant"
}

variable "namespace" {
  description = "Kubernetes namespace (created if missing)."
  type        = string
  default     = "vector"
}

variable "chart_version" {
  description = "qdrant/qdrant Helm chart version to pin."
  type        = string
  default     = "1.13.1"
}

variable "replicas" {
  description = "Number of Qdrant replicas (use >= 3 for a production cluster)."
  type        = number
  default     = 3

  validation {
    condition     = var.replicas >= 1
    error_message = "replicas must be at least 1."
  }
}

variable "api_key" {
  description = "API key enforced by Qdrant. The chart stores it in a Kubernetes Secret. Required — unauthenticated vector stores are not acceptable."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.api_key) >= 16
    error_message = "api_key must be at least 16 characters."
  }
}

variable "persistence_size" {
  description = "PVC size per replica."
  type        = string
  default     = "50Gi"
}

variable "storage_class" {
  description = "StorageClass for persistence. Null uses the cluster default."
  type        = string
  default     = null
}

variable "resources" {
  description = "Container resource requests/limits."
  type = object({
    requests = optional(object({
      cpu    = optional(string, "500m")
      memory = optional(string, "1Gi")
    }), {})
    limits = optional(object({
      cpu    = optional(string, "2")
      memory = optional(string, "4Gi")
    }), {})
  })
  default = {}
}

variable "extra_values" {
  description = "Additional Helm values merged last (map rendered to YAML)."
  type        = any
  default     = {}
}
