# terraform/ai/bedrock — Bedrock agent + knowledge base skeleton on OpenSearch
# Serverless (vector), model invocation logging, guardrails, and optional
# provisioned throughput.
#
# Skeleton note: the vector index inside the collection must be created
# out-of-band (TAP ingestion job / opensearch provider) before the knowledge
# base can ingest documents.

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  tags = merge(var.tags, { managed_by = "tap" })
}

# ---------------------------------------------------------------------------
# Model invocation logging (account singleton) → CloudWatch
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "invocation" {
  count = var.enable_invocation_logging ? 1 : 0

  name              = "/tap/bedrock/${var.name}/invocations"
  retention_in_days = var.invocation_log_retention_days
  kms_key_id        = var.logs_kms_key_arn

  tags = local.tags
}

data "aws_iam_policy_document" "logging_assume" {
  count = var.enable_invocation_logging ? 1 : 0

  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

data "aws_iam_policy_document" "logging" {
  count = var.enable_invocation_logging ? 1 : 0

  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.invocation[0].arn}:*"]
  }
}

resource "aws_iam_role" "logging" {
  count = var.enable_invocation_logging ? 1 : 0

  name               = "${var.name}-bedrock-logging"
  assume_role_policy = data.aws_iam_policy_document.logging_assume[0].json
  tags               = local.tags
}

resource "aws_iam_role_policy" "logging" {
  count = var.enable_invocation_logging ? 1 : 0

  name   = "invocation-logs"
  role   = aws_iam_role.logging[0].id
  policy = data.aws_iam_policy_document.logging[0].json
}

resource "aws_bedrock_model_invocation_logging_configuration" "this" {
  count = var.enable_invocation_logging ? 1 : 0

  logging_config {
    embedding_data_delivery_enabled = true
    image_data_delivery_enabled     = true
    text_data_delivery_enabled      = true

    cloudwatch_config {
      log_group_name = aws_cloudwatch_log_group.invocation[0].name
      role_arn       = aws_iam_role.logging[0].arn
    }
  }

  depends_on = [aws_iam_role_policy.logging]
}

# ---------------------------------------------------------------------------
# Guardrail
# ---------------------------------------------------------------------------

resource "aws_bedrock_guardrail" "this" {
  name                      = "${var.name}-guardrail"
  description               = "TAP content guardrail for ${var.name}"
  blocked_input_messaging   = var.guardrail_blocked_input_message
  blocked_outputs_messaging = var.guardrail_blocked_output_message

  content_policy_config {
    dynamic "filters_config" {
      for_each = var.guardrail_content_filters

      content {
        type            = filters_config.key
        input_strength  = filters_config.value.input_strength
        output_strength = filters_config.value.output_strength
      }
    }
  }

  dynamic "topic_policy_config" {
    for_each = length(var.guardrail_denied_topics) > 0 ? [1] : []

    content {
      dynamic "topics_config" {
        for_each = var.guardrail_denied_topics

        content {
          name       = topics_config.key
          definition = topics_config.value
          type       = "DENY"
        }
      }
    }
  }

  tags = local.tags
}

resource "aws_bedrock_guardrail_version" "this" {
  guardrail_arn = aws_bedrock_guardrail.this.guardrail_arn
  description   = "Pinned version managed by TAP"
}

# ---------------------------------------------------------------------------
# OpenSearch Serverless vector collection (knowledge base storage)
# ---------------------------------------------------------------------------

resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "${var.name}-enc"
  type = "encryption"

  policy = jsonencode({
    Rules = [{
      ResourceType = "collection"
      Resource     = ["collection/${var.name}"]
    }]
    AWSOwnedKey = true
  })
}

resource "aws_opensearchserverless_security_policy" "network" {
  name = "${var.name}-net"
  type = "network"

  # Private access only: reachable through OpenSearch Serverless VPC endpoints
  # and the Bedrock service, not the public internet.
  policy = jsonencode([{
    Rules = [
      {
        ResourceType = "collection"
        Resource     = ["collection/${var.name}"]
      },
      {
        ResourceType = "dashboard"
        Resource     = ["collection/${var.name}"]
      }
    ]
    AllowFromPublic = false
    SourceServices  = ["bedrock.amazonaws.com"]
  }])
}

resource "aws_opensearchserverless_collection" "this" {
  name = var.name
  type = "VECTORSEARCH"

  tags = local.tags

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network,
  ]
}

# ---------------------------------------------------------------------------
# Knowledge base role
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "kb_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

data "aws_iam_policy_document" "kb" {
  statement {
    sid       = "InvokeEmbeddingModel"
    actions   = ["bedrock:InvokeModel"]
    resources = [var.embedding_model_arn]
  }

  statement {
    sid       = "VectorStoreAccess"
    actions   = ["aoss:APIAccessAll"]
    resources = [aws_opensearchserverless_collection.this.arn]
  }
}

