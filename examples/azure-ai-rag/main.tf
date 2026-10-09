# examples/azure-ai-rag — root module: Azure landing zone + Key Vault +
# Azure OpenAI + rag-stack (qdrant backend on an existing K8s cluster,
# document bucket + ingestion queue on AWS).
# Run through TAP: `tap run plan --workspace <ws> --dir examples/azure-ai-rag`

terraform {
  required_version = ">= 1.6.0"

  # Local backend for standalone development only; TAP injects its managed,
  # encrypted state backend at run time (see ARCHITECTURE.md §9).
  backend "local" {}

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
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

provider "azurerm" {
  features {}
}

# AWS hosts the RAG document bucket + ingestion queue.
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = module.tags.tags
  }
}

# Kubernetes cluster that hosts Qdrant (e.g. the AKS cluster from azure/aks).
provider "helm" {
  kubernetes {
    config_path    = var.kubeconfig_path
    config_context = var.kubeconfig_context
  }
}

# Unused with the qdrant backend, but must be configurable (count = 0 module).
# Reads PINECONE_API_KEY from the environment when actually used.
provider "pinecone" {}

module "naming" {
  source = "../../terraform/shared/naming"

  org         = var.org
  environment = var.environment
  region      = var.azure_location
  name        = "ai"
}

module "tags" {
  source = "../../terraform/shared/tags"

  owner       = var.owner
  cost_center = var.cost_center
  environment = var.environment
  data_class  = var.data_class
  extra_tags  = module.naming.tags_base
}

module "landing_zone" {
  source = "../../terraform/azure/landing-zone"

  name     = module.naming.prefix
  location = var.azure_location

  resource_groups = {
    mgmt = {}
    ai   = {}
  }

  management_group_key = "mgmt"
  allowed_locations    = var.allowed_locations
  required_tag_keys    = ["owner", "cost_center", "environment", "data_class"]

  tags = module.tags.tags
}

module "key_vault" {
  source = "../../terraform/azure/key-vault"

  name                = replace("${module.naming.prefix}-kv", "_", "-")
  resource_group_name = module.landing_zone.resource_group_names["ai"]
  location            = var.azure_location

  # Standalone example keeps the vault reachable for bootstrap; flip to false
  # and add a private_endpoint once VNet + DNS zones exist.
  public_network_access_enabled = true
  allowed_ip_rules              = var.vault_allowed_ip_rules

  log_analytics_workspace_id = module.landing_zone.log_analytics_workspace_id

  tags = module.tags.tags
}

module "azure_openai" {
  source = "../../terraform/ai/azure-openai"

  name                = "${module.naming.prefix}-aoai"
  resource_group_name = module.landing_zone.resource_group_names["ai"]
  location            = var.azure_location

  # Standalone example: public until a private endpoint subnet is supplied.
  public_network_access_enabled = true

  deployments = {
    gpt4o = {
      model    = "gpt-4o"
      version  = "2024-08-06"
      capacity = 50
    }
    embeddings = {
      model    = "text-embedding-3-large"
      version  = "1"
      capacity = 120
    }
  }

  log_analytics_workspace_id = module.landing_zone.log_analytics_workspace_id

  tags = module.tags.tags
}

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
