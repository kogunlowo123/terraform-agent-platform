package tap.kubernetes.pod_security_test

import rego.v1

import data.tap.kubernetes.pod_security as policy

good_container := {
	"name": "app",
	"image": "ghcr.io/tap/app:1.0.0",
	"securityContext": {"runAsNonRoot": true, "allowPrivilegeEscalation": false},
}

pod(spec) := {"kind": "Pod", "metadata": {"name": "test"}, "spec": spec}

deployment(spec) := {
	"kind": "Deployment",
	"metadata": {"name": "test"},
	"spec": {"template": {"spec": spec}},
}

test_compliant_pod_allowed if {
	count(policy.deny) == 0 with input as pod({"containers": [good_container]})
}

test_privileged_container_denied if {
	some msg in policy.deny with input as pod({"containers": [object.union(
		good_container,
		{"securityContext": {"privileged": true, "runAsNonRoot": true}},
	)]})
	contains(msg, "privileged")
}

test_privilege_escalation_denied if {
	count(policy.deny) > 0 with input as pod({"containers": [object.union(
		good_container,
		{"securityContext": {"runAsNonRoot": true, "allowPrivilegeEscalation": true}},
	)]})
}

test_hostpath_volume_denied if {
	some msg in policy.deny with input as pod({
		"containers": [good_container],
		"volumes": [{"name": "host", "hostPath": {"path": "/var/run/docker.sock"}}],
	})
	contains(msg, "hostPath")
}

test_missing_run_as_non_root_denied if {
	some msg in policy.deny with input as pod({"containers": [{"name": "app", "image": "x"}]})
	contains(msg, "runAsNonRoot")
}

test_pod_level_run_as_non_root_satisfies if {
	count(policy.deny) == 0 with input as pod({
		"securityContext": {"runAsNonRoot": true},
		"containers": [{
			"name": "app", "image": "x",
			"securityContext": {"allowPrivilegeEscalation": false},
		}],
	})
}

test_container_override_of_pod_setting_denied if {
	count(policy.deny) > 0 with input as pod({
		"securityContext": {"runAsNonRoot": true},
		"containers": [{
			"name": "app", "image": "x",
			"securityContext": {"runAsNonRoot": false},
		}],
	})
}

test_deployment_template_checked if {
	count(policy.deny) > 0 with input as deployment({"containers": [{"name": "app", "image": "x"}]})
}

test_init_containers_checked if {
	count(policy.deny) > 0 with input as pod({
		"containers": [good_container],
		"initContainers": [{"name": "init", "image": "x", "securityContext": {"privileged": true, "runAsNonRoot": true}}],
	})
}
