# deployment/gcp/outputs.tf — Terraform outputs for agent task infrastructure.

output "instance_template_name" {
  description = "Name of the instance template for agent tasks"
  value       = google_compute_instance_template.agent_task.name
}

output "instance_template_self_link" {
  description = "Self-link of the instance template (used by eco remote run)"
  value       = google_compute_instance_template.agent_task.self_link
}

output "service_account_email" {
  description = "Email of the agent task service account"
  value       = google_service_account.agent_task.email
}

output "log_bucket" {
  description = "GCS bucket for agent task logs (empty if not configured)"
  value       = var.log_bucket_name != "" ? google_storage_bucket.agent_logs[0].name : ""
}
