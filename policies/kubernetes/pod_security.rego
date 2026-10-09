# Baseline pod security for TAP-managed Kubernetes workloads.
#
# Input: a single Kubernetes manifest (Pod or a workload controller that
# embeds a pod template). Used at admission (via the OPA sidecar) and in CI
# against rendered manifests.
#
# Rules: no privileged containers, no hostPath volumes, runAsNonRoot required.
package tap.kubernetes.pod_security

import rego.v1

controller_kinds := {"Deployment", "StatefulSet", "DaemonSet", "Job", "ReplicaSet"}

pod_spec := input.spec if input.kind == "Pod"

pod_spec := input.spec.template.spec if input.kind in controller_kinds

pod_spec := input.spec.jobTemplate.spec.template.spec if input.kind == "CronJob"

name := object.get(input, ["metadata", "name"], "unknown")

containers contains c if some c in object.get(pod_spec, "containers", [])

containers contains c if some c in object.get(pod_spec, "initContainers", [])

# --- privileged ---------------------------------------------------------------

deny contains msg if {
	some c in containers
	object.get(c, ["securityContext", "privileged"], false) == true
	msg := sprintf("%s/%s: container %q must not run privileged", [input.kind, name, c.name])
}

deny contains msg if {
	some c in containers
	object.get(c, ["securityContext", "allowPrivilegeEscalation"], false) == true
	msg := sprintf("%s/%s: container %q must not allow privilege escalation", [input.kind, name, c.name])
}

# --- hostPath -----------------------------------------------------------------

deny contains msg if {
	some v in object.get(pod_spec, "volumes", [])
	v.hostPath
	msg := sprintf("%s/%s: hostPath volume %q is not allowed", [input.kind, name, v.name])
}

# --- runAsNonRoot ----------------------------------------------------------------

deny contains msg if {
	some c in containers
	not run_as_non_root(c)
	msg := sprintf("%s/%s: container %q must set runAsNonRoot: true (container or pod securityContext)", [input.kind, name, c.name])
}

run_as_non_root(c) if c.securityContext.runAsNonRoot == true

# Pod-level setting applies when the container does not override it.
run_as_non_root(c) if {
	not container_overrides_run_as(c)
	pod_spec.securityContext.runAsNonRoot == true
}

container_overrides_run_as(c) if {
	is_boolean(object.get(c, ["securityContext", "runAsNonRoot"], null))
}
