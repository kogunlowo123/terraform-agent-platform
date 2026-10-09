package tap.terraform.require_tags_test

import rego.v1

import data.tap.terraform.require_tags as policy

full_tags := {
	"owner": "platform-team",
	"cost_center": "cc-1001",
	"environment": "prod",
	"data_class": "internal",
}

rc(rtype, after) := {
	"address": sprintf("%s.example", [rtype]),
	"type": rtype,
	"change": {"actions": ["create"], "after": after},
}

test_fully_tagged_instance_allowed if {
	count(policy.deny) == 0 with input as {"resource_changes": [rc("aws_instance", {"tags": full_tags})]}
}

test_missing_tag_denied if {
	some msg in policy.deny with input as {"resource_changes": [rc("aws_instance", {"tags": object.remove(full_tags, {"cost_center"})})]}
	contains(msg, "cost_center")
}

test_empty_tag_denied if {
	some msg in policy.deny with input as {"resource_changes": [rc("aws_s3_bucket", {"tags": object.union(full_tags, {"owner": "  "})})]}
	contains(msg, "\"owner\" is empty")
}

test_tags_all_satisfies_requirement if {
	count(policy.deny) == 0 with input as {"resource_changes": [rc("aws_db_instance", {"tags": {}, "tags_all": full_tags})]}
}

test_gcp_labels_checked if {
	some msg in policy.deny with input as {"resource_changes": [rc("google_compute_instance", {"labels": object.remove(full_tags, {"data_class"})})]}
	contains(msg, "data_class")
}

test_untaggable_type_ignored if {
	count(policy.deny) == 0 with input as {"resource_changes": [rc("aws_iam_role_policy_attachment", {})]}
}

test_extra_types_from_config if {
	count(policy.deny) > 0 with input as {"resource_changes": [rc("aws_sqs_queue", {"tags": {}})]}
		with data.tap.config as {"taggable_types": ["aws_sqs_queue"]}
}
