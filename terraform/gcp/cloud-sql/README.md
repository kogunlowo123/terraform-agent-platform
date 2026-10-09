# gcp/cloud-sql

PostgreSQL on Cloud SQL with production defaults:

- **Private IP only** (`ipv4_enabled = false`) over an existing Service
  Networking peering; TLS enforced (`ssl_mode = ENCRYPTED_ONLY`).
- Optional **CMEK** (`cmek_key_name`); Google-managed encryption otherwise.
- Automated daily backups + **point-in-time recovery** (WAL retention 7d).
- REGIONAL HA by default, query insights on, deletion protection at both
  Terraform and API level.

> Prerequisite: `google_service_networking_connection` must already exist on
> `network` (typically owned by the VPC/root module).

## Usage

```hcl
module "postgres" {
  source = "../../terraform/gcp/cloud-sql"

  name       = "${module.naming.prefix}-pg"
  project_id = "acme-prod"
  region     = "europe-west1"
  network    = google_compute_network.this.self_link

  tier          = "db-custom-4-16384"
  cmek_key_name = google_kms_crypto_key.sql.id

  labels = module.tags.tags
}
```

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `name`, `project_id`, `region` | `string` | — | Identity and placement. |
| `database_version` | `string` | `"POSTGRES_16"` | Engine version. |
| `tier` | `string` | `"db-custom-2-8192"` | Machine tier. |
| `availability_type` | `string` | `"REGIONAL"` | Or ZONAL. |
| `disk_size_gb` | `number` | `100` | Autoresizing SSD. |
| `network` | `string` | — | Peered VPC self link. |
| `cmek_key_name` | `string` | `null` | CMEK key. |
| `database_name` / `username` | `string` | `tap` / `tap_admin` | Initial DB and user. |
| `backup_start_time` | `string` | `"02:00"` | UTC window. |
| `retained_backups` | `number` | `14` | Backup count. |
| `transaction_log_retention_days` | `number` | `7` | PITR window. |
| `database_flags` | `map(string)` | `{}` | Postgres flags. |
| `deletion_protection` | `bool` | `true` | Both guard levels. |
| `labels` | `map(string)` | `{}` | User labels. |

## Outputs

| Name | Description |
|---|---|
| `instance_name`, `connection_name`, `private_ip_address` | Connectivity. |
| `database_name`, `username`, `password` (sensitive) | Initial credentials. |
| `server_ca_cert` (sensitive) | TLS CA. |
