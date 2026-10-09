# aws/eks

Production EKS cluster:

- Private API endpoint by default (`endpoint_public_access = false`).
- KMS envelope encryption of Kubernetes secrets (key created + rotated if not supplied).
- `API` authentication mode with declarative **access entries**.
- IRSA (IAM OIDC provider) on by default; EBS CSI addon gets a scoped IRSA role automatically.
- Managed node groups behind launch templates enforcing **IMDSv2** and encrypted gp3 root volumes.
- Core managed addons: vpc-cni, coredns, kube-proxy, aws-ebs-csi-driver.
- Full control-plane logging to CloudWatch.

## Usage

```hcl
module "eks" {
  source = "../../terraform/aws/eks"

  name               = module.naming.prefix
  kubernetes_version = "1.30"
  subnet_ids         = module.vpc.private_subnet_ids

  node_groups = {
    system = {
      instance_types = ["m6i.large"]
      min_size       = 2
      max_size       = 4
      desired_size   = 2
    }
    runners = {
      instance_types = ["c6i.xlarge"]
      capacity_type  = "SPOT"
      min_size       = 0
      max_size       = 20
      desired_size   = 2
      labels         = { "tap.dev/role" = "runner" }
    }
  }

  access_entries = {
    platform_admins = {
      principal_arn = "arn:aws:iam::123456789012:role/platform-admin"
      policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
    }
  }

  tags = module.tags.tags
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `string` | — | Cluster name. |
| `kubernetes_version` | `string` | `"1.30"` | Control plane minor version. |
| `subnet_ids` | `list(string)` | — | Private subnets (>= 2 AZs). |
| `endpoint_public_access` | `bool` | `false` | Public API endpoint. |
| `endpoint_public_access_cidrs` | `list(string)` | `[]` | Allowed CIDRs when public. |
| `kms_key_arn` | `string` | `null` | CMK for secrets; null creates one. |
| `enabled_log_types` | `list(string)` | all five | Control plane logs. |
| `enable_irsa` | `bool` | `true` | Create IAM OIDC provider. |
| `node_groups` | `map(object)` | one default group | Managed node groups. |
| `access_entries` | `map(object)` | `{}` | API-mode access entries. |
| `addons` | `map(object)` | vpc-cni, coredns, kube-proxy, ebs-csi | Managed addons. |
| `tags` | `map(string)` | `{}` | Tags for all resources. |

## Outputs

| Name | Description |
|---|---|
| `cluster_name`, `cluster_arn`, `cluster_endpoint`, `cluster_version` | Cluster identifiers. |
| `cluster_certificate_authority_data` | CA bundle. |
| `cluster_security_group_id` | EKS-managed SG. |
| `oidc_issuer_url`, `oidc_provider_arn` | IRSA wiring. |
| `node_role_arn`, `node_group_arns` | Node identities. |
| `kms_key_arn` | Secrets encryption key. |
| `ebs_csi_irsa_role_arn` | EBS CSI IRSA role. |
