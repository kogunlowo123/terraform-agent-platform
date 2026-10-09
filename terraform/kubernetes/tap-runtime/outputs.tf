output "namespace" {
  description = "Name of the runtime namespace."
  value       = kubernetes_namespace_v1.this.metadata[0].name
}

output "service_account_name" {
  description = "Runner ServiceAccount name."
  value       = kubernetes_service_account_v1.runner.metadata[0].name
}

output "network_policy_names" {
  description = "Names of all NetworkPolicies created."
  value = [
    kubernetes_network_policy_v1.default_deny.metadata[0].name,
    kubernetes_network_policy_v1.allow_dns.metadata[0].name,
    kubernetes_network_policy_v1.allow_cloud_egress.metadata[0].name,
    kubernetes_network_policy_v1.allow_opa.metadata[0].name,
  ]
}
