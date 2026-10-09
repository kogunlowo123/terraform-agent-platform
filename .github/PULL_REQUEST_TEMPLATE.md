# Summary

<!-- What does this change do, and why? Link the issue or ADR. -->

## Type of change

- [ ] Terraform module
- [ ] Policy (Rego) — requires security team review
- [ ] Platform / SDK / agents (Python)
- [ ] CI / GitOps / observability
- [ ] Docs / compliance mappings

## Checklist

- [ ] `make lint` and `make test` pass locally
- [ ] New/changed Rego has a `_test.rego` and `opa test policies/` passes
- [ ] New/changed Terraform is formatted (`terraform fmt`) and validated
- [ ] Mandatory tags / policy conventions respected (see `policies/README.md`)
- [ ] Breaking changes called out below and an ADR added/updated if architectural
- [ ] No secrets, credentials, or tenant data in the diff

## Policy changes only

- [ ] Rollout stage set in `governance/bundles/bundle.yaml` (new policies start `advisory`)
- [ ] Compliance control mappings updated (`compliance/controls/*.yaml`)

## Breaking changes / migration notes

<!-- None, or describe the migration path. -->

## How was this tested?

<!-- Unit tests, opa test output, plan output against examples/, compose stack, etc. -->
