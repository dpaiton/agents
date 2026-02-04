# deployment/gcp/iam.tf — Service account and IAM bindings for agent tasks.
#
# Follows least-privilege: the service account can only manage its own
# instance, read secrets, and write logs.

resource "google_service_account" "agent_task" {
  account_id   = "agents-task-runner"
  display_name = "Agents Task Runner"
  description  = "Service account for remote agent task instances"
}

# ---------------------------------------------------------------------------
# IAM bindings — least privilege
# ---------------------------------------------------------------------------

# Read API keys from Secret Manager
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.agent_task.email}"
}

# Manage own compute instance (for self-deletion on completion)
resource "google_project_iam_member" "compute_instance_admin" {
  project = var.project_id
  role    = "roles/compute.instanceAdmin.v1"
  member  = "serviceAccount:${google_service_account.agent_task.email}"
}

# Write logs to Cloud Logging
resource "google_project_iam_member" "log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.agent_task.email}"
}

# Write to log bucket (if configured)
resource "google_storage_bucket_iam_member" "log_bucket_writer" {
  count = var.log_bucket_name != "" ? 1 : 0

  bucket = google_storage_bucket.agent_logs[0].name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.agent_task.email}"
}
