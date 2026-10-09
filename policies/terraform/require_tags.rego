# Require the TAP mandatory tag set on all taggable resources.
#
# Input: Terraform plan JSON (`resource_changes`). GCP resources are checked
# for `labels`; AWS/Azure for `tags` (falling back to `tags_all` on AWS).
package tap.terraform.require_tags

import rego.v1

required_tags := {"owner", "cost_center", "environment", "data_class"}

# Representative taggable types; extend via data.tap.config.taggable_types.
default_taggable_types := {
	"aws_instance",
	"aws_s3_bucket",
	"aws_db_instance",
	"aws_ebs_volume",
	"aws_eks_cluster",
	"aws_lb",
	"aws_vpc",
	"aws_lambda_function",
	"aws_dynamodb_table",
	"azurerm_resource_group",
	"azurerm_storage_account",
	"azurerm_linux_virtual_machine",
	"azurerm_windows_virtual_machine",
	"azurerm_kubernetes_cluster",
	"google_compute_instance",
	"google_storage_bucket",
	"google_container_cluster",
}

taggable_types := default_taggable_types | extra_types

extra_types := {t | some t in object.get(data.tap.config, "taggable_types", [])}

managed(rc) if {
	some action in rc.change.actions
	action in {"create", "update"}
}

taggable contains rc if {
	some rc in input.resource_changes
	rc.type in taggable_types
	managed(rc)
}

tags_of(rc) := rc.change.after.labels if {
	startswith(rc.type, "google_")
} else := object.union(
	object.get(rc.change.after, "tags_all", {}),
	object.get(rc.change.after, "tags", {}),
)

deny contains msg if {
	some rc in taggable
	some tag in sort(required_tags)
	not tags_of(rc)[tag]
	msg := sprintf("%s: missing required tag %q", [rc.address, tag])
}

deny contains msg if {
	some rc in taggable
	some tag in sort(required_tags)
	trim_space(tags_of(rc)[tag]) == ""
	msg := sprintf("%s: required tag %q is empty", [rc.address, tag])
}
