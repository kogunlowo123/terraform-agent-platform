# examples/aws-eks-platform — root module: VPC + EKS + OIDC runner role.
# Run through TAP: `tap run plan --workspace <ws> --dir examples/aws-eks-platform`

terraform {
  required_version = ">= 1.6.0"

  # Local backend for standalone development only; TAP injects its managed,
  # encrypted state backend at run time (see ARCHITECTURE.md §9).
  backend "local" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
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
  name        = "platform"
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
  nat_gateway_mode = "per_az"

  tags = module.tags.tags
}

module "eks" {
  source = "../../terraform/aws/eks"

  name               = module.naming.prefix
  kubernetes_version = var.kubernetes_version
  subnet_ids         = module.vpc.private_subnet_ids

  node_groups = {
    system = {
      instance_types = ["m6i.large"]
      min_size       = 2
      max_size       = 4
      desired_size   = 2
    }
    runners = {
      instance_types = ["c6i.xlarge"]
      capacity_type  = "SPOT"
      min_size       = 0
      max_size       = 20
      desired_size   = 2
      labels         = { "tap.dev/role" = "runner" }
    }
  }

  access_entries = var.cluster_admin_role_arn != null ? {
    platform_admins = {
      principal_arn = var.cluster_admin_role_arn
      policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
    }
  } : {}

  tags = module.tags.tags
}

# Federated role TAP runners assume via OIDC — no static credentials.
module "runner_role" {
  source = "../../terraform/aws/iam"

  role_name = "${module.naming.prefix}-tap-runner"

  enable_github_oidc = var.github_org != null
  github_subjects    = var.github_org != null ? ["repo:${var.github_org}/*:environment:${var.environment}"] : []

  tap_oidc_issuer_url  = var.tap_oidc_issuer_url
  tap_oidc_thumbprints = var.tap_oidc_thumbprints
  tap_subjects         = var.tap_oidc_issuer_url != null ? ["workspace:${var.org}/${var.environment}/*"] : []

  permissions_boundary_arn = var.runner_permissions_boundary_arn

  policy_arns = ["arn:aws:iam::aws:policy/ReadOnlyAccess"] # plans read; applies get scoped inline policies per workspace

  tags = module.tags.tags
}
