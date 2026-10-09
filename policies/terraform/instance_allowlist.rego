# Per-environment compute instance type allowlist, data-driven via
# `data.tap.config.instance_allowlist` (shipped in the policy bundle's data.json):
#
#   {"instance_allowlist": {
#     "dev":  ["t3.micro", "t3.small"],
#     "prod": ["m6i.large", "m6i.xlarge", "r6i.large"]
#   }}
#
# Input: Terraform plan JSON plus TAP run context:
#   {"workspace": {"environment": "prod"}, "resource_changes": [...]}
package tap.terraform.instance_allowlist

import rego.v1

instance_types := {"aws_instance", "aws_launch_template"}

env := object.get(input, ["workspace", "environment"], "dev")

allowlist := object.get(data.tap.config, ["instance_allowlist", env], [])

managed(rc) if {
	some action in rc.change.actions
	action in {"create", "update"}
}

instances contains rc if {
	some rc in input.resource_changes
	rc.type in instance_types
	managed(rc)
}

deny contains msg if {
	count(allowlist) > 0
	some rc in instances
	itype := rc.change.after.instance_type
	not itype in allowlist
	msg := sprintf(
		"%s: instance type %q is not in the %q environment allowlist %v",
		[rc.address, itype, env, allowlist],
	)
}

# No allowlist configured for this environment: advise rather than block,
# so new environments are not bricked by missing bundle data.
advisory contains msg if {
	count(allowlist) == 0
	count(instances) > 0
	msg := sprintf(
		"no instance allowlist configured for environment %q; add data.tap.config.instance_allowlist.%s",
		[env, env],
	)
}
