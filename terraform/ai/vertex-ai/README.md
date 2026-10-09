# ai/vertex-ai

Vertex AI building blocks:

- **Online prediction endpoint** (optional VPC peering network, optional CMEK).
- **Vector Search** index + index endpoint skeleton (tree-AH config; stream or
  batch updates; private when a network is supplied).
- **Service agent IAM**: forces creation of the `aiplatform` service identity
  and grants it CMEK encrypter/decrypter and `objectViewer` on data buckets.

> Deliberate gap: *deploying a model onto the endpoint*
> (`endpoints.deployModel`) has no stable Terraform resource. TAP's LLMOps
> agent performs the deploy via the Vertex AI API after apply; the endpoint
> and IAM here make that call possible.

## Usage

```hcl
module "vertex" {
  source = "../../terraform/ai/vertex-ai"

  name       = "${module.naming.prefix}-llm"
  project_id = "acme-prod"
  region     = "europe-west1"

  endpoint_network = "projects/1234567890/global/networks/acme-prod-vpc"
  cmek_key_name    = google_kms_crypto_key.vertex.id

  vector_index = {
    dimensions         = 768
    contents_delta_uri = "gs://acme-prod-embeddings/delta"
  }

  service_agent_bucket_grants = ["acme-prod-embeddings"]

  labels = module.tags.tags
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `name`, `project_id`, `region` | `string` | — | Identity and placement. |
| `endpoint_display_name` | `string` | `null` (= name) | Endpoint display name. |
| `endpoint_network` | `string` | `null` | Peered VPC for private access. |
| `cmek_key_name` | `string` | `null` | CMEK for endpoint + index endpoint. |
| `vector_index` | `object` | `null` | dimensions (required), neighbors, distance, shard, update method, delta URI, tree-AH knobs. |
| `service_agent_kms_grant` | `bool` | `true` | Grant agent on CMEK. |
| `service_agent_bucket_grants` | `list(string)` | `[]` | Buckets for objectViewer. |
| `labels` | `map(string)` | `{}` | Labels. |

## Outputs

| Name | Description |
|---|---|
| `endpoint_id`, `endpoint_name` | Prediction endpoint. |
| `index_id`, `index_endpoint_id`, `index_endpoint_public_domain` | Vector Search. |
| `service_agent_email` | aiplatform service agent. |
