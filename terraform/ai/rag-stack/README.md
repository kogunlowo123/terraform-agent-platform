# ai/rag-stack

Composition module — demonstrates how TAP wires modules together:

- **Vector backend selection** via `vector_backend = "qdrant" | "pinecone"`,
  implemented with conditional `count` on the child modules
  (`../qdrant`, `../pinecone`). Exactly one is instantiated.
- **Document bucket** (S3): versioned, SSE-KMS with bucket keys, all public
  access blocked, TLS-only bucket policy, lifecycle expiry of noncurrent
  versions.
- **Ingestion queue** (SQS): KMS-encrypted, DLQ with redrive policy.

Providers `aws`, `helm`, and `pinecone` are all declared because Terraform
must be able to configure the child modules even when their count is 0.

## Usage

```hcl
module "rag_stack" {
  source = "../../terraform/ai/rag-stack"

  name           = "${module.naming.prefix}-rag"
  vector_backend = "qdrant"

  qdrant = {
    namespace        = "vector"
    replicas         = 3
    persistence_size = "100Gi"
    api_key          = var.qdrant_api_key
  }

  tags = module.tags.tags
}
```

Switching to Pinecone:

```hcl
  vector_backend = "pinecone"
  pinecone = {
    dimension = 1536
    cloud     = "aws"
    region    = "us-east-1"
  }
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `string` | — | Base name. |
| `vector_backend` | `string` | — | `qdrant` or `pinecone`. |
| `qdrant` | `object` (sensitive) | `{}` | Namespace, replicas, size, api_key (required for qdrant). |
| `pinecone` | `object` | `{}` | dimension, metric, cloud, region. |
| `kms_key_arn` | `string` | `null` | CMK; null creates one. |
| `bucket_force_destroy` | `bool` | `false` | Keep false in prod. |
| `document_retention_days` | `number` | `90` | Noncurrent version expiry. |
| `queue_visibility_timeout` | `number` | `300` | Seconds. |
| `queue_max_receive_count` | `number` | `5` | Before DLQ. |
| `tags` | `map(string)` | `{}` | AWS tags. |

## Outputs

| Name | Description |
|---|---|
| `vector_backend`, `vector_endpoint` | Selected backend + endpoint. |
| `document_bucket_name`, `document_bucket_arn` | Document store. |
| `ingest_queue_url`, `ingest_queue_arn`, `dlq_arn` | Ingestion pipeline. |
| `kms_key_arn` | Encryption key. |
