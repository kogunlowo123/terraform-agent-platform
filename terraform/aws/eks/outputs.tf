output "cluster_name" {
  description = "EKS cluster name."
  value       = aws_eks_cluster.this.name
}

output "cluster_arn" {
  description = "EKS cluster ARN."
  value       = aws_eks_cluster.this.arn
}

output "cluster_endpoint" {
  description = "Kubernetes API server endpoint."
  value       = aws_eks_cluster.this.endpoint
}

output "cluster_certificate_authority_data" {
  description = "Base64 CA bundle for the cluster."
  value       = aws_eks_cluster.this.certificate_authority[0].data
}

output "cluster_version" {
  description = "Running Kubernetes version."
  value       = aws_eks_cluster.this.version
}

output "cluster_security_group_id" {
  description = "EKS-managed cluster security group ID."
  value       = aws_eks_cluster.this.vpc_config[0].cluster_security_group_id
}

output "oidc_issuer_url" {
  description = "OIDC issuer URL of the cluster."
  value       = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

output "oidc_provider_arn" {
  description = "ARN of the IAM OIDC provider for IRSA (null when enable_irsa = false)."
  value       = var.enable_irsa ? aws_iam_openid_connect_provider.this[0].arn : null
}

output "node_role_arn" {
  description = "IAM role ARN shared by managed node groups."
  value       = aws_iam_role.node.arn
}

output "node_group_arns" {
  description = "Map of node group name => ARN."
  value       = { for k, ng in aws_eks_node_group.this : k => ng.arn }
}

output "kms_key_arn" {
  description = "KMS key ARN used for secrets envelope encryption."
  value       = local.kms_key_arn
}

output "ebs_csi_irsa_role_arn" {
  description = "IRSA role ARN wired into the aws-ebs-csi-driver addon (null when not created)."
  value       = local.create_ebs_csi_irsa ? aws_iam_role.ebs_csi[0].arn : null
}
