output "cluster_id" {
  description = "Fully qualified cluster ID."
  value       = google_container_cluster.this.id
}

output "cluster_name" {
  description = "Cluster name."
  value       = google_container_cluster.this.name
}

output "endpoint" {
  description = "Control plane endpoint IP."
  value       = google_container_cluster.this.endpoint
  sensitive   = true
}

output "ca_certificate" {
  description = "Base64 cluster CA certificate."
  value       = google_container_cluster.this.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "workload_identity_pool" {
  description = "Workload identity pool (<project>.svc.id.goog)."
  value       = "${var.project_id}.svc.id.goog"
}

output "node_service_account_email" {
  description = "Service account used by node pools."
  value       = local.node_sa_email
}

output "node_pool_names" {
  description = "Names of managed node pools."
  value       = [for p in google_container_node_pool.this : p.name]
}
