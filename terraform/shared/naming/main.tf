# terraform/shared/naming — locals-only naming convention module for TAP.
# Produces a deterministic resource name prefix and a base tag map that every
# other TAP module merges into its own tags/labels.

locals {
  env_short_codes = {
    dev         = "dev"
    development = "dev"
    test        = "tst"
    stage       = "stg"
    staging     = "stg"
    prod        = "prd"
    production  = "prd"
    sandbox     = "sbx"
  }

  region_short_codes = {
    # AWS
    "us-east-1"      = "use1"
    "us-east-2"      = "use2"
    "us-west-1"      = "usw1"
    "us-west-2"      = "usw2"
    "eu-west-1"      = "euw1"
    "eu-west-2"      = "euw2"
    "eu-west-3"      = "euw3"
    "eu-central-1"   = "euc1"
    "eu-north-1"     = "eun1"
    "ap-southeast-1" = "apse1"
    "ap-southeast-2" = "apse2"
    "ap-northeast-1" = "apne1"
    "ap-northeast-2" = "apne2"
    "ap-south-1"     = "aps1"
    "ca-central-1"   = "cac1"
    "sa-east-1"      = "sae1"

    # Azure
    "eastus"             = "eus"
    "eastus2"            = "eus2"
    "westus2"            = "wus2"
    "westus3"            = "wus3"
    "centralus"          = "cus"
    "northeurope"        = "neu"
    "westeurope"         = "weu"
    "uksouth"            = "uks"
    "ukwest"             = "ukw"
    "francecentral"      = "frc"
    "germanywestcentral" = "gwc"
    "swedencentral"      = "sec"
    "southeastasia"      = "sea"
    "australiaeast"      = "aue"
    "canadacentral"      = "cac"

    # GCP
    "us-central1"          = "usc1"
    "us-east1"             = "use1g"
    "us-east4"             = "use4"
    "us-west1"             = "usw1g"
    "europe-west1"         = "euw1g"
    "europe-west2"         = "euw2g"
    "europe-west3"         = "euw3g"
    "europe-west4"         = "euw4"
    "europe-north1"        = "eun1g"
    "asia-southeast1"      = "ase1"
    "asia-northeast1"      = "ane1"
    "australia-southeast1" = "ause1"
  }

  env_short = lookup(local.env_short_codes, lower(var.environment), substr(lower(var.environment), 0, 3))

  # Fall back to a compacted form of the raw region when no short code is known.
  region_short = lookup(local.region_short_codes, lower(var.region), replace(lower(var.region), "-", ""))

  prefix = join(var.delimiter, compact([var.org, local.env_short, local.region_short, var.name]))

  tags_base = merge(
    var.additional_tags,
    {
      organization = var.org
      environment  = lower(var.environment)
      region       = lower(var.region)
      managed_by   = "tap"
    }
  )
}
