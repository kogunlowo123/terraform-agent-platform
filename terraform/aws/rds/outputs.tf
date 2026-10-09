output "instance_id" {
  description = "RDS instance identifier."
  value       = aws_db_instance.this.id
}

output "instance_arn" {
  description = "RDS instance ARN."
  value       = aws_db_instance.this.arn
}

output "endpoint" {
  description = "Connection endpoint (host:port)."
  value       = aws_db_instance.this.endpoint
}

output "address" {
  description = "DNS address of the instance."
  value       = aws_db_instance.this.address
}

output "port" {
  description = "Listening port."
  value       = aws_db_instance.this.port
}

output "db_name" {
  description = "Initial database name."
  value       = aws_db_instance.this.db_name
}

output "security_group_id" {
  description = "Security group guarding the instance."
  value       = aws_security_group.this.id
}

output "secret_arn" {
  description = "Secrets Manager secret ARN holding the master credentials."
  value       = aws_secretsmanager_secret.this.arn
}

output "kms_key_arn" {
  description = "KMS key used for storage/PI/secret encryption."
  value       = local.kms_key_arn
}

output "parameter_group_name" {
  description = "Parameter group attached to the instance."
  value       = aws_db_parameter_group.this.name
}
