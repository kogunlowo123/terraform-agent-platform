output "release_name" {
  description = "Helm release name."
  value       = helm_release.qdrant.name
}

output "namespace" {
  description = "Namespace Qdrant runs in."
  value       = helm_release.qdrant.namespace
}

output "service_host" {
  description = "In-cluster service DNS name for the Qdrant HTTP/gRPC API."
  value       = "${helm_release.qdrant.name}.${helm_release.qdrant.namespace}.svc.cluster.local"
}

output "http_port" {
  description = "Qdrant HTTP API port."
  value       = 6333
}

output "grpc_port" {
  description = "Qdrant gRPC API port."
  value       = 6334
}
