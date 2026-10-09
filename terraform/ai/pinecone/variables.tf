variable "index_name" {
  description = "Pinecone index name."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]([a-z0-9-]{0,43}[a-z0-9])?$", var.index_name))
    error_message = "index_name must be 1-45 lowercase alphanumeric/hyphen characters."
  }
}

variable "dimension" {
  description = "Vector dimension (must match the embedding model, e.g. 1536, 768, 3072)."
  type        = number

  validation {
    condition     = var.dimension >= 1 && var.dimension <= 20000
    error_message = "dimension must be between 1 and 20000."
  }
}

variable "metric" {
  description = "Similarity metric."
  type        = string
  default     = "cosine"

  validation {
    condition     = contains(["cosine", "euclidean", "dotproduct"], var.metric)
    error_message = "metric must be cosine, euclidean, or dotproduct."
  }
}

variable "cloud" {
  description = "Cloud for the serverless spec."
  type        = string
  default     = "aws"

  validation {
    condition     = contains(["aws", "gcp", "azure"], var.cloud)
    error_message = "cloud must be aws, gcp, or azure."
  }
}

variable "region" {
  description = "Region for the serverless spec (e.g. us-east-1, us-central1, eastus2)."
  type        = string
  default     = "us-east-1"
}

variable "deletion_protection" {
  description = "Enable Pinecone deletion protection on the index."
  type        = bool
  default     = true
}
