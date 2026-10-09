# Deny unencrypted storage: RDS instances/clusters, EBS volumes, S3 buckets,
# and Azure storage accounts.
#
# Input: Terraform plan JSON (`resource_changes`).
package tap.terraform.encryption_required

import rego.v1

managed(rc) if {
	some action in rc.change.actions
	action in {"create", "update"}
}

# --- RDS ----------------------------------------------------------------------

deny contains msg if {
	some rc in input.resource_changes
	rc.type in {"aws_db_instance", "aws_rds_cluster"}
	managed(rc)
	not rc.change.after.storage_encrypted == true
	msg := sprintf("%s: storage_encrypted must be true", [rc.address])
}

# --- EBS ----------------------------------------------------------------------

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_ebs_volume"
	managed(rc)
	not rc.change.after.encrypted == true
	msg := sprintf("%s: EBS volume must set encrypted = true", [rc.address])
}

deny contains msg if {
	some rc in input.resource_changes
	rc.type in {"aws_instance", "aws_launch_template"}
	managed(rc)
	some bd in object.get(rc.change.after, "root_block_device", [])
	bd.encrypted == false
	msg := sprintf("%s: root block device must be encrypted", [rc.address])
}

# --- S3 -------------------------------------------------------------------------

# Buckets must have server-side encryption: either an inline (legacy)
# server_side_encryption_configuration or a companion
# aws_s3_bucket_server_side_encryption_configuration resource in the plan.
deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_s3_bucket"
	managed(rc)
	count(object.get(rc.change.after, "server_side_encryption_configuration", [])) == 0
	not sse_resource_in_plan
	msg := sprintf("%s: no server-side encryption configuration in plan", [rc.address])
}

sse_resource_in_plan if {
	some rc in input.resource_changes
	rc.type == "aws_s3_bucket_server_side_encryption_configuration"
	managed(rc)
}

# --- Azure storage accounts ------------------------------------------------------

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "azurerm_storage_account"
	managed(rc)
	object.get(rc.change.after, "https_traffic_only_enabled", object.get(rc.change.after, "enable_https_traffic_only", false)) != true
	msg := sprintf("%s: HTTPS-only traffic must be enabled", [rc.address])
}

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "azurerm_storage_account"
	managed(rc)
	object.get(rc.change.after, "infrastructure_encryption_enabled", false) != true
	msg := sprintf("%s: infrastructure_encryption_enabled must be true", [rc.address])
}

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "azurerm_managed_disk"
	managed(rc)
	object.get(rc.change.after, "disk_encryption_set_id", "") == ""
	object.get(rc.change.after, "encryption_settings", []) == []
	msg := sprintf("%s: managed disk requires a disk encryption set or encryption settings", [rc.address])
}
