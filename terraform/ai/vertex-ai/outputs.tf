output "endpoint_id" {
  description = "Prediction endpoint resource ID."
  value       = google_vertex_ai_endpoint.this.id
}

output "endpoint_name" {
  description = "Fully qualified endpoint name (deploy models to this via the Vertex API)."
  value       = google_vertex_ai_endpoint.this.name
}

output "index_id" {
  description = "Vector Search index ID (null when vector_index is null)."
  value       = var.vector_index != null ? google_vertex_ai_index.this[0].id : null
}

output "index_endpoint_id" {
  description = "Vector Search index endpoint ID (null when vector_index is null)."
  value       = var.vector_index != null ? google_vertex_ai_index_endpoint.this[0].id : null
}

output "index_endpoint_public_domain" {
  description = "Public match domain of the index endpoint (null when private or not created)."
  value       = var.vector_index != null ? google_vertex_ai_index_endpoint.this[0].public_endpoint_domain_name : null
}

output "service_agent_email" {
  description = "Vertex AI service agent email (grant it access to data sources)."
  value       = google_project_service_identity.aiplatform.email
}
