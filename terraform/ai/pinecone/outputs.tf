output "index_name" {
  description = "Pinecone index name."
  value       = pinecone_index.this.name
}

output "index_host" {
  description = "Index host URL used by clients."
  value       = pinecone_index.this.host
}

output "dimension" {
  description = "Vector dimension of the index."
  value       = pinecone_index.this.dimension
}

output "metric" {
  description = "Similarity metric of the index."
  value       = pinecone_index.this.metric
}
