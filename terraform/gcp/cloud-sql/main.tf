# terraform/gcp/cloud-sql — PostgreSQL with private IP only, optional CMEK,
# automated backups + PITR, SSL required, and deletion protection at both the
# Terraform and API level.

locals {
  labels = merge(var.labels, { managed_by = "tap" })
}

resource "google_sql_database_instance" "this" {
  name             = var.name
  project          = var.project_id
  region           = var.region
  database_version = var.database_version

  encryption_key_name = var.cmek_key_name

  deletion_protection = var.deletion_protection # Terraform-level guard

  settings {
    tier              = var.tier
    availability_type = var.availability_type
    edition           = "ENTERPRISE"

    disk_type       = "PD_SSD"
    disk_size       = var.disk_size_gb
    disk_autoresize = true

    deletion_protection_enabled = var.deletion_protection # API-level guard

    ip_configuration {
      ipv4_enabled    = false # private IP only
      private_network = var.network
      ssl_mode        = "ENCRYPTED_ONLY"
    }

    backup_configuration {
      enabled                        = true
      start_time                     = var.backup_start_time
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = var.transaction_log_retention_days

      backup_retention_settings {
        retained_backups = var.retained_backups
        retention_unit   = "COUNT"
      }
    }

    maintenance_window {
      day          = 7 # Sunday
      hour         = 4
      update_track = "stable"
    }

    insights_config {
      query_insights_enabled  = true
      record_application_tags = true
      record_client_address   = false
    }

    dynamic "database_flags" {
      for_each = var.database_flags

      content {
        name  = database_flags.key
        value = database_flags.value
      }
    }

    user_labels = local.labels
  }
}

resource "google_sql_database" "this" {
  name     = var.database_name
  project  = var.project_id
  instance = google_sql_database_instance.this.name
}

resource "random_password" "user" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>?"
}

resource "google_sql_user" "this" {
  name     = var.username
  project  = var.project_id
  instance = google_sql_database_instance.this.name
  password = random_password.user.result
}
