variable "org" {
  description = "Short organization code."
  type        = string
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"
}

variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
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

variable "vpc_cidr" {
  description = "VPC CIDR."
  type        = string
  default     = "10.42.0.0/16"
}

variable "azs" {
  description = "Availability zones."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "kubernetes_version" {
  description = "EKS control plane version."
  type        = string
  default     = "1.30"
}

variable "cluster_admin_role_arn" {
  description = "IAM role granted cluster-admin via an access entry. Null skips it."
  type        = string
  default     = null
}

variable "github_org" {
  description = "GitHub org trusted for runner OIDC. Null disables GitHub trust."
  type        = string
  default     = null
}

variable "tap_oidc_issuer_url" {
  description = "TAP platform OIDC issuer URL. Null disables TAP trust."
  type        = string
  default     = null
}

variable "tap_oidc_thumbprints" {
  description = "Thumbprints for the TAP issuer."
  type        = list(string)
  default     = []
}

variable "runner_permissions_boundary_arn" {
  description = "Permission boundary for the runner role."
  type        = string
  default     = null
}
