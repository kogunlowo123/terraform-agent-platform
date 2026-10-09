output "cluster_id" {
  description = "AKS cluster resource ID."
  value       = azurerm_kubernetes_cluster.this.id
}

output "cluster_name" {
  description = "AKS cluster name."
  value       = azurerm_kubernetes_cluster.this.name
}

output "oidc_issuer_url" {
  description = "OIDC issuer URL for workload identity federation."
  value       = azurerm_kubernetes_cluster.this.oidc_issuer_url
}

output "kubelet_identity_object_id" {
  description = "Object ID of the kubelet managed identity (grant it ACR pull, etc.)."
  value       = azurerm_kubernetes_cluster.this.kubelet_identity[0].object_id
}

output "cluster_identity_principal_id" {
  description = "Principal ID of the cluster's system-assigned identity."
  value       = azurerm_kubernetes_cluster.this.identity[0].principal_id
}

output "key_vault_secrets_provider_identity_client_id" {
  description = "Client ID of the Key Vault secrets provider identity (for SecretProviderClass)."
  value       = azurerm_kubernetes_cluster.this.key_vault_secrets_provider[0].secret_identity[0].client_id
}

output "node_resource_group" {
  description = "Auto-created resource group holding node resources."
  value       = azurerm_kubernetes_cluster.this.node_resource_group
}

output "private_fqdn" {
  description = "Private FQDN of the API server (null for public clusters)."
  value       = azurerm_kubernetes_cluster.this.private_fqdn
}

output "user_node_pool_ids" {
  description = "Map of user node pool name => ID."
  value       = { for k, p in azurerm_kubernetes_cluster_node_pool.user : k => p.id }
}
