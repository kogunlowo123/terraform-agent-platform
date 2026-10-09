# Contributing to TAP

Thanks for improving the Terraform Agent Platform. This guide covers workflow
and standards; architecture context lives in
[`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md) and
decisions in [`docs/adr/`](docs/adr/).

## Getting set up

```bash
git clone https://github.com/example-org/terraform-agent-platform
cd terraform-agent-platform
./scripts/dev-up.sh                 # local stack (or scripts/dev-up.ps1)
pip install -e ./platform -e ./sdk
pip install pre-commit && pre-commit install
```

Toolchain: Python 3.12+, Terraform 1.9+, OPA 0.68+, Go 1.22 (terratest only),
Docker with compose v2.

## Workflow

1. Open or claim an issue; significant changes start with a short design note
   or an ADR (`docs/adr/`).
2. Branch from `main`: `feat/<topic>`, `fix/<topic>`, `policy/<topic>`.
3. Keep commits scoped; use conventional-commit style subjects
   (`feat:`, `fix:`, `policy:`, `docs:`, `ci:`).
4. Before pushing: `make lint test policy-test` (and `make terraform-check`
   for module changes).
5. Open a PR using the template. CODEOWNERS routes review: policies and
   governance require security-team approval.

## Standards by area

### Python (`platform/`, `sdk/`, `agents/`)
* Ruff (lint + format) and mypy are gating. Type hints required on public
  functions.
* Tests are contract tests with mocked I/O — see
  [`tests/README.md`](tests/README.md). New services need tests in
  `tests/platform/`; new agent behavior in `tests/agents/`.

### Rego (`policies/`)
* OPA >= 0.60 style (`import rego.v1`), formatted with `opa fmt`.
* Decision conventions (`deny` / `soft_fail` / `advisory`) and input contracts:
  [`policies/README.md`](policies/README.md).
* Every policy ships a `_test.rego`. New policies land at `advisory` stage in
  [`governance/bundles/bundle.yaml`](governance/bundles/bundle.yaml) and map to
  compliance controls where applicable.

### Terraform (`terraform/`)
* `terraform fmt`, `validate`, tflint clean; checkov/tfsec findings addressed
  or explicitly waived with justification.
* Modules must pass the shipped policies — including the mandatory tag set
  (owner, cost_center, environment, data_class).

### CI / GitOps / Observability
* Workflow changes need a green run on the PR itself.
* Alert rule changes include a rationale (threshold, `for`, severity) in the PR.

## Security

Never commit credentials, state files, or tenant data (gitleaks runs in
pre-commit and CI). Report vulnerabilities per [`SECURITY.md`](SECURITY.md) —
not via public issues.

## Code of conduct

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

By contributing you agree your contributions are licensed under the
[Apache License 2.0](LICENSE).
