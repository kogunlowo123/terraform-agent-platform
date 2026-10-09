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
  default     = "internal"
}

variable "vpc_cidr" {
  description = "VPC CIDR."
  type        = string
  default     = "10.40.0.0/16"
}

variable "azs" {
  description = "Availability zones."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "nat_gateway_mode" {
  description = "single | per_az | none."
  type        = string
  default     = "single"
}
