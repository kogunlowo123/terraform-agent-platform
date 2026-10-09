package tap.terraform.deny_open_ingress_test

import rego.v1

import data.tap.terraform.deny_open_ingress as policy

sg(ingress) := {"resource_changes": [{
	"address": "aws_security_group.web",
	"type": "aws_security_group",
	"change": {"actions": ["create"], "after": {"ingress": ingress}},
}]}

test_https_from_world_allowed if {
	count(policy.deny) == 0 with input as sg([{
		"from_port": 443, "to_port": 443, "protocol": "tcp",
		"cidr_blocks": ["0.0.0.0/0"],
	}])
}

test_http_from_world_allowed if {
	count(policy.deny) == 0 with input as sg([{
		"from_port": 80, "to_port": 80, "protocol": "tcp",
		"cidr_blocks": ["0.0.0.0/0"],
	}])
}

test_ssh_from_world_denied if {
	some msg in policy.deny with input as sg([{
		"from_port": 22, "to_port": 22, "protocol": "tcp",
		"cidr_blocks": ["0.0.0.0/0"],
	}])
	contains(msg, "administrative port 22")
}

test_rdp_from_world_denied if {
	some msg in policy.deny with input as sg([{
		"from_port": 3389, "to_port": 3389, "protocol": "tcp",
		"cidr_blocks": ["0.0.0.0/0"],
	}])
	contains(msg, "administrative port 3389")
}

test_arbitrary_port_from_world_denied if {
	some msg in policy.deny with input as sg([{
		"from_port": 8080, "to_port": 8080, "protocol": "tcp",
		"cidr_blocks": ["0.0.0.0/0"],
	}])
	contains(msg, "only 80 and 443")
}

test_all_protocols_from_world_denied if {
	count(policy.deny) > 0 with input as sg([{
		"from_port": 0, "to_port": 0, "protocol": "-1",
		"cidr_blocks": ["0.0.0.0/0"],
	}])
}

test_range_covering_ssh_denied if {
	some msg in policy.deny with input as sg([{
		"from_port": 20, "to_port": 25, "protocol": "tcp",
		"cidr_blocks": ["0.0.0.0/0"],
	}])
	contains(msg, "administrative port 22")
}

test_internal_cidr_allowed if {
	count(policy.deny) == 0 with input as sg([{
		"from_port": 22, "to_port": 22, "protocol": "tcp",
		"cidr_blocks": ["10.0.0.0/8"],
	}])
}

test_ipv6_world_open_denied if {
	count(policy.deny) > 0 with input as sg([{
		"from_port": 9000, "to_port": 9000, "protocol": "tcp",
		"cidr_blocks": [], "ipv6_cidr_blocks": ["::/0"],
	}])
}

test_sg_rule_resource_denied if {
	count(policy.deny) > 0 with input as {"resource_changes": [{
		"address": "aws_security_group_rule.open",
		"type": "aws_security_group_rule",
		"change": {"actions": ["create"], "after": {
			"type": "ingress", "from_port": 5432, "to_port": 5432,
			"protocol": "tcp", "cidr_blocks": ["0.0.0.0/0"],
		}},
	}]}
}

test_vpc_ingress_rule_resource_denied if {
	count(policy.deny) > 0 with input as {"resource_changes": [{
		"address": "aws_vpc_security_group_ingress_rule.open",
		"type": "aws_vpc_security_group_ingress_rule",
		"change": {"actions": ["create"], "after": {
			"cidr_ipv4": "0.0.0.0/0", "from_port": 22, "to_port": 22,
			"ip_protocol": "tcp",
		}},
	}]}
}
