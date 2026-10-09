output "prefix" {
  description = "Deterministic resource name prefix: <org><delim><env_short><delim><region_short>[<delim><name>]."
  value       = local.prefix
}

output "tags_base" {
  description = "Base tag map (organization, environment, region, managed_by=tap) merged with additional_tags."
  value       = local.tags_base
}

output "env_short" {
  description = "Short code derived from the environment (e.g. prd, stg, dev)."
  value       = local.env_short
}

output "region_short" {
  description = "Short code derived from the cloud region (e.g. use1, weu, usc1)."
  value       = local.region_short
}

output "delimiter" {
  description = "Delimiter used between prefix segments."
  value       = var.delimiter
}
