output "account_id" {
  description = "Cognitive account resource ID."
  value       = azurerm_cognitive_account.this.id
}

output "account_name" {
  description = "Cognitive account name."
  value       = azurerm_cognitive_account.this.name
}

output "endpoint" {
  description = "Azure OpenAI endpoint URL (https://<subdomain>.openai.azure.com/)."
  value       = azurerm_cognitive_account.this.endpoint
}

output "custom_subdomain_name" {
  description = "Custom subdomain in use."
  value       = azurerm_cognitive_account.this.custom_subdomain_name
}

output "identity_principal_id" {
  description = "Principal ID of the system-assigned identity (null when using a user-assigned identity for CMK)."
  value       = var.customer_managed_key == null ? azurerm_cognitive_account.this.identity[0].principal_id : null
}

output "deployment_names" {
  description = "Map of deployment key => deployment name."
  value       = { for k, d in azurerm_cognitive_deployment.this : k => d.name }
}

output "private_endpoint_ip" {
  description = "Private IP of the account endpoint (null when not created)."
  value       = var.private_endpoint != null ? azurerm_private_endpoint.this[0].private_service_connection[0].private_ip_address : null
}
