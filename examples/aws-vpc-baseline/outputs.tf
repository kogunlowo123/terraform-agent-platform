output "vpc_id" {
  description = "ID of the baseline VPC."
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnets for workloads."
  value       = module.vpc.private_subnet_ids
}

output "intra_subnet_ids" {
  description = "Intra subnets for data stores."
  value       = module.vpc.intra_subnet_ids
}

output "name_prefix" {
  description = "Naming prefix used across the workspace."
  value       = module.naming.prefix
}
