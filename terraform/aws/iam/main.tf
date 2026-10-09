# terraform/aws/iam — OIDC federation role for TAP runners.
# Trusts GitHub Actions OIDC and/or the TAP platform OIDC issuer, with
# mandatory sub/aud conditions (no wildcard-only trust), permission boundary
# support, and least-privilege policy attachment.

locals {
  tags = merge(var.tags, { managed_by = "tap" })

  github_issuer_host = "token.actions.githubusercontent.com"

  create_github_provider = var.enable_github_oidc && var.github_oidc_provider_arn == null
  github_provider_arn    = var.enable_github_oidc ? (local.create_github_provider ? aws_iam_openid_connect_provider.github[0].arn : var.github_oidc_provider_arn) : null

  tap_enabled         = var.tap_oidc_issuer_url != null
  tap_issuer_host     = local.tap_enabled ? replace(var.tap_oidc_issuer_url, "https://", "") : null
  create_tap_provider = local.tap_enabled && var.tap_oidc_provider_arn == null
  tap_provider_arn    = local.tap_enabled ? (local.create_tap_provider ? aws_iam_openid_connect_provider.tap[0].arn : var.tap_oidc_provider_arn) : null
}

# ---------------------------------------------------------------------------
# OIDC identity providers
# ---------------------------------------------------------------------------

resource "aws_iam_openid_connect_provider" "github" {
  count = local.create_github_provider ? 1 : 0

  url            = "https://${local.github_issuer_host}"
  client_id_list = ["sts.amazonaws.com"]

  # AWS validates GitHub's cert chain against trusted CAs; thumbprints are
  # still required by the API but no longer security-relevant for GitHub.
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
  ]

  tags = local.tags
}

resource "aws_iam_openid_connect_provider" "tap" {
  count = local.create_tap_provider ? 1 : 0

  url             = var.tap_oidc_issuer_url
  client_id_list  = [var.tap_oidc_audience]
  thumbprint_list = var.tap_oidc_thumbprints

  tags = local.tags
}

# ---------------------------------------------------------------------------
# Trust policy
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "assume" {
  dynamic "statement" {
    for_each = var.enable_github_oidc && length(var.github_subjects) > 0 ? [1] : []

    content {
      sid     = "GitHubActionsOIDC"
      actions = ["sts:AssumeRoleWithWebIdentity"]

      principals {
        type        = "Federated"
        identifiers = [local.github_provider_arn]
      }

      condition {
        test     = "StringEquals"
        variable = "${local.github_issuer_host}:aud"
        values   = ["sts.amazonaws.com"]
      }

      condition {
        test     = "StringLike"
        variable = "${local.github_issuer_host}:sub"
        values   = var.github_subjects
      }
    }
  }

  dynamic "statement" {
    for_each = local.tap_enabled && length(var.tap_subjects) > 0 ? [1] : []

    content {
      sid     = "TAPPlatformOIDC"
      actions = ["sts:AssumeRoleWithWebIdentity"]

      principals {
        type        = "Federated"
        identifiers = [local.tap_provider_arn]
      }

      condition {
        test     = "StringEquals"
        variable = "${local.tap_issuer_host}:aud"
        values   = [var.tap_oidc_audience]
      }

      condition {
        test     = "StringLike"
        variable = "${local.tap_issuer_host}:sub"
        values   = var.tap_subjects
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Role + policies
# ---------------------------------------------------------------------------

resource "aws_iam_role" "this" {
  name                 = var.role_name
  assume_role_policy   = data.aws_iam_policy_document.assume.json
  permissions_boundary = var.permissions_boundary_arn
  max_session_duration = var.max_session_duration

  tags = local.tags

  lifecycle {
    precondition {
      condition     = (var.enable_github_oidc && length(var.github_subjects) > 0) || (local.tap_enabled && length(var.tap_subjects) > 0)
      error_message = "At least one trust source must be configured: GitHub (enable_github_oidc + github_subjects) or TAP (tap_oidc_issuer_url + tap_subjects)."
    }
  }
}

resource "aws_iam_role_policy_attachment" "managed" {
  for_each = toset(var.policy_arns)

  role       = aws_iam_role.this.name
  policy_arn = each.value
}

resource "aws_iam_role_policy" "inline" {
  for_each = var.inline_policies

  name   = each.key
  role   = aws_iam_role.this.id
  policy = each.value
}
