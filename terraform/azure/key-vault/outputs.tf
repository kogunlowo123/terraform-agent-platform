output "key_vault_id" {
  description = "Resource ID of the vault."
  value       = azurerm_key_vault.this.id
}

output "key_vault_name" {
  description = "Name of the vault."
  value       = azurerm_key_vault.this.name
}

output "key_vault_uri" {
  description = "Vault URI (https://<name>.vault.azure.net/)."
  value       = azurerm_key_vault.this.vault_uri
}

output "private_endpoint_id" {
  description = "Private endpoint resource ID (null when not created)."
  value       = var.private_endpoint != null ? azurerm_private_endpoint.this[0].id : null
}

output "private_endpoint_ip" {
  description = "Private IP of the vault endpoint (null when not created)."
  value       = var.private_endpoint != null ? azurerm_private_endpoint.this[0].private_service_connection[0].private_ip_address : null
}
