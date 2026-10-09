terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    # Required transitively: child modules are selected with count, but their
    # providers must still be configurable from the root.
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13"
    }
    pinecone = {
      source  = "pinecone-io/pinecone"
      version = "~> 1.0"
    }
  }
}
