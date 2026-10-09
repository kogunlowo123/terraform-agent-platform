# terraform/ai/rag-stack — composition module demonstrating TAP module
# composition: a selectable vector backend (qdrant | pinecone via conditional
# count), a hardened S3 document bucket, and a KMS-encrypted ingestion queue
# with DLQ.

locals {
  tags = merge(var.tags, { managed_by = "tap", component = "rag-stack" })

  use_qdrant   = var.vector_backend == "qdrant"
  use_pinecone = var.vector_backend == "pinecone"

  kms_key_arn = var.kms_key_arn != null ? var.kms_key_arn : aws_kms_key.this[0].arn
}

# ---------------------------------------------------------------------------
# Vector backend — exactly one of the two child modules is instantiated
# ---------------------------------------------------------------------------

module "qdrant" {
  source = "../qdrant"
  count  = local.use_qdrant ? 1 : 0

  release_name     = "${var.name}-qdrant"
  namespace        = var.qdrant.namespace
  replicas         = var.qdrant.replicas
  chart_version    = var.qdrant.chart_version
  persistence_size = var.qdrant.persistence_size
  storage_class    = var.qdrant.storage_class
  api_key          = var.qdrant.api_key
}

module "pinecone" {
  source = "../pinecone"
  count  = local.use_pinecone ? 1 : 0

  index_name = var.name
  dimension  = var.pinecone.dimension
  metric     = var.pinecone.metric
  cloud      = var.pinecone.cloud
  region     = var.pinecone.region
}

# ---------------------------------------------------------------------------
# KMS (created when not supplied)
# ---------------------------------------------------------------------------

resource "aws_kms_key" "this" {
  count = var.kms_key_arn == null ? 1 : 0

  description             = "RAG stack encryption for ${var.name}"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = local.tags
}

resource "aws_kms_alias" "this" {
  count = var.kms_key_arn == null ? 1 : 0

  name          = "alias/${var.name}-rag"
  target_key_id = aws_kms_key.this[0].key_id
}

# ---------------------------------------------------------------------------
# Document bucket — versioned, KMS, public access blocked, TLS-only
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "documents" {
  bucket_prefix = "${var.name}-docs-"
  force_destroy = var.bucket_force_destroy

  tags = local.tags
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = local.kms_key_arn
    }

    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    id     = "expire-noncurrent"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = var.document_retention_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.documents]
}

data "aws_iam_policy_document" "bucket" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]

    resources = [
      aws_s3_bucket.documents.arn,
      "${aws_s3_bucket.documents.arn}/*",
    ]

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "documents" {
  bucket = aws_s3_bucket.documents.id
  policy = data.aws_iam_policy_document.bucket.json

  depends_on = [aws_s3_bucket_public_access_block.documents]
}

# ---------------------------------------------------------------------------
# Ingestion queue + DLQ
# ---------------------------------------------------------------------------

resource "aws_sqs_queue" "dlq" {
  name = "${var.name}-ingest-dlq"

  kms_master_key_id                 = local.kms_key_arn
  kms_data_key_reuse_period_seconds = 300
  message_retention_seconds         = 1209600 # 14 days to investigate failures

  tags = local.tags
}

resource "aws_sqs_queue" "ingest" {
  name = "${var.name}-ingest"

  kms_master_key_id                 = local.kms_key_arn
  kms_data_key_reuse_period_seconds = 300
  visibility_timeout_seconds        = var.queue_visibility_timeout
  message_retention_seconds         = 345600 # 4 days

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.queue_max_receive_count
  })

  tags = local.tags
}

resource "aws_sqs_queue_redrive_allow_policy" "dlq" {
  queue_url = aws_sqs_queue.dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.ingest.arn]
  })
}

# ---------------------------------------------------------------------------
# Guard: qdrant backend requires an API key
# ---------------------------------------------------------------------------

resource "terraform_data" "qdrant_api_key_guard" {
  count = local.use_qdrant ? 1 : 0

  lifecycle {
    precondition {
      condition     = var.qdrant.api_key != null
      error_message = "qdrant.api_key is required when vector_backend = \"qdrant\"."
    }
  }
}
