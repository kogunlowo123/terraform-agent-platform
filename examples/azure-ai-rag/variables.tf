variable "org" {
  description = "Short organization code."
  type        = string
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"
}

variable "azure_location" {
  description = "Azure region for the landing zone and AI services."
  type        = string
  default     = "swedencentral"
}

variable "aws_region" {
  description = "AWS region for the RAG document bucket + ingestion queue."
  type        = string
  default     = "eu-north-1"
}

variable "owner" {
  description = "Accountable team."
  type        = string
}

variable "cost_center" {
  description = "Billing code."
  type        = string
}

variable "data_class" {
  description = "Data classification."
  type        = string
  default     = "confidential"
}

variable "allowed_locations" {
  description = "Azure policy: allowed regions."
  type        = list(string)
  default     = ["swedencentral", "westeurope"]
}

variable "vault_allowed_ip_rules" {
  description = "Public CIDRs allowed through the Key Vault firewall during bootstrap."
  type        = list(string)
  default     = []
}

variable "kubeconfig_path" {
  description = "Path to the kubeconfig for the cluster hosting Qdrant."
  type        = string
  default     = "~/.kube/config"
}

variable "kubeconfig_context" {
  description = "Kubeconfig context to use. Null uses the current context."
  type        = string
  default     = null
}

variable "qdrant_api_key" {
  description = "API key for Qdrant (inject from the TAP secret store; never commit)."
  type        = string
  sensitive   = true
}
