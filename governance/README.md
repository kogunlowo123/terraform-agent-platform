# TAP Governance

Policy-as-code lifecycle for the Terraform Agent Platform. Policies are code:
versioned, tested, reviewed, signed, and rolled out in stages.

## Policy lifecycle

```
author -> opa test -> PR review -> bundle build -> signed publish -> staged rollout
```

### 1. Author

* Write Rego (OPA >= 0.60, `import rego.v1`) under [`policies/`](../policies/)
  in the package namespace `tap.<domain>.<policy>`.
* Follow the decision conventions in
  [`policies/README.md`](../policies/README.md): `deny`, `soft_fail`,
  `advisory`. Configuration goes in bundle data (`data.tap.config`), not in
  the policy body.
* Every policy MUST ship a `_test.rego` covering at least: one passing input,
  one failing input per rule, and one boundary case.

### 2. Test

```bash
opa fmt --diff policies/
opa test policies/ -v --coverage
```

CI (`terraform-ci.yml`) blocks merge on failures and on formatting drift.

### 3. PR review

`policies/**` is owned by the security team
([`.github/CODEOWNERS`](../.github/CODEOWNERS)); a security approval is
mandatory. Reviewers check: blast radius, message quality (actionable, names
the resource address), rollout stage, and whether the control maps to a
compliance framework entry in [`compliance/controls/`](../compliance/controls/).

### 4. Bundle build

The release pipeline builds an OCI-distributable OPA bundle per the manifest
in [`bundles/bundle.yaml`](bundles/bundle.yaml):

```bash
opa build -b policies/ -o dist/tap-policies.tar.gz \
  --revision "$(git rev-parse --short HEAD)"
```

Bundle data (`data.json`) is rendered from the manifest's `config` section so
allowlists and model lists are reviewed in the same PR as the policy.

### 5. Signed publish

Bundles are pushed to the registry and signed with cosign (keyless, GitHub
OIDC identity):

```bash
oras push ghcr.io/<org>/tap-policies:<version> dist/tap-policies.tar.gz
cosign sign ghcr.io/<org>/tap-policies:<version>
```

The Policy Service verifies the signature against the pinned identity before
activating a bundle; unsigned or mis-signed bundles are rejected and the
previous bundle stays live.

### 6. Staged rollout

Each policy carries a `stage` in the bundle manifest:

| Stage      | Effect                                                        |
|------------|---------------------------------------------------------------|
| `advisory` | All results downgraded to advisory; observe denial rate       |
| `soft`     | `deny` downgraded to `soft_fail` (approval instead of block)  |
| `hard`     | Full enforcement                                              |

Promotion requires: >= 7 days at the prior stage, denial-rate review on the
`PolicyDenialSpike` dashboard, and sign-off recorded in the promoting PR.
Rollback = republish the previous bundle version (bundles are immutable and
content-addressed, so rollback is instant and auditable).

## Sentinel migration

Teams migrating from Terraform Cloud/Enterprise Sentinel policies: see
[`sentinel-adapter/README.md`](sentinel-adapter/README.md).