resource "aws_iam_role" "kb" {
  name               = "${var.name}-bedrock-kb"
  assume_role_policy = data.aws_iam_policy_document.kb_assume.json
  tags               = local.tags
}

resource "aws_iam_role_policy" "kb" {
  name   = "knowledge-base-access"
  role   = aws_iam_role.kb.id
  policy = data.aws_iam_policy_document.kb.json
}

resource "aws_opensearchserverless_access_policy" "kb" {
  name = "${var.name}-kb-access"
  type = "data"

  policy = jsonencode([{
    Rules = [
      {
        ResourceType = "collection"
        Resource     = ["collection/${var.name}"]
        Permission   = ["aoss:CollectionItems", "aoss:DescribeCollectionItems"]
      },
      {
        ResourceType = "index"
        Resource     = ["index/${var.name}/*"]
        Permission   = ["aoss:ReadDocument", "aoss:WriteDocument", "aoss:CreateIndex", "aoss:DescribeIndex", "aoss:UpdateIndex"]
      }
    ]
    Principal = [aws_iam_role.kb.arn]
  }])
}

# ---------------------------------------------------------------------------
# Knowledge base (vector) — skeleton; index created out-of-band
# ---------------------------------------------------------------------------

resource "aws_bedrockagent_knowledge_base" "this" {
  name     = "${var.name}-kb"
  role_arn = aws_iam_role.kb.arn

  knowledge_base_configuration {
    type = "VECTOR"

    vector_knowledge_base_configuration {
      embedding_model_arn = var.embedding_model_arn
    }
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"

    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.this.arn
      vector_index_name = var.vector_index_name

      field_mapping {
        vector_field   = "tap-vector"
        text_field     = "tap-text"
        metadata_field = "tap-metadata"
      }
    }
  }

  tags = local.tags

  depends_on = [
    aws_iam_role_policy.kb,
    aws_opensearchserverless_access_policy.kb,
  ]
}

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "agent_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

data "aws_iam_policy_document" "agent" {
  statement {
    sid     = "InvokeFoundationModel"
    actions = ["bedrock:InvokeModel"]
    resources = [
      "arn:${data.aws_partition.current.partition}:bedrock:${data.aws_region.current.name}::foundation-model/${var.agent_foundation_model}"
    ]
  }

  statement {
    sid       = "RetrieveFromKB"
    actions   = ["bedrock:Retrieve"]
    resources = [aws_bedrockagent_knowledge_base.this.arn]
  }

  statement {
    sid       = "ApplyGuardrail"
    actions   = ["bedrock:ApplyGuardrail"]
    resources = [aws_bedrock_guardrail.this.guardrail_arn]
  }
}

resource "aws_iam_role" "agent" {
  name               = "${var.name}-bedrock-agent"
  assume_role_policy = data.aws_iam_policy_document.agent_assume.json
  tags               = local.tags
}

resource "aws_iam_role_policy" "agent" {
  name   = "agent-access"
  role   = aws_iam_role.agent.id
  policy = data.aws_iam_policy_document.agent.json
}

resource "aws_bedrockagent_agent" "this" {
  agent_name              = "${var.name}-agent"
  agent_resource_role_arn = aws_iam_role.agent.arn
  foundation_model        = var.agent_foundation_model
  instruction             = var.agent_instruction

  idle_session_ttl_in_seconds = var.agent_idle_session_ttl

  guardrail_configuration {
    guardrail_identifier = aws_bedrock_guardrail.this.guardrail_id
    guardrail_version    = aws_bedrock_guardrail_version.this.version
  }

  tags = local.tags

  depends_on = [aws_iam_role_policy.agent]
}

resource "aws_bedrockagent_agent_knowledge_base_association" "this" {
  agent_id             = aws_bedrockagent_agent.this.agent_id
  knowledge_base_id    = aws_bedrockagent_knowledge_base.this.id
  description          = "TAP knowledge base for ${var.name}"
  knowledge_base_state = "ENABLED"
}

# ---------------------------------------------------------------------------
# Optional provisioned throughput
# ---------------------------------------------------------------------------

resource "aws_bedrock_provisioned_model_throughput" "this" {
  count = var.provisioned_throughput.enabled ? 1 : 0

  provisioned_model_name = "${var.name}-pt"
  model_arn              = var.provisioned_throughput.model_arn
  model_units            = var.provisioned_throughput.model_units
  commitment_duration    = var.provisioned_throughput.commitment_duration

  tags = local.tags

  lifecycle {
    precondition {
      condition     = var.provisioned_throughput.model_arn != null
      error_message = "provisioned_throughput.model_arn is required when enabled = true."
    }
  }
}
