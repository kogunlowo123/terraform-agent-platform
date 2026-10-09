package tap.ai.model_governance_test

import rego.v1

import data.tap.ai.model_governance as policy

config := {"ai": {"approved_models": ["gpt-4o", "claude-sonnet-4-5", "anthropic.claude-sonnet-4-5-v1:0"]}}

rc(rtype, addr, after) := {
	"address": addr,
	"type": rtype,
	"change": {"actions": ["create"], "after": after},
}

test_approved_azure_deployment_allowed if {
	count(policy.deny) == 0 with input as {"resource_changes": [rc(
		"azurerm_cognitive_deployment", "azurerm_cognitive_deployment.gpt",
		{"model": [{"name": "gpt-4o"}], "rai_policy_name": "default-filter"},
	)]}
		with data.tap.config as config
}

test_unapproved_model_denied if {
	some msg in policy.deny with input as {"resource_changes": [rc(
		"azurerm_cognitive_deployment", "azurerm_cognitive_deployment.rogue",
		{"model": [{"name": "experimental-llm-9000"}], "rai_policy_name": "default-filter"},
	)]}
		with data.tap.config as config
	contains(msg, "experimental-llm-9000")
}

test_azure_without_content_filter_denied if {
	some msg in policy.deny with input as {"resource_changes": [rc(
		"azurerm_cognitive_deployment", "azurerm_cognitive_deployment.gpt",
		{"model": [{"name": "gpt-4o"}], "rai_policy_name": ""},
	)]}
		with data.tap.config as config
	contains(msg, "content filter")
}

test_bedrock_without_logging_denied if {
	some msg in policy.deny with input as {"resource_changes": [rc(
		"aws_bedrockagent_agent", "aws_bedrockagent_agent.helper",
		{"foundation_model": "anthropic.claude-sonnet-4-5-v1:0"},
	)]}
		with data.tap.config as config
	contains(msg, "invocation_logging")
}

test_bedrock_with_logging_allowed if {
	count(policy.deny) == 0 with input as {"resource_changes": [
		rc(
			"aws_bedrockagent_agent", "aws_bedrockagent_agent.helper",
			{"foundation_model": "anthropic.claude-sonnet-4-5-v1:0"},
		),
		rc(
			"aws_bedrock_model_invocation_logging_configuration", "aws_bedrock_model_invocation_logging_configuration.this",
			{},
		),
	]}
		with data.tap.config as config
}

test_unapproved_bedrock_model_denied if {
	count(policy.deny) > 0 with input as {"resource_changes": [
		rc("aws_bedrockagent_agent", "aws_bedrockagent_agent.helper", {"foundation_model": "shadow-model"}),
		rc("aws_bedrock_model_invocation_logging_configuration", "logcfg", {}),
	]}
		with data.tap.config as config
}

test_public_cognitive_account_denied if {
	some msg in policy.deny with input as {"resource_changes": [rc(
		"azurerm_cognitive_account", "azurerm_cognitive_account.openai",
		{"public_network_access_enabled": true},
	)]}
		with data.tap.config as config
	contains(msg, "public network access")
}

test_private_cognitive_account_allowed if {
	count(policy.deny) == 0 with input as {"resource_changes": [rc(
		"azurerm_cognitive_account", "azurerm_cognitive_account.openai",
		{"public_network_access_enabled": false},
	)]}
		with data.tap.config as config
}

test_sagemaker_without_vpc_denied if {
	count(policy.deny) > 0 with input as {"resource_changes": [rc("aws_sagemaker_model", "aws_sagemaker_model.clf", {})]}
		with data.tap.config as config
}

test_vertex_without_network_is_advisory if {
	count(policy.deny) == 0 with input as {"resource_changes": [rc("google_vertex_ai_endpoint", "google_vertex_ai_endpoint.pred", {"network": ""})]}
		with data.tap.config as config
	count(policy.advisory) == 1 with input as {"resource_changes": [rc("google_vertex_ai_endpoint", "google_vertex_ai_endpoint.pred", {"network": ""})]}
		with data.tap.config as config
}
