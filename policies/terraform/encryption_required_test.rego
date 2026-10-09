package tap.terraform.encryption_required_test

import rego.v1

import data.tap.terraform.encryption_required as policy

rc(rtype, after) := {
	"address": sprintf("%s.example", [rtype]),
	"type": rtype,
	"change": {"actions": ["create"], "after": after},
}

test_encrypted_rds_allowed if {
	count(policy.deny) == 0 with input as {"resource_changes": [rc("aws_db_instance", {"storage_encrypted": true})]}
}

test_unencrypted_rds_denied if {
	some msg in policy.deny with input as {"resource_changes": [rc("aws_db_instance", {"storage_encrypted": false})]}
	contains(msg, "storage_encrypted")
}

test_rds_cluster_missing_flag_denied if {
	count(policy.deny) > 0 with input as {"resource_changes": [rc("aws_rds_cluster", {})]}
}

test_unencrypted_ebs_denied if {
	count(policy.deny) > 0 with input as {"resource_changes": [rc("aws_ebs_volume", {"encrypted": false})]}
}

test_unencrypted_root_block_device_denied if {
	count(policy.deny) > 0 with input as {"resource_changes": [rc("aws_instance", {"root_block_device": [{"encrypted": false}]})]}
}

test_s3_without_sse_denied if {
	some msg in policy.deny with input as {"resource_changes": [rc("aws_s3_bucket", {"bucket": "data"})]}
	contains(msg, "server-side encryption")
}

test_s3_with_sse_resource_allowed if {
	count(policy.deny) == 0 with input as {"resource_changes": [
		rc("aws_s3_bucket", {"bucket": "data"}),
		rc("aws_s3_bucket_server_side_encryption_configuration", {"bucket": "data"}),
	]}
}

test_storage_account_http_denied if {
	some msg in policy.deny with input as {"resource_changes": [rc("azurerm_storage_account", {
		"https_traffic_only_enabled": false,
		"infrastructure_encryption_enabled": true,
	})]}
	contains(msg, "HTTPS-only")
}

test_storage_account_compliant_allowed if {
	count(policy.deny) == 0 with input as {"resource_changes": [rc("azurerm_storage_account", {
		"https_traffic_only_enabled": true,
		"infrastructure_encryption_enabled": true,
	})]}
}

test_managed_disk_without_des_denied if {
	count(policy.deny) > 0 with input as {"resource_changes": [rc("azurerm_managed_disk", {})]}
}
