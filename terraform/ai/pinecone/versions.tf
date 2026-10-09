terraform {
  required_version = ">= 1.6.0"

  required_providers {
    pinecone = {
      source  = "pinecone-io/pinecone"
      version = "~> 1.0"
    }
  }
}
