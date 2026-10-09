output "cluster_name" {
  description = "EKS cluster name."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Kubernetes API endpoint (private)."
  value       = module.eks.cluster_endpoint
}

output "oidc_provider_arn" {
  description = "IRSA OIDC provider ARN."
  value       = module.eks.oidc_provider_arn
}

output "runner_role_arn" {
  description = "Federated role TAP runners assume."
  value       = module.runner_role.role_arn
}

output "private_subnet_ids" {
  description = "Private subnets hosting the cluster."
  value       = module.vpc.private_subnet_ids
}
