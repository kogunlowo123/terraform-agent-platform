output "instance_name" {
  description = "Cloud SQL instance name."
  value       = google_sql_database_instance.this.name
}

output "connection_name" {
  description = "Connection name for the Cloud SQL Auth Proxy / connectors."
  value       = google_sql_database_instance.this.connection_name
}

output "private_ip_address" {
  description = "Private IP of the instance."
  value       = google_sql_database_instance.this.private_ip_address
}

output "database_name" {
  description = "Initial database name."
  value       = google_sql_database.this.name
}

output "username" {
  description = "Initial SQL user."
  value       = google_sql_user.this.name
}

output "password" {
  description = "Generated password for the initial user. Store it in Secret Manager; do not echo it."
  value       = random_password.user.result
  sensitive   = true
}

output "server_ca_cert" {
  description = "Server CA certificate for verified TLS connections."
  value       = google_sql_database_instance.this.server_ca_cert[0].cert
  sensitive   = true
}
