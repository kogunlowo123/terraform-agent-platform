# terraform/kubernetes/tap-runtime — namespace-scoped runtime for TAP runner
# pods: restricted Pod Security labels, a no-automount ServiceAccount,
# ResourceQuota, LimitRange, and default-deny NetworkPolicy with explicit
# egress to cloud APIs, DNS, and the OPA policy service.

locals {
  labels = merge(var.labels, {
    "app.kubernetes.io/part-of"    = "tap"
    "app.kubernetes.io/managed-by" = "terraform"
  })
}

resource "kubernetes_namespace_v1" "this" {
  metadata {
    name = var.namespace

    labels = merge(local.labels, {
      "pod-security.kubernetes.io/enforce" = var.pod_security_level
      "pod-security.kubernetes.io/audit"   = "restricted"
      "pod-security.kubernetes.io/warn"    = "restricted"
    })
  }
}

resource "kubernetes_service_account_v1" "runner" {
  metadata {
    name      = var.service_account_name
    namespace = kubernetes_namespace_v1.this.metadata[0].name
    labels    = local.labels
  }

  # Runners authenticate to clouds via OIDC token exchange, never via a
  # long-lived mounted token.
  automount_service_account_token = false
}

resource "kubernetes_resource_quota_v1" "this" {
  metadata {
    name      = "tap-runtime-quota"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
    labels    = local.labels
  }

  spec {
    hard = {
      "requests.cpu"    = var.resource_quota.requests_cpu
      "requests.memory" = var.resource_quota.requests_memory
      "limits.cpu"      = var.resource_quota.limits_cpu
      "limits.memory"   = var.resource_quota.limits_memory
      "pods"            = var.resource_quota.pods
    }
  }
}

resource "kubernetes_limit_range_v1" "this" {
  metadata {
    name      = "tap-runtime-limits"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
    labels    = local.labels
  }

  spec {
    limit {
      type = "Container"

      default = {
        cpu    = var.container_limits.default_cpu
        memory = var.container_limits.default_memory
      }

      default_request = {
        cpu    = var.container_limits.default_request_cpu
        memory = var.container_limits.default_request_memory
      }

      max = {
        cpu    = var.container_limits.max_cpu
        memory = var.container_limits.max_memory
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Network policies
# ---------------------------------------------------------------------------

# 1. Default deny all ingress and egress for every pod in the namespace.
resource "kubernetes_network_policy_v1" "default_deny" {
  metadata {
    name      = "default-deny-all"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
    labels    = local.labels
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}

# 2. Allow DNS resolution (kube-dns) for all pods.
resource "kubernetes_network_policy_v1" "allow_dns" {
  metadata {
    name      = "allow-dns-egress"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
    labels    = local.labels
  }

  spec {
    pod_selector {}
    policy_types = ["Egress"]

    egress {
      to {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "kube-system" }
        }
      }

      ports {
        port     = "53"
        protocol = "UDP"
      }

      ports {
        port     = "53"
        protocol = "TCP"
      }
    }
  }
}

# 3. Allow HTTPS egress to cloud provider APIs (public internet minus RFC1918
#    and the metadata service by default).
resource "kubernetes_network_policy_v1" "allow_cloud_egress" {
  metadata {
    name      = "allow-cloud-egress"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
    labels    = local.labels
  }

  spec {
    pod_selector {}
    policy_types = ["Egress"]

    egress {
      dynamic "to" {
        for_each = var.egress_cidrs

        content {
          ip_block {
            cidr   = to.value.cidr
            except = to.value.except
          }
        }
      }

      ports {
        port     = "443"
        protocol = "TCP"
      }
    }
  }
}

# 4. Allow egress to the in-cluster OPA policy service.
resource "kubernetes_network_policy_v1" "allow_opa" {
  metadata {
    name      = "allow-opa-egress"
    namespace = kubernetes_namespace_v1.this.metadata[0].name
    labels    = local.labels
  }

  spec {
    pod_selector {}
    policy_types = ["Egress"]

    egress {
      to {
        namespace_selector {
          match_labels = var.opa_endpoints.namespace_labels
        }
      }

      ports {
        port     = tostring(var.opa_endpoints.port)
        protocol = "TCP"
      }
    }
  }
}
