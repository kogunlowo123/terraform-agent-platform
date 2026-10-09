package tap.terraform.deny_public_s3_test

import rego.v1

import data.tap.terraform.deny_public_s3 as policy

plan(changes) := {"resource_changes": changes}

bucket(addr, after) := {
	"address": addr,
	"type": "aws_s3_bucket",
	"change": {"actions": ["create"], "after": after},
}

good_pab(bucket_name) := {
	"address": sprintf("aws_s3_bucket_public_access_block.%s", [bucket_name]),
	"type": "aws_s3_bucket_public_access_block",
	"change": {"actions": ["create"], "after": {
		"bucket": bucket_name,
		"block_public_acls": true,
		"block_public_policy": true,
		"ignore_public_acls": true,
		"restrict_public_buckets": true,
	}},
}

test_private_bucket_with_pab_allowed if {
	count(policy.deny) == 0 with input as plan([
		bucket("aws_s3_bucket.logs", {"bucket": "logs", "acl": "private"}),
		good_pab("logs"),
	])
}

test_public_acl_denied if {
	some msg in policy.deny with input as plan([
		bucket("aws_s3_bucket.site", {"bucket": "site", "acl": "public-read"}),
		good_pab("site"),
	])
	contains(msg, "public ACL")
}

test_public_bucket_acl_resource_denied if {
	count(policy.deny) > 0 with input as plan([{
		"address": "aws_s3_bucket_acl.site",
		"type": "aws_s3_bucket_acl",
		"change": {"actions": ["create"], "after": {"acl": "public-read-write"}},
	}])
}

test_public_bucket_policy_denied if {
	count(policy.deny) > 0 with input as plan([{
		"address": "aws_s3_bucket_policy.site",
		"type": "aws_s3_bucket_policy",
		"change": {"actions": ["create"], "after": {"policy": json.marshal({"Statement": [{
			"Effect": "Allow",
			"Principal": "*",
			"Action": "s3:GetObject",
			"Resource": "*",
		}]})}},
	}])
}

test_missing_public_access_block_denied if {
	some msg in policy.deny with input as plan([bucket("aws_s3_bucket.data", {"bucket": "data", "acl": "private"})])
	contains(msg, "no aws_s3_bucket_public_access_block")
}

test_weak_public_access_block_denied if {
	pab := {
		"address": "aws_s3_bucket_public_access_block.data",
		"type": "aws_s3_bucket_public_access_block",
		"change": {"actions": ["create"], "after": {
			"bucket": "data",
			"block_public_acls": true,
			"block_public_policy": false,
			"ignore_public_acls": true,
			"restrict_public_buckets": true,
		}},
	}
	some msg in policy.deny with input as plan([
		bucket("aws_s3_bucket.data", {"bucket": "data", "acl": "private"}),
		pab,
	])
	contains(msg, "block_public_policy")
}

test_delete_not_flagged if {
	count(policy.deny) == 0 with input as plan([{
		"address": "aws_s3_bucket.old",
		"type": "aws_s3_bucket",
		"change": {"actions": ["delete"], "after": null},
	}])
}
