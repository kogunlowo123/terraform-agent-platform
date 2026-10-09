# terraform/ai/vertex-ai — online prediction endpoint, Vector Search index +
# index endpoint skeleton, and service agent IAM (CMEK + bucket grants).
#
# Deliberate gap: deploying a *model* onto the prediction endpoint
# (endpoints.deployModel) has no stable Terraform resource — TAP's LLMOps
# agent performs that step through the Vertex AI API after apply.

locals {
  labels = merge(var.labels, { managed_by = "tap" })

  endpoint_display_name = coalesce(var.endpoint_display_name, var.name)
}

# ---------------------------------------------------------------------------
# Service agent identity + IAM
# ---------------------------------------------------------------------------

# Forces creation of the Vertex AI service agent so IAM grants can target it.
resource "google_project_service_identity" "aiplatform" {
  provider = google-beta

  project = var.project_id
  service = "aiplatform.googleapis.com"
}

resource "google_kms_crypto_key_iam_member" "service_agent" {
  count = var.cmek_key_name != null && var.service_agent_kms_grant ? 1 : 0

  crypto_key_id = var.cmek_key_name
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${google_project_service_identity.aiplatform.email}"
}

resource "google_storage_bucket_iam_member" "service_agent" {
  for_each = toset(var.service_agent_bucket_grants)

  bucket = each.value
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_project_service_identity.aiplatform.email}"
}

# ---------------------------------------------------------------------------
# Online prediction endpoint
# ---------------------------------------------------------------------------

resource "google_vertex_ai_endpoint" "this" {
  name         = var.name
  display_name = local.endpoint_display_name
  project      = var.project_id
  location     = var.region
  region       = var.region

  network = var.endpoint_network

  dynamic "encryption_spec" {
    for_each = var.cmek_key_name != null ? [1] : []

    content {
      kms_key_name = var.cmek_key_name
    }
  }

  labels = local.labels

  depends_on = [google_kms_crypto_key_iam_member.service_agent]
}

# ---------------------------------------------------------------------------
# Vector Search index + index endpoint (skeleton)
# ---------------------------------------------------------------------------

resource "google_vertex_ai_index" "this" {
  count = var.vector_index != null ? 1 : 0

  display_name = "${var.name}-index"
  project      = var.project_id
  region       = var.region

  index_update_method = var.vector_index.index_update_method

  metadata {
    contents_delta_uri = var.vector_index.contents_delta_uri

    config {
      dimensions                  = var.vector_index.dimensions
      approximate_neighbors_count = var.vector_index.approximate_neighbors_count
      distance_measure_type       = var.vector_index.distance_measure_type
      shard_size                  = var.vector_index.shard_size

      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count    = var.vector_index.leaf_node_embedding_count
          leaf_nodes_to_search_percent = var.vector_index.leaf_nodes_to_search_percent
        }
      }
    }
  }

  labels = local.labels
}

resource "google_vertex_ai_index_endpoint" "this" {
  count = var.vector_index != null ? 1 : 0

  display_name = "${var.name}-index-endpoint"
  project      = var.project_id
  region       = var.region

  network = var.endpoint_network

  public_endpoint_enabled = var.endpoint_network == null # private when a network is given

  # Note: google_vertex_ai_index_endpoint does not support encryption_spec;
  # CMEK applies to the prediction endpoint above only.

  labels = local.labels

  depends_on = [google_kms_crypto_key_iam_member.service_agent]
}
