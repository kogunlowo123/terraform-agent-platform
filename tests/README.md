# TAP Test Strategy

The pyramid, from widest (fast, many) to narrowest (slow, few):

```
        ┌───────────────┐
        │   e2e          │  compose stack + API: one governed run end-to-end
        ├───────────────┤
        │   module       │  terratest: terraform init/plan assertions per module
        ├───────────────┤
        │   policy       │  opa test: every .rego has a _test.rego beside it
        ├───────────────┤
        │   unit         │  pytest: services, agents, guardrails — mocked deps
        └───────────────┘
```

## Layers

| Layer | Tooling | Where | Runs in |
|---|---|---|---|
| Unit | pytest (+ pytest-asyncio), all I/O mocked | `tests/platform/`, `tests/agents/` | every PR (`platform-ci.yml`), <60s |
| Policy | `opa test policies/ -v` | `policies/**/_test.rego` | every PR (`terraform-ci.yml`), seconds |
| Module | terratest (Go), `init` + `plan` assertions, no apply by default | `tests/terraform/` | nightly + on `terraform/**` PRs with cloud creds |
| E2E | compose stack (`scripts/dev-up.sh`) + API-driven run | `tests/e2e/` (future) | nightly |

## Conventions

* **Unit tests are contract tests.** Service tests pin the observable contract
  (inputs, outputs, state transitions, emitted events) against mocked
  dependencies — never against implementation details. When the platform
  module under test does not exist yet, the test file carries a minimal
  reference implementation that IS the executable contract; the real module
  must make the same tests pass when it replaces the reference import.
* **Policy tests** cover at minimum: one passing input, one failing input per
  rule, one boundary case (see `governance/README.md`).
* **Terratest** never applies by default: `init` + `plan` only. Apply-mode
  (`TAP_TERRATEST_APPLY=1`) is reserved for the nightly job with an isolated
  sandbox account.
* **No live cloud or LLM calls** anywhere below e2e. The AI Gateway is mocked
  at the HTTP boundary.

## Running locally

```bash
make test           # pytest unit suites
make policy-test    # opa fmt + opa test
cd tests/terraform && go test -v -timeout 30m   # terratest (needs terraform + creds)
```
