# terraform/ai/qdrant — Qdrant vector database on Kubernetes via the official
# Helm chart (https://qdrant.github.io/qdrant-helm). API key enforced,
# persistence on, resources bounded.

locals {
  base_values = {
    replicaCount = var.replicas

    persistence = merge(
      { size = var.persistence_size },
      var.storage_class != null ? { storageClassName = var.storage_class } : {}
    )

    resources = {
      requests = {
        cpu    = var.resources.requests.cpu
        memory = var.resources.requests.memory
      }
      limits = {
        cpu    = var.resources.limits.cpu
        memory = var.resources.limits.memory
      }
    }

    # Restricted-PSS-compatible pod security.
    podSecurityContext = {
      runAsNonRoot = true
      runAsUser    = 1000
      fsGroup      = 1000
    }

    containerSecurityContext = {
      allowPrivilegeEscalation = false
      readOnlyRootFilesystem   = true
      capabilities             = { drop = ["ALL"] }
    }

    metrics = {
      serviceMonitor = { enabled = false }
    }
  }
}

resource "helm_release" "qdrant" {
  name             = var.release_name
  namespace        = var.namespace
  create_namespace = true

  repository = "https://qdrant.github.io/qdrant-helm"
  chart      = "qdrant"
  version    = var.chart_version

  values = [
    yamlencode(local.base_values),
    yamlencode(var.extra_values),
  ]

  # API key kept out of the plan-visible values.
  set_sensitive {
    name  = "apiKey"
    value = var.api_key
  }

  atomic          = true
  cleanup_on_fail = true
  timeout         = 600
}
