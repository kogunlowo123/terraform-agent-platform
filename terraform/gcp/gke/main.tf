# terraform/gcp/gke — VPC-native GKE with workload identity, shielded +
# private nodes, release channel, optional node auto-provisioning, and a
# minimal-permission node service account.

locals {
  labels = merge(var.labels, { managed_by = "tap" })

  node_sa_email = var.node_service_account != null ? var.node_service_account : google_service_account.nodes[0].email
}

# ---------------------------------------------------------------------------
# Minimal node service account (created when not supplied)
# ---------------------------------------------------------------------------

resource "google_service_account" "nodes" {
  count = var.node_service_account == null ? 1 : 0

  project      = var.project_id
  account_id   = "${substr(var.name, 0, 22)}-nodes"
  display_name = "GKE nodes for ${var.name} (TAP-managed)"
}

resource "google_project_iam_member" "nodes" {
  for_each = var.node_service_account == null ? toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/artifactregistry.reader",
  ]) : toset([])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.nodes[0].email}"
}

# ---------------------------------------------------------------------------
# Cluster
# ---------------------------------------------------------------------------

resource "google_container_cluster" "this" {
  name     = var.name
  project  = var.project_id
  location = var.location

  network    = var.network
  subnetwork = var.subnetwork

  # Node pools are managed separately; remove the default one.
  remove_default_node_pool = true
  initial_node_count       = 1

  networking_mode = "VPC_NATIVE"

  ip_allocation_policy {
    cluster_secondary_range_name  = var.pods_secondary_range_name
    services_secondary_range_name = var.services_secondary_range_name
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = var.enable_private_endpoint
    master_ipv4_cidr_block  = var.master_ipv4_cidr_block
  }

  dynamic "master_authorized_networks_config" {
    for_each = length(var.master_authorized_networks) > 0 ? [1] : []

    content {
      dynamic "cidr_blocks" {
        for_each = var.master_authorized_networks

        content {
          display_name = cidr_blocks.key
          cidr_block   = cidr_blocks.value
        }
      }
    }
  }

  release_channel {
    channel = var.release_channel
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  dynamic "cluster_autoscaling" {
    for_each = var.enable_node_auto_provisioning ? [1] : []

    content {
      enabled = true

      resource_limits {
        resource_type = "cpu"
        minimum       = 0
        maximum       = var.nap_resource_limits.max_cpu
      }

      resource_limits {
        resource_type = "memory"
        minimum       = 0
        maximum       = var.nap_resource_limits.max_memory
      }

      auto_provisioning_defaults {
        service_account = local.node_sa_email
        oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]

        shielded_instance_config {
          enable_secure_boot          = true
          enable_integrity_monitoring = true
        }

        management {
          auto_repair  = true
          auto_upgrade = true
        }
      }
    }
  }

  binary_authorization {
    evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
  }

  logging_service    = "logging.googleapis.com/kubernetes"
  monitoring_service = "monitoring.googleapis.com/kubernetes"

  deletion_protection = var.deletion_protection

  resource_labels = local.labels

  lifecycle {
    ignore_changes = [initial_node_count]
  }
}

# ---------------------------------------------------------------------------
# Node pools — shielded nodes, GKE metadata server, autoscaling, auto-repair
# ---------------------------------------------------------------------------

resource "google_container_node_pool" "this" {
  for_each = var.node_pools

  name     = each.key
  project  = var.project_id
  location = var.location
  cluster  = google_container_cluster.this.name

  autoscaling {
    min_node_count = each.value.min_count
    max_node_count = each.value.max_count
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }

  node_config {
    machine_type    = each.value.machine_type
    disk_size_gb    = each.value.disk_size_gb
    disk_type       = each.value.disk_type
    spot            = each.value.spot
    service_account = local.node_sa_email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]

    labels = each.value.labels

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }

    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    metadata = {
      disable-legacy-endpoints = "true"
    }

    dynamic "taint" {
      for_each = each.value.taints

      content {
        key    = taint.value.key
        value  = taint.value.value
        effect = taint.value.effect
      }
    }
  }
}
