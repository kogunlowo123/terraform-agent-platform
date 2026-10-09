# TAP Compliance Framework

Compliance controls as data: each framework is a YAML file in
[`controls/`](controls/) mapping a representative set of controls to the Rego
policies that enforce them and the audit queries that evidence them. The
compliance agent and the `/v1/audit` API consume these files directly; auditors
get generated evidence packs instead of screenshots.

## Model

```yaml
framework: soc2
version: "2017 TSC (2022 points of focus)"
controls:
  - id: CC6.1
    title: Logical access security
    description: >
      The entity implements logical access security software ...
    policy_refs:                  # Rego packages that ENFORCE the control
      - tap.terraform.deny_public_s3
      - tap.terraform.encryption_required
    evidence:                     # audit queries that PROVE enforcement
      - "SELECT run_id, decision, created_at FROM policy_results WHERE package = 'tap.terraform.deny_public_s3' AND created_at > now() - interval '90 days'"
    automation: full              # full | partial | manual
```

Field semantics:

| Field | Meaning |
|---|---|
| `id` | Canonical control identifier within the framework |
| `title` / `description` | Auditor-facing summary of the control |
| `policy_refs` | Rego package paths under `data.tap.*`; empty when no technical control applies |
| `evidence` | Queries against the TAP audit schema (`policy_results`, `runs`, `approvals`, `audit_log`) or named platform reports |
| `automation` | `full` = policy-enforced and evidenced automatically; `partial` = enforced but needs human-collected evidence; `manual` = organizational control, tracked only |

## Frameworks

| File | Framework |
|---|---|
| [`controls/soc2.yaml`](controls/soc2.yaml) | SOC 2 (Trust Services Criteria) |
| [`controls/iso27001.yaml`](controls/iso27001.yaml) | ISO/IEC 27001:2022 Annex A |
| [`controls/hipaa.yaml`](controls/hipaa.yaml) | HIPAA Security Rule |
| [`controls/pci-dss.yaml`](controls/pci-dss.yaml) | PCI-DSS v4.0 |
| [`controls/gdpr.yaml`](controls/gdpr.yaml) | GDPR |
| [`controls/nist-800-53.yaml`](controls/nist-800-53.yaml) | NIST SP 800-53 rev 5 |
| [`controls/cis.yaml`](controls/cis.yaml) | CIS Benchmarks (AWS + Kubernetes) |

The sets are representative, not exhaustive: they cover the controls TAP can
enforce or evidence. Extend per tenant via the same schema.

## How it is consumed

1. **Plan time** — the Policy Service tags each decision with the control IDs
   from the bundle manifest, so every denial is traceable to a framework
   control.
2. **Continuously** — the compliance agent re-runs `evidence` queries on a
   schedule and flags controls whose evidence has gone stale or empty.
3. **Audit time** — `tap compliance report --framework soc2 --window 90d`
   renders the control set with pass/fail status and attached evidence rows.

## Adding a control

1. Add the entry to the framework YAML (keep `id` canonical to the framework).
2. If a policy enforces it, add the control ID to that policy's `controls`
   list in [`../governance/bundles/bundle.yaml`](../governance/bundles/bundle.yaml).
3. CI validates YAML shape and that every `policy_refs` entry resolves to a
   package in `policies/`.
