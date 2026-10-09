variable "name" {
  description = "Base name for Vertex AI resources (lowercase, hyphens)."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,40}$", var.name))
    error_message = "name must be lowercase alphanumeric/hyphen characters starting with a letter."
  }
}

variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "Vertex AI region (e.g. europe-west1)."
  type        = string
}

variable "endpoint_display_name" {
  description = "Display name for the online prediction endpoint. Null defaults to name."
  type        = string
  default     = null
}

variable "endpoint_network" {
  description = "Optional VPC network for private endpoint access (projects/<num>/global/networks/<name>). Requires a Service Networking peering."
  type        = string
  default     = null
}

variable "cmek_key_name" {
  description = "Optional CMEK key for endpoint and index (projects/.../cryptoKeys/...). The Vertex AI service agent needs encrypter/decrypter on it."
  type        = string
  default     = null
}

variable "vector_index" {
  description = "Vector Search index skeleton config. Null skips index + index endpoint."
  type = object({
    dimensions                   = number
    approximate_neighbors_count  = optional(number, 150)
    distance_measure_type        = optional(string, "DOT_PRODUCT_DISTANCE")
    shard_size                   = optional(string, "SHARD_SIZE_SMALL")
    index_update_method          = optional(string, "STREAM_UPDATE") # STREAM_UPDATE | BATCH_UPDATE
    contents_delta_uri           = optional(string)                  # gs:// bucket path for batch updates
    leaf_node_embedding_count    = optional(number, 1000)
    leaf_nodes_to_search_percent = optional(number, 10)
  })
  default = null

  validation {
    condition = var.vector_index == null || contains(
      ["STREAM_UPDATE", "BATCH_UPDATE"],
      try(var.vector_index.index_update_method, "STREAM_UPDATE")
    )
    error_message = "index_update_method must be STREAM_UPDATE or BATCH_UPDATE."
  }
}

variable "service_agent_kms_grant" {
  description = "Grant the Vertex AI (aiplatform) service agent encrypter/decrypter on cmek_key_name."
  type        = bool
  default     = true
}

variable "service_agent_bucket_grants" {
  description = "GCS bucket names the Vertex AI service agent gets objectViewer on (training data, index sources)."
  type        = list(string)
  default     = []
}

variable "labels" {
  description = "Labels applied to all resources."
  type        = map(string)
  default     = {}
}
