# terraform/ai/pinecone — serverless Pinecone index.
# The provider authenticates via the PINECONE_API_KEY environment variable
# (injected by the TAP runner from the workspace secret store) — never put
# the key in Terraform variables or state.

resource "pinecone_index" "this" {
  name      = var.index_name
  dimension = var.dimension
  metric    = var.metric

  spec = {
    serverless = {
      cloud  = var.cloud
      region = var.region
    }
  }

  deletion_protection = var.deletion_protection ? "enabled" : "disabled"
}
