variable "name" {
  description = "Name prefix for all Bedrock resources (lowercase; also used for the OpenSearch collection)."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,27}$", var.name))
    error_message = "name must be 3-28 lowercase alphanumeric/hyphen characters starting with a letter (OpenSearch Serverless limit)."
  }
}

variable "agent_foundation_model" {
  description = "Foundation model ID for the Bedrock agent (e.g. \"anthropic.claude-3-5-sonnet-20241022-v2:0\")."
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}

variable "agent_instruction" {
  description = "System instruction for the Bedrock agent (min 40 characters per API requirement)."
  type        = string
  default     = "You are a TAP infrastructure assistant. Answer questions using the attached knowledge base and never fabricate resource identifiers."

  validation {
    condition     = length(var.agent_instruction) >= 40
    error_message = "agent_instruction must be at least 40 characters."
  }
}

variable "agent_idle_session_ttl" {
  description = "Agent idle session TTL in seconds."
  type        = number
  default     = 600
}

variable "embedding_model_arn" {
  description = "Embedding model ARN for the knowledge base (e.g. arn:aws:bedrock:<region>::foundation-model/amazon.titan-embed-text-v2:0)."
  type        = string
}

variable "vector_index_name" {
  description = "Name of the vector index inside the OpenSearch Serverless collection. The index itself must be created out-of-band (TAP ingestion job) before KB sync."
  type        = string
  default     = "tap-kb-index"
}

variable "provisioned_throughput" {
  description = "Optional provisioned throughput purchase. commitment one of: none (null commitment), one_month, six_months."
  type = object({
    enabled             = optional(bool, false)
    model_arn           = optional(string)
    model_units         = optional(number, 1)
    commitment_duration = optional(string) # null = no commitment; "OneMonth" | "SixMonths"
  })
  default = {}

  validation {
    condition = (
      var.provisioned_throughput.commitment_duration == null ||
      contains(["OneMonth", "SixMonths"], coalesce(var.provisioned_throughput.commitment_duration, "OneMonth"))
    )
    error_message = "commitment_duration must be null, OneMonth, or SixMonths."
  }
}

variable "enable_invocation_logging" {
  description = "Enable account-level Bedrock model invocation logging to CloudWatch. NOTE: this is an account singleton — enable it in exactly one workspace per account/region."
  type        = bool
  default     = true
}

variable "invocation_log_retention_days" {
  description = "CloudWatch retention for invocation logs."
  type        = number
  default     = 90
}

variable "logs_kms_key_arn" {
  description = "Optional KMS key for the invocation log group."
  type        = string
  default     = null
}

variable "guardrail_blocked_input_message" {
  description = "Message returned when a prompt is blocked by the guardrail."
  type        = string
  default     = "This request was blocked by TAP content policy."
}

variable "guardrail_blocked_output_message" {
  description = "Message returned when a model response is blocked by the guardrail."
  type        = string
  default     = "The response was blocked by TAP content policy."
}

variable "guardrail_content_filters" {
  description = "Content filters: type => { input_strength, output_strength } (NONE|LOW|MEDIUM|HIGH)."
  type = map(object({
    input_strength  = string
    output_strength = string
  }))
  default = {
    HATE          = { input_strength = "HIGH", output_strength = "HIGH" }
    INSULTS       = { input_strength = "HIGH", output_strength = "HIGH" }
    SEXUAL        = { input_strength = "HIGH", output_strength = "HIGH" }
    VIOLENCE      = { input_strength = "HIGH", output_strength = "HIGH" }
    MISCONDUCT    = { input_strength = "HIGH", output_strength = "HIGH" }
    PROMPT_ATTACK = { input_strength = "HIGH", output_strength = "NONE" }
  }

  validation {
    condition = alltrue([
      for f in values(var.guardrail_content_filters) :
      contains(["NONE", "LOW", "MEDIUM", "HIGH"], f.input_strength) &&
      contains(["NONE", "LOW", "MEDIUM", "HIGH"], f.output_strength)
    ])
    error_message = "Filter strengths must be NONE, LOW, MEDIUM, or HIGH."
  }
}

variable "guardrail_denied_topics" {
  description = "Denied topics: name => definition sentence."
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default     = {}
}
