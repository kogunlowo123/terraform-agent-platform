# TAP Policies

Rego policies evaluated by the TAP Policy Service on every run, and by CI via
`opa test`. Written for OPA >= 0.60 (`import rego.v1`).

## Bundle layout

```
policies/
├── terraform/            # plan-time gates on Terraform plan JSON
│   ├── deny_public_s3.rego
│   ├── require_tags.rego
│   ├── encryption_required.rego
│   ├── deny_open_ingress.rego
│   └── instance_allowlist.rego
├── cost/
│   └── budget_gate.rego  # Infracost delta vs workspace budget
├── kubernetes/
│   └── pod_security.rego # admission + rendered-manifest CI checks
└── ai/
    └── model_governance.rego
```

Every policy ships with a `_test.rego` beside it. Bundles are built and signed
from this tree by the governance pipeline — see
[`governance/README.md`](../governance/README.md) and
[`governance/bundles/bundle.yaml`](../governance/bundles/bundle.yaml).
Data-driven configuration (allowlists, approved models, extra taggable types)
lives in the bundle's `data.json` under `data.tap.config`, never in the Rego.

## Decision format

Each policy package may define any of three set-valued rules:

| Rule                  | Meaning                                       | Platform behavior |
|-----------------------|-----------------------------------------------|-------------------|
| `deny contains msg`   | Hard violation                                | Run fails; audit event; no override |
| `soft_fail contains msg` | Violation that a human may accept          | Run pauses; approval signal to the workflow; approver identity recorded |
| `advisory contains msg`  | Signal only                                | Attached to the run report and PR comment; never blocks |

Messages are plain strings prefixed with the offending resource address, e.g.
`aws_security_group.web: ingress from 0.0.0.0/0 to administrative port 22 is
always denied`.

## Input contracts

* **terraform/**: the full Terraform plan JSON (`terraform show -json plan.out`),
  with TAP run context merged in at the top level:
  `{"workspace": {"environment", "budget_usd", "name"}, "resource_changes": [...]}`.
* **cost/**: `{"cost": {"monthly_delta_usd"}, "workspace": {"budget_usd", "name"}}`.
* **kubernetes/**: one Kubernetes manifest per evaluation (Pod or controller).
* **ai/**: same plan JSON as terraform/ (AI infra is Terraform-managed).

## How the platform consumes decisions

The Run workflow (Temporal) calls the Policy Service after the plan step:

```
POST /v1/data/tap  { "input": <plan JSON + run context> }
```

The service aggregates all packages under `data.tap.*` into one verdict:

1. any `deny` non-empty            -> run state `policy_failed` (hard)
2. else any `soft_fail` non-empty  -> run state `awaiting_approval`
3. `advisory` messages             -> appended to the run report / PR comment

Rollout stage (advisory -> soft -> hard) is applied per policy by the bundle
manifest (`governance/bundles/bundle.yaml`): a policy in `advisory` stage has
its `deny`/`soft_fail` results downgraded by the Policy Service, which lets a
new policy bake on real traffic before it can block anyone.

## Local development

```bash
opa fmt -w policies/          # format
opa test policies/ -v         # run all policy tests
opa eval -d policies/ -d bundle-data.json \
  -i plan.json 'data.tap.terraform'   # evaluate a real plan
```

`make policy-test` runs the same checks as CI
([`.github/workflows/terraform-ci.yml`](../.github/workflows/terraform-ci.yml)).
