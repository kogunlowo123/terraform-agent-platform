# Deny publicly accessible S3 buckets.
#
# Input: Terraform plan JSON (`terraform show -json plan.out`), evaluated over
# `resource_changes`. Consumed by the TAP Policy Service at plan time as a
# hard gate, and by CI via `opa test` / `opa eval`.
package tap.terraform.deny_public_s3

import rego.v1

public_acls := {"public-read", "public-read-write", "website"}

pab_settings := {
	"block_public_acls",
	"block_public_policy",
	"ignore_public_acls",
	"restrict_public_buckets",
}

# Resources being created or updated (never flag deletes).
managed(rc) if {
	some action in rc.change.actions
	action in {"create", "update"}
}

buckets contains rc if {
	some rc in input.resource_changes
	rc.type == "aws_s3_bucket"
	managed(rc)
}

pabs contains rc if {
	some rc in input.resource_changes
	rc.type == "aws_s3_bucket_public_access_block"
	managed(rc)
}

# --- public ACLs -------------------------------------------------------------

deny contains msg if {
	some rc in buckets
	rc.change.after.acl in public_acls
	msg := sprintf("S3 bucket %q uses public ACL %q", [rc.address, rc.change.after.acl])
}

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_s3_bucket_acl"
	managed(rc)
	rc.change.after.acl in public_acls
	msg := sprintf("S3 bucket ACL %q grants public access (%q)", [rc.address, rc.change.after.acl])
}

# --- public bucket policies ---------------------------------------------------

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_s3_bucket_policy"
	managed(rc)
	policy := json.unmarshal(rc.change.after.policy)
	some stmt in policy.Statement
	stmt.Effect == "Allow"
	is_public_principal(stmt.Principal)
	msg := sprintf("S3 bucket policy %q allows a public principal (*)", [rc.address])
}

is_public_principal(p) if p == "*"

is_public_principal(p) if p.AWS == "*"

is_public_principal(p) if {
	some v in p.AWS
	v == "*"
}

# --- missing or weakened public access block -----------------------------------

deny contains msg if {
	some rc in buckets
	not bucket_has_pab(rc)
	msg := sprintf(
		"S3 bucket %q has no aws_s3_bucket_public_access_block in this plan",
		[rc.address],
	)
}

deny contains msg if {
	some pab in pabs
	some setting in sort(pab_settings)
	object.get(pab.change.after, setting, false) != true
	msg := sprintf("public access block %q must set %s = true", [pab.address, setting])
}

bucket_has_pab(bucket_rc) if {
	some pab in pabs
	pab_references(pab, bucket_rc)
}

# Matched by name when both sides are known at plan time.
pab_references(pab, bucket_rc) if {
	pab.change.after.bucket == bucket_rc.change.after.bucket
}

# Bucket reference is computed (resolved at apply): assume it covers the bucket
# rather than produce a false positive; the weakened-settings rule still applies.
pab_references(pab, _) if {
	not pab.change.after.bucket
}
