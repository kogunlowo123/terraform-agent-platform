output "vector_backend" {
  description = "Selected vector backend (qdrant | pinecone)."
  value       = var.vector_backend
}

output "vector_endpoint" {
  description = "Endpoint of the vector backend: in-cluster DNS for Qdrant, host URL for Pinecone."
  value = var.vector_backend == "qdrant" ? (
    try("http://${module.qdrant[0].service_host}:${module.qdrant[0].http_port}", null)
  ) : try(module.pinecone[0].index_host, null)
}

output "document_bucket_name" {
  description = "Name of the RAG document bucket."
  value       = aws_s3_bucket.documents.bucket
}

output "document_bucket_arn" {
  description = "ARN of the RAG document bucket."
  value       = aws_s3_bucket.documents.arn
}

output "ingest_queue_url" {
  description = "URL of the ingestion queue."
  value       = aws_sqs_queue.ingest.url
}

output "ingest_queue_arn" {
  description = "ARN of the ingestion queue."
  value       = aws_sqs_queue.ingest.arn
}

output "dlq_arn" {
  description = "ARN of the ingestion dead-letter queue."
  value       = aws_sqs_queue.dlq.arn
}

output "kms_key_arn" {
  description = "KMS key encrypting the bucket and queues."
  value       = local.kms_key_arn
}
