# ai/bedrock

Bedrock agent + RAG knowledge base skeleton:

- **Agent** (Claude by default) with IAM role scoped to model invoke, KB
  retrieve, and guardrail apply; KB association included.
- **Knowledge base** (VECTOR) on **OpenSearch Serverless** (`VECTORSEARCH`
  collection, public access off, Bedrock as allowed source service).
- **Guardrail** (content filters incl. prompt-attack, optional denied topics)
  with a pinned version wired into the agent.
- **Model invocation logging** to CloudWatch (account/region singleton —
  enable in exactly one workspace).
- Optional **provisioned throughput** purchase.

> Skeleton caveat: the vector index (`vector_index_name` with fields
> `tap-vector`/`tap-text`/`tap-metadata`) must be created in the collection
> out-of-band before the KB can sync — TAP's ingestion job does this.

## Usage

```hcl
module "bedrock" {
  source = "../../terraform/ai/bedrock"

  name                = "${module.naming.prefix}-rag"
  embedding_model_arn = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"

  guardrail_denied_topics = {
    credentials = "Requests to reveal, generate, or manipulate cloud credentials or secrets."
  }

  provisioned_throughput = {
    enabled     = false
  }

  tags = module.tags.tags
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `string` | — | 3-28 lowercase chars (AOSS limit). |
| `agent_foundation_model` | `string` | Claude 3.5 Sonnet v2 | Agent model ID. |
| `agent_instruction` | `string` | TAP assistant prompt | >= 40 chars. |
| `agent_idle_session_ttl` | `number` | `600` | Seconds. |
| `embedding_model_arn` | `string` | — | KB embedding model. |
| `vector_index_name` | `string` | `"tap-kb-index"` | Out-of-band index. |
| `provisioned_throughput` | `object` | disabled | model_arn/units/commitment. |
| `enable_invocation_logging` | `bool` | `true` | Account singleton. |
| `invocation_log_retention_days` | `number` | `90` | Retention. |
| `logs_kms_key_arn` | `string` | `null` | CMK for logs. |
| `guardrail_*` | various | high-strength filters | Messages, filters, denied topics. |
| `tags` | `map(string)` | `{}` | Tags. |

## Outputs

| Name | Description |
|---|---|
| `agent_id`, `agent_arn` | Agent identifiers. |
| `knowledge_base_id`, `knowledge_base_arn`, `kb_role_arn` | KB wiring. |
| `collection_arn`, `collection_endpoint` | Vector store. |
| `guardrail_id`, `guardrail_version` | Guardrail. |
| `provisioned_throughput_arn` | PT (null when disabled). |
| `invocation_log_group` | Invocation logs. |
