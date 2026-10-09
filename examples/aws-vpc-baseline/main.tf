# examples/aws-vpc-baseline — root module: shared/naming + shared/tags + aws/vpc.
# Run through TAP: `tap run plan --workspace <ws> --dir examples/aws-vpc-baseline`

terraform {
  required_version = ">= 1.6.0"

  # Local backend for standalone development only. When executed by TAP, the
  # runner injects a generated backend pointing at TAP-managed encrypted state
  # (per-tenant KMS, Postgres advisory locking) — see docs/architecture/ARCHITECTURE.md §9.
  backend "local" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = module.tags.tags
  }
}

module "naming" {
  source = "../../terraform/shared/naming"

  org         = var.org
  environment = var.environment
  region      = var.region
  name        = "net"
}

module "tags" {
  source = "../../terraform/shared/tags"

  owner       = var.owner
  cost_center = var.cost_center
  environment = var.environment
  data_class  = var.data_class
  extra_tags  = module.naming.tags_base
}

module "vpc" {
  source = "../../terraform/aws/vpc"

  name             = module.naming.prefix
  vpc_cidr         = var.vpc_cidr
  azs              = var.azs
  nat_gateway_mode = var.nat_gateway_mode

  tags = module.tags.tags
}
