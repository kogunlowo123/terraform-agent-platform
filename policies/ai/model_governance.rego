# AI deployment governance.
#
# Input: Terraform plan JSON (`resource_changes`) for AI infrastructure
# (Azure OpenAI / Bedrock / SageMaker / Vertex), evaluated at plan time.
#
# Rules:
#   * Only models on the approved list (data.tap.config.ai.approved_models)
#     may be deployed.
#   * Azure OpenAI deployments must attach a content filter (RAI policy).
#   * Bedrock usage requires model invocation logging in the same plan.
#   * AI endpoints must not be publicly reachable.
package tap.ai.model_governance

import rego.v1

default_approved_models := [
	"claude-sonnet-4-5",
	"claude-haiku-4-5",
	"gpt-4o",
	"gpt-4o-mini",
	"anthropic.claude-sonnet-4-5-v1:0",
	"amazon.titan-embed-text-v2:0",
]

approved_models := object.get(data.tap.config, ["ai", "approved_models"], default_approved_models)

managed(rc) if {
	some action in rc.change.actions
	action in {"create", "update"}
}

# --- approved model list ---------------------------------------------------------

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "azurerm_cognitive_deployment"
	managed(rc)
	some model in rc.change.after.model
	not model.name in approved_models
	msg := sprintf("%s: model %q is not on the approved model list", [rc.address, model.name])
}

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_bedrockagent_agent"
	managed(rc)
	not rc.change.after.foundation_model in approved_models
	msg := sprintf(
		"%s: foundation model %q is not on the approved model list",
		[rc.address, rc.change.after.foundation_model],
	)
}

# --- Azure: content filter required ------------------------------------------------

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "azurerm_cognitive_deployment"
	managed(rc)
	trim_space(object.get(rc.change.after, "rai_policy_name", "")) == ""
	msg := sprintf("%s: Azure OpenAI deployment requires a content filter (rai_policy_name)", [rc.address])
}

# --- Bedrock: invocation logging required --------------------------------------------

bedrock_in_plan if {
	some rc in input.resource_changes
	startswith(rc.type, "aws_bedrock")
	rc.type != "aws_bedrock_model_invocation_logging_configuration"
	managed(rc)
}

invocation_logging_in_plan if {
	some rc in input.resource_changes
	rc.type == "aws_bedrock_model_invocation_logging_configuration"
	managed(rc)
}

deny contains msg if {
	bedrock_in_plan
	not invocation_logging_in_plan
	msg := "Bedrock resources require aws_bedrock_model_invocation_logging_configuration in the same plan"
}

# --- no public endpoints -------------------------------------------------------------

deny contains msg if {
	some rc in input.resource_changes
	rc.type in {"azurerm_cognitive_account", "azurerm_ai_services"}
	managed(rc)
	object.get(rc.change.after, "public_network_access_enabled", true) == true
	msg := sprintf("%s: AI endpoint must disable public network access", [rc.address])
}

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_sagemaker_model"
	managed(rc)
	count(object.get(rc.change.after, "vpc_config", [])) == 0
	msg := sprintf("%s: SageMaker model must run inside a VPC (vpc_config)", [rc.address])
}

advisory contains msg if {
	some rc in input.resource_changes
	rc.type == "google_vertex_ai_endpoint"
	managed(rc)
	trim_space(object.get(rc.change.after, "network", "")) == ""
	msg := sprintf("%s: Vertex AI endpoint has no VPC network binding; prefer private service connect", [rc.address])
}
