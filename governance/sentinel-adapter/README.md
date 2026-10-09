# Sentinel -> Rego Adapter

Migration guide for teams moving Sentinel policies (Terraform Cloud /
Enterprise) onto TAP's OPA-native policy engine. TAP does not execute
Sentinel; this adapter maps Sentinel concepts to equivalent Rego so policies
can be ported mechanically and then idiomatically.

## Conceptual mapping

| Sentinel concept | TAP / OPA equivalent |
|---|---|
| `tfplan/v2` import | Terraform plan JSON as `input` (`input.resource_changes`) |
| `tfconfig/v2` import | `terraform show -json` configuration section (`input.configuration`) |
| `tfstate/v2` import | prior state in plan JSON (`rc.change.before`) |
| `tfrun` import | TAP run context (`input.workspace`, `input.cost`) |
| Policy set (`sentinel.hcl`) | Bundle manifest [`../bundles/bundle.yaml`](../bundles/bundle.yaml) |
| Enforcement level `advisory` | bundle `stage: advisory` / `advisory contains msg` |
| Enforcement level `soft-mandatory` | bundle `stage: soft` / `soft_fail contains msg` |
| Enforcement level `hard-mandatory` | bundle `stage: hard` / `deny contains msg` |
| `main = rule { ... }` | `deny contains msg if { ... }` (inverted: Rego states the violation) |
| Mocks (`sentinel test`) | `_test.rego` + `with input as` / `with data.x as` |

> The key inversion: Sentinel's `main` rule states what must be TRUE for the
> plan to pass; Rego deny rules state what makes it FAIL. Port the negation,
> not the rule.

## Idiom migration table

| Sentinel idiom | Rego (OPA >= 0.60, `import rego.v1`) |
|---|---|
| `import "tfplan/v2" as tfplan` | (none — plan JSON is `input`) |
| `tfplan.resource_changes` | `input.resource_changes` |
| `filter tfplan.resource_changes as _, rc { rc.type is "aws_instance" }` | `instances := [rc \| some rc in input.resource_changes; rc.type == "aws_instance"]` |
| `rc.change.actions contains "create"` | `"create" in rc.change.actions` |
| `rc.change.after.acl is "private"` | `rc.change.after.acl == "private"` |
| `all instances as _, i { i.instance_type in allowed }` | `every i in instances { i.instance_type in allowed }` |
| `any buckets as _, b { b.acl is "public-read" }` | `some b in buckets; b.acl == "public-read"` |
| `if x else y` expressions | `v := x if cond` + `v := y if not cond`, or `object.get(...)` for defaults |
| `strings.has_prefix(t, "aws_")` | `startswith(t, "aws_")` |
| `length(x)` | `count(x)` |
| `param allowed_types default ["t3.micro"]` | `object.get(data.tap.config, "allowed_types", ["t3.micro"])` |
| `print(...)` debugging | `print(...)` (same built-in) |
| `rule { ... } else { ... }` | separate `deny contains msg if { ... }` rules |
| `sentinel apply -trace` | `opa eval --explain notes` |
| `sentinel test` with `mock-tfplan.sentinel` | `opa test` with inline test input objects |

## Porting workflow

1. Classify the Sentinel policy's enforcement level; pick the matching TAP
   decision rule and bundle stage.
2. Translate filters to comprehensions and `main` to inverted `deny` rules
   using the table above.
3. Move policy parameters into `data.tap.config` (bundle manifest `config`).
4. Recreate each Sentinel mock as a Rego test input; port every test case.
5. Land as `advisory`, compare denial rates against the legacy Sentinel run
   history, then promote per the lifecycle in [`../README.md`](../README.md).

## Worked example

Sentinel:

```python
import "tfplan/v2" as tfplan

ebs = filter tfplan.resource_changes as _, rc {
    rc.type is "aws_ebs_volume" and rc.change.actions contains "create"
}

main = rule {
    all ebs as _, v { v.change.after.encrypted is true }
}
```

Rego ([`policies/terraform/encryption_required.rego`](../../policies/terraform/encryption_required.rego)):

```rego
package tap.terraform.encryption_required

import rego.v1

deny contains msg if {
    some rc in input.resource_changes
    rc.type == "aws_ebs_volume"
    "create" in rc.change.actions
    not rc.change.after.encrypted == true
    msg := sprintf("%s: EBS volume must set encrypted = true", [rc.address])
}
```

## Not portable

* Sentinel's `http` import for live lookups — replace with bundle data or the
  Policy Service's data refresh (policies must stay deterministic).
* Time-of-evaluation rules (`time.now`) — move the decision to the platform
  (e.g., change-freeze windows are a Run workflow concern, not a policy).
