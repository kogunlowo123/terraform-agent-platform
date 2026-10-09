# TAP Examples

End-to-end root modules that compose the [`terraform/`](../terraform) module
library. Each directory is a self-contained Terraform/OpenTofu root module and
doubles as a TAP **workspace** definition.

## Index

| Example | Composes | Scenario |
|---|---|---|
| [`aws-vpc-baseline/`](aws-vpc-baseline/) | `shared/naming` + `shared/tags` + `aws/vpc` | Minimal network baseline: multi-AZ VPC, flow logs, gateway endpoints. |
| [`aws-eks-platform/`](aws-eks-platform/) | above + `aws/eks` + `aws/iam` | Platform cluster with IRSA, access entries, and the OIDC-federated TAP runner role. |
| [`azure-ai-rag/`](azure-ai-rag/) | `azure/landing-zone` + `azure/key-vault` + `ai/azure-openai` + `ai/rag-stack` (qdrant) | Governed AI landing zone with Azure OpenAI deployments and a full RAG stack. |

## How TAP runs these

1. **Workspace mapping** — each example directory maps 1:1 to a TAP workspace
   (`tenant/project/workspace`). The workspace stores the variable values that
   `terraform.tfvars.example` documents, plus secrets (e.g. `qdrant_api_key`)
   in the workspace secret store.

   ```bash
   tap workspace create acme/prod/network --dir examples/aws-vpc-baseline
   tap run plan  --workspace acme/prod/network
   tap run apply --workspace acme/prod/network   # gated by OPA + approval
   ```

2. **State** — every example declares `backend "local"` for standalone
   development only. At run time the TAP runner generates an override pointing
   at TAP-managed state: versioned, encrypted with the tenant's KMS key, and
   locked (see `docs/architecture/ARCHITECTURE.md` §9).

3. **Credentials** — runners receive 15-minute OIDC-federated cloud
   credentials scoped to the workspace's role (`terraform/aws/iam` creates
   that role on AWS). No static keys anywhere.

4. **Policy gates** — `tap run plan` produces plan JSON that the OPA policy
   service evaluates (required tags, encryption, no-public-access, cost
   ceilings) before any apply is scheduled.

## Running standalone (without TAP)

```bash
cd examples/aws-vpc-baseline
cp terraform.tfvars.example terraform.tfvars   # edit values
terraform init
terraform plan
```

Standalone use is for module development only — production changes must flow
through governed TAP runs.
