output "agent_id" {
  description = "Bedrock agent ID."
  value       = aws_bedrockagent_agent.this.agent_id
}

output "agent_arn" {
  description = "Bedrock agent ARN."
  value       = aws_bedrockagent_agent.this.agent_arn
}

output "knowledge_base_id" {
  description = "Knowledge base ID."
  value       = aws_bedrockagent_knowledge_base.this.id
}

output "knowledge_base_arn" {
  description = "Knowledge base ARN."
  value       = aws_bedrockagent_knowledge_base.this.arn
}

output "collection_arn" {
  description = "OpenSearch Serverless vector collection ARN."
  value       = aws_opensearchserverless_collection.this.arn
}

output "collection_endpoint" {
  description = "OpenSearch Serverless collection endpoint (create the vector index here before KB sync)."
  value       = aws_opensearchserverless_collection.this.collection_endpoint
}

output "guardrail_id" {
  description = "Guardrail ID."
  value       = aws_bedrock_guardrail.this.guardrail_id
}

output "guardrail_version" {
  description = "Pinned guardrail version."
  value       = aws_bedrock_guardrail_version.this.version
}

output "provisioned_throughput_arn" {
  description = "Provisioned throughput ARN (null when disabled)."
  value       = var.provisioned_throughput.enabled ? aws_bedrock_provisioned_model_throughput.this[0].provisioned_model_arn : null
}

output "invocation_log_group" {
  description = "CloudWatch log group receiving model invocation logs (null when disabled)."
  value       = var.enable_invocation_logging ? aws_cloudwatch_log_group.invocation[0].name : null
}

output "kb_role_arn" {
  description = "IAM role the knowledge base uses (grant it s3 read on your source bucket for ingestion)."
  value       = aws_iam_role.kb.arn
}
