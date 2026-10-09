package tap.terraform.instance_allowlist_test

import rego.v1

import data.tap.terraform.instance_allowlist as policy

config := {"instance_allowlist": {
	"dev": ["t3.micro", "t3.small"],
	"prod": ["m6i.large", "m6i.xlarge"],
}}

plan(env, itype) := {
	"workspace": {"environment": env},
	"resource_changes": [{
		"address": "aws_instance.app",
		"type": "aws_instance",
		"change": {"actions": ["create"], "after": {"instance_type": itype}},
	}],
}

test_allowed_type_passes if {
	count(policy.deny) == 0 with input as plan("prod", "m6i.large")
		with data.tap.config as config
}

test_disallowed_type_denied if {
	some msg in policy.deny with input as plan("prod", "p4d.24xlarge")
		with data.tap.config as config
	contains(msg, "p4d.24xlarge")
}

test_allowlist_is_per_environment if {
	# t3.micro is fine in dev but not in prod
	count(policy.deny) == 0 with input as plan("dev", "t3.micro")
		with data.tap.config as config
	count(policy.deny) > 0 with input as plan("prod", "t3.micro")
		with data.tap.config as config
}

test_launch_template_checked if {
	count(policy.deny) > 0 with input as {
		"workspace": {"environment": "dev"},
		"resource_changes": [{
			"address": "aws_launch_template.app",
			"type": "aws_launch_template",
			"change": {"actions": ["create"], "after": {"instance_type": "m7i.48xlarge"}},
		}],
	}
		with data.tap.config as config
}

test_missing_allowlist_is_advisory_not_deny if {
	count(policy.deny) == 0 with input as plan("staging", "t3.micro")
		with data.tap.config as config
	count(policy.advisory) == 1 with input as plan("staging", "t3.micro")
		with data.tap.config as config
}

test_defaults_to_dev_environment if {
	count(policy.deny) > 0 with input as {"resource_changes": [{
		"address": "aws_instance.app",
		"type": "aws_instance",
		"change": {"actions": ["create"], "after": {"instance_type": "m6i.large"}},
	}]}
		with data.tap.config as config
}
