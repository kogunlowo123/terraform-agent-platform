variable "name" {
  description = "GKE cluster name."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,38}[a-z0-9]$", var.name))
    error_message = "name must be 2-40 lowercase alphanumeric/hyphen characters starting with a letter."
  }
}

variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "location" {
  description = "Region (regional cluster) or zone (zonal). Prefer a region for HA."
  type        = string
}

variable "network" {
  description = "VPC self link or name."
  type        = string
}

variable "subnetwork" {
  description = "Subnetwork self link or name."
  type        = string
}

variable "pods_secondary_range_name" {
  description = "Secondary range on the subnetwork for pod IPs (VPC-native)."
  type        = string
}

variable "services_secondary_range_name" {
  description = "Secondary range on the subnetwork for service IPs (VPC-native)."
  type        = string
}

variable "release_channel" {
  description = "GKE release channel."
  type        = string
  default     = "REGULAR"

  validation {
    condition     = contains(["RAPID", "REGULAR", "STABLE"], var.release_channel)
    error_message = "release_channel must be RAPID, REGULAR, or STABLE."
  }
}

variable "enable_private_endpoint" {
  description = "Make the control plane endpoint private-only (no public master address)."
  type        = bool
  default     = false
}

variable "master_ipv4_cidr_block" {
  description = "/28 CIDR for the private control plane."
  type        = string
  default     = "172.16.0.0/28"

  validation {
    condition     = can(regex("/28$", var.master_ipv4_cidr_block))
    error_message = "master_ipv4_cidr_block must be a /28."
  }
}

variable "master_authorized_networks" {
  description = "CIDRs allowed to reach the control plane, keyed by display name."
  type        = map(string)
  default     = {}
}

variable "node_service_account" {
  description = "Service account email for nodes. Null creates a minimal dedicated SA."
  type        = string
  default     = null
}

variable "node_pools" {
  description = "Node pools keyed by name."
  type = map(object({
    machine_type = optional(string, "e2-standard-4")
    min_count    = optional(number, 1)
    max_count    = optional(number, 5)
    disk_size_gb = optional(number, 100)
    disk_type    = optional(string, "pd-balanced")
    spot         = optional(bool, false)
    labels       = optional(map(string), {})
    taints = optional(list(object({
      key    = string
      value  = string
      effect = string # NO_SCHEDULE | PREFER_NO_SCHEDULE | NO_EXECUTE
    })), [])
  }))
  default = {
    default = {}
  }
}

variable "enable_node_auto_provisioning" {
  description = "Enable node auto-provisioning (NAP) with the resource limits below."
  type        = bool
  default     = false
}

variable "nap_resource_limits" {
  description = "NAP resource ceilings (only used when enable_node_auto_provisioning = true)."
  type = object({
    max_cpu    = optional(number, 64)
    max_memory = optional(number, 256)
  })
  default = {}
}

variable "deletion_protection" {
  description = "Prevent Terraform from destroying the cluster."
  type        = bool
  default     = true
}

variable "labels" {
  description = "Resource labels applied to the cluster (GCP labels must be lowercase)."
  type        = map(string)
  default     = {}
}
