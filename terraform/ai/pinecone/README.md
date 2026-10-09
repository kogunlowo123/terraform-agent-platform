# ai/pinecone

Serverless Pinecone index via the `pinecone-io/pinecone` provider.

- **Auth**: the provider reads `PINECONE_API_KEY` from the environment — the
  TAP runner injects it from the workspace secret store. No key in variables
  or state.
- Deletion protection enabled by default.

## Usage

```hcl
module "pinecone" {
  source = "../../terraform/ai/pinecone"

  index_name = "${module.naming.prefix}-rag"
  dimension  = 1536
  metric     = "cosine"
  cloud      = "aws"
  region     = "us-east-1"
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `index_name` | `string` | — | 1-45 lowercase chars. |
| `dimension` | `number` | — | Must match the embedding model. |
| `metric` | `string` | `"cosine"` | cosine/euclidean/dotproduct. |
| `cloud` | `string` | `"aws"` | aws/gcp/azure. |
| `region` | `string` | `"us-east-1"` | Serverless region. |
| `deletion_protection` | `bool` | `true` | Pinecone-side guard. |

## Outputs

| Name | Description |
|---|---|
| `index_name` | Index name. |
| `index_host` | Client host URL. |
| `dimension`, `metric` | Index geometry. |
