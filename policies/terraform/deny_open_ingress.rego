# Deny world-open security group ingress.
#
# Rules:
#   * 0.0.0.0/0 (or ::/0) ingress is only permitted on ports 80 and 443.
#   * Ports 22 (SSH) and 3389 (RDP) are ALWAYS denied from 0.0.0.0/0,
#     with a distinct message so the platform can mark them non-overridable.
#
# Input: Terraform plan JSON (`resource_changes`). Covers inline
# aws_security_group ingress blocks, aws_security_group_rule, and
# aws_vpc_security_group_ingress_rule.
package tap.terraform.deny_open_ingress

import rego.v1

open_cidrs := {"0.0.0.0/0", "::/0"}

admin_ports := {22, 3389}

allowed_public_ports := {80, 443}

managed(rc) if {
	some action in rc.change.actions
	action in {"create", "update"}
}

# --- collect world-open ingress rules into a normalized set ---------------------

open_ingress contains rule if {
	some rc in input.resource_changes
	rc.type == "aws_security_group"
	managed(rc)
	some ing in object.get(rc.change.after, "ingress", [])
	rule_open(ing.cidr_blocks, object.get(ing, "ipv6_cidr_blocks", []))
	rule := normalize(rc.address, ing.from_port, ing.to_port, ing.protocol)
}

open_ingress contains rule if {
	some rc in input.resource_changes
	rc.type == "aws_security_group_rule"
	managed(rc)
	rc.change.after.type == "ingress"
	rule_open(
		object.get(rc.change.after, "cidr_blocks", []),
		object.get(rc.change.after, "ipv6_cidr_blocks", []),
	)
	rule := normalize(
		rc.address,
		rc.change.after.from_port,
		rc.change.after.to_port,
		rc.change.after.protocol,
	)
}

open_ingress contains rule if {
	some rc in input.resource_changes
	rc.type == "aws_vpc_security_group_ingress_rule"
	managed(rc)
	cidrs := array.concat(
		[c | c := object.get(rc.change.after, "cidr_ipv4", ""); c != ""],
		[c | c := object.get(rc.change.after, "cidr_ipv6", ""); c != ""],
	)
	rule_open(cidrs, [])
	rule := normalize(
		rc.address,
		object.get(rc.change.after, "from_port", 0),
		object.get(rc.change.after, "to_port", 65535),
		object.get(rc.change.after, "ip_protocol", "-1"),
	)
}

rule_open(v4, v6) if {
	some c in array.concat([x | some x in v4], [x | some x in v6])
	c in open_cidrs
}

# Protocol "-1" / "all" means every port regardless of declared range.
normalize(addr, _, _, proto) := {"address": addr, "from": 0, "to": 65535, "protocol": proto} if {
	proto in {"-1", "all"}
}

normalize(addr, from, to, proto) := {"address": addr, "from": from, "to": to, "protocol": proto} if {
	not proto in {"-1", "all"}
}

# --- decisions -------------------------------------------------------------------

# Non-overridable: SSH/RDP open to the world.
deny contains msg if {
	some rule in open_ingress
	some port in sort(admin_ports)
	rule.from <= port
	port <= rule.to
	msg := sprintf(
		"%s: ingress from 0.0.0.0/0 to administrative port %d is always denied",
		[rule.address, port],
	)
}

# Any other world-open port outside 80/443.
deny contains msg if {
	some rule in open_ingress
	not web_only(rule)
	not covers_admin_port(rule)
	msg := sprintf(
		"%s: ingress from 0.0.0.0/0 on ports %d-%d; only 80 and 443 may be world-open",
		[rule.address, rule.from, rule.to],
	)
}

web_only(rule) if {
	rule.from == rule.to
	rule.from in allowed_public_ports
}

covers_admin_port(rule) if {
	some port in admin_ports
	rule.from <= port
	port <= rule.to
}
