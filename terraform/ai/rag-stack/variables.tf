variable "name" {
  description = "Base name for RAG stack resources (bucket/queue prefixes, index/release names)."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,36}$", var.name))
    error_message = "name must be 3-37 lowercase alphanumeric/hyphen characters starting with a letter."
  }
}

variable "vector_backend" {
  description = "Vector database backend for the stack."
  type        = string

  validation {
    condition     = contains(["qdrant", "pinecone"], var.vector_backend)
    error_message = "vector_backend must be \"qdrant\" or \"pinecone\"."
  }
}

variable "qdrant" {
  description = "Qdrant settings (used when vector_backend = qdrant)."
  type = object({
    namespace        = optional(string, "vector")
    replicas         = optional(number, 3)
    chart_version    = optional(string, "1.13.1")
    persistence_size = optional(string, "50Gi")
    storage_class    = optional(string)
    api_key          = optional(string) # required when backend = qdrant
  })
  default   = {}
  sensitive = true
}

variable "pinecone" {
  description = "Pinecone settings (used when vector_backend = pinecone)."
  type = object({
    dimension = optional(number, 1536)
    metric    = optional(string, "cosine")
    cloud     = optional(string, "aws")
    region    = optional(string, "us-east-1")
  })
  default = {}
}

variable "kms_key_arn" {
  description = "KMS key for the document bucket and ingestion queue. Null creates a dedicated rotated key."
  type        = string
  default     = null
}

variable "bucket_force_destroy" {
  description = "Allow destroying the document bucket with objects inside. Keep false in production."
  type        = bool
  default     = false
}

variable "document_retention_days" {
  description = "Expire noncurrent object versions after this many days."
  type        = number
  default     = 90
}

variable "queue_visibility_timeout" {
  description = "Ingestion queue visibility timeout in seconds (>= ingestion job max runtime)."
  type        = number
  default     = 300
}

variable "queue_max_receive_count" {
  description = "Deliveries before a message is moved to the DLQ."
  type        = number
  default     = 5
}

variable "tags" {
  description = "Tags applied to all AWS resources."
  type        = map(string)
  default     = {}
}
