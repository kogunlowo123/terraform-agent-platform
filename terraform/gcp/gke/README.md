# gcp/gke

VPC-native GKE cluster with TAP security posture:

- **Workload identity** (`<project>.svc.id.goog`) — no node credentials in pods.
- **Private + shielded nodes** (secure boot, integrity monitoring), GKE metadata server, legacy endpoints disabled.
- Release channel upgrades, binary authorization enforced, deletion protection.
- Minimal dedicated node service account (logging/monitoring/AR-read) created when none is given.
- Optional **node auto-provisioning** with CPU/memory ceilings.

## Usage

```hcl
module "gke" {
  source = "../../terraform/gcp/gke"

  name       = module.naming.prefix
  project_id = "acme-prod"
  location   = "europe-west1"

  network                       = google_compute_network.this.self_link
  subnetwork                    = google_compute_subnetwork.gke.self_link
  pods_secondary_range_name     = "pods"
  services_secondary_range_name = "services"

  master_authorized_networks = {
    corp-vpn = "10.8.0.0/16"
  }

  node_pools = {
    workload = { machine_type = "n2-standard-8", min_count = 1, max_count = 10 }
  }

  enable_node_auto_provisioning = true

  labels = module.tags.tags
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `name`, `project_id`, `location` | `string` | — | Identity and placement. |
| `network`, `subnetwork` | `string` | — | VPC wiring. |
| `pods_secondary_range_name`, `services_secondary_range_name` | `string` | — | VPC-native ranges. |
| `release_channel` | `string` | `"REGULAR"` | RAPID/REGULAR/STABLE. |
| `enable_private_endpoint` | `bool` | `false` | Private-only master. |
| `master_ipv4_cidr_block` | `string` | `"172.16.0.0/28"` | Control plane range. |
| `master_authorized_networks` | `map(string)` | `{}` | name => CIDR. |
| `node_service_account` | `string` | `null` | Null creates a minimal SA. |
| `node_pools` | `map(object)` | one default pool | Shielded node pools. |
| `enable_node_auto_provisioning` | `bool` | `false` | NAP. |
| `nap_resource_limits` | `object` | 64 CPU / 256 GiB | NAP ceilings. |
| `deletion_protection` | `bool` | `true` | Destroy guard. |
| `labels` | `map(string)` | `{}` | Resource labels. |

## Outputs

| Name | Description |
|---|---|
| `cluster_id`, `cluster_name`, `endpoint`, `ca_certificate` | Cluster access. |
| `workload_identity_pool` | WI pool string. |
| `node_service_account_email` | Node SA. |
| `node_pool_names` | Managed pools. |
