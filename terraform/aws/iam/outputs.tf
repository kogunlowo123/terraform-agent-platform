output "role_arn" {
  description = "ARN of the federated runner role."
  value       = aws_iam_role.this.arn
}

output "role_name" {
  description = "Name of the federated runner role."
  value       = aws_iam_role.this.name
}

output "github_oidc_provider_arn" {
  description = "ARN of the GitHub OIDC provider in use (null when GitHub trust is disabled)."
  value       = local.github_provider_arn
}

output "tap_oidc_provider_arn" {
  description = "ARN of the TAP platform OIDC provider in use (null when TAP trust is disabled)."
  value       = local.tap_provider_arn
}
