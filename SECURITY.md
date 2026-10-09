# Security Policy

## Reporting a vulnerability

**Do not open public issues for security vulnerabilities.**

Report privately via GitHub Security Advisories ("Report a vulnerability" on
the repository's Security tab) or email security@example.org. Include:

* affected component (control plane, SDK, agents, runner images, policies, CI)
* version/commit, reproduction steps, and impact assessment
* any suggested remediation

You will receive an acknowledgement within **2 business days** and a triage
decision within **7 days**. We practice coordinated disclosure: we will agree
on a disclosure timeline with you (default 90 days) and credit reporters in
the advisory unless anonymity is requested.

## Supported versions

| Version | Supported |
|---|---|
| latest minor (0.x) | yes — security fixes land on `main` and the latest release |
| older releases | no — upgrade to the latest release |

## Scope

In scope: this repository (platform, SDK, agents, policies, CI/GitOps
configurations, runner images) and published artifacts (ghcr images, PyPI SDK,
policy bundles).

Out of scope: vulnerabilities in third-party dependencies without a
demonstrated impact on TAP (report upstream; we track them via Dependabot,
Trivy, and Grype), and issues requiring a compromised cloud account or
privileged cluster access.

## Platform security posture

* No static cloud credentials: OIDC federation, 15-minute workspace-scoped
  tokens for runners.
* Ephemeral, single-use runner pods; per-tenant encrypted state.
* Signed supply chain: cosign-signed images and policy bundles, SBOM published
  per release (`.github/workflows/release.yml`).
* Continuous scanning: Trivy, gitleaks, Grype weekly and per PR
  (`.github/workflows/security-scan.yml`).
* Agent containment: scope allowlists, mutation budgets, mandatory policy
  pre-check, human approval for destroy (see
  `docs/architecture/ARCHITECTURE.md` §12).

## Secrets hygiene

If you accidentally commit a secret: rotate it immediately, then contact
security@example.org. History rewriting alone is not sufficient.
