output "openai_endpoint" {
  description = "Azure OpenAI endpoint URL."
  value       = module.azure_openai.endpoint
}

output "openai_deployments" {
  description = "Deployed model names."
  value       = module.azure_openai.deployment_names
}

output "key_vault_uri" {
  description = "Key Vault URI for workload secrets."
  value       = module.key_vault.key_vault_uri
}

output "vector_endpoint" {
  description = "Qdrant endpoint inside the cluster."
  value       = module.rag_stack.vector_endpoint
}

output "document_bucket_name" {
  description = "RAG document bucket."
  value       = module.rag_stack.document_bucket_name
}

output "ingest_queue_url" {
  description = "Ingestion queue URL."
  value       = module.rag_stack.ingest_queue_url
}
