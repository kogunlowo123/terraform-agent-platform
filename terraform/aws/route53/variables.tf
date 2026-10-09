variable "zone_name" {
  description = "DNS zone name (e.g. \"prod.tap.example.com\")."
  type        = string

  validation {
    condition     = can(regex("^([a-z0-9]([a-z0-9-]*[a-z0-9])?\\.)+[a-z]{2,}$", var.zone_name))
    error_message = "zone_name must be a valid lowercase DNS name."
  }
}

variable "private_zone" {
  description = "Create a private hosted zone associated with vpc_ids."
  type        = bool
  default     = false
}

variable "vpc_ids" {
  description = "VPC IDs to associate (required when private_zone = true)."
  type        = list(string)
  default     = []
}

variable "comment" {
  description = "Zone comment."
  type        = string
  default     = "Managed by TAP"
}

variable "force_destroy" {
  description = "Allow destroying the zone even when records remain. Keep false in production."
  type        = bool
  default     = false
}

variable "records" {
  description = <<-EOT
    DNS records keyed by "<name> <type>" (key is only a map key; name/type come
    from the object). Exactly one of `records` or `alias` must be set per entry.
  EOT
  type = map(object({
    name    = string
    type    = string
    ttl     = optional(number, 300)
    records = optional(list(string))
    alias = optional(object({
      name                   = string
      zone_id                = string
      evaluate_target_health = optional(bool, false)
    }))
  }))
  default = {}

  validation {
    condition = alltrue([
      for r in values(var.records) :
      contains(["A", "AAAA", "CNAME", "TXT", "MX", "NS", "SRV", "CAA", "PTR"], r.type)
    ])
    error_message = "record type must be one of A, AAAA, CNAME, TXT, MX, NS, SRV, CAA, PTR."
  }

  validation {
    condition = alltrue([
      for r in values(var.records) :
      (r.records != null && r.alias == null) || (r.records == null && r.alias != null)
    ])
    error_message = "Each record must set exactly one of `records` or `alias`."
  }
}

variable "tags" {
  description = "Tags applied to the zone."
  type        = map(string)
  default     = {}
}
