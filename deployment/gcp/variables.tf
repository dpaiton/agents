# deployment/gcp/variables.tf — Input variables for agent task infrastructure.

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone for compute instances"
  type        = string
  default     = "us-central1-a"
}

variable "machine_type" {
  description = "Default machine type for agent task instances"
  type        = string
  default     = "e2-standard-2"
}

variable "disk_size_gb" {
  description = "Boot disk size in GB"
  type        = number
  default     = 30
}

variable "preemptible" {
  description = "Use preemptible (spot) instances for cost savings"
  type        = bool
  default     = true
}

variable "timeout_hours" {
  description = "Default auto-shutdown timeout in hours"
  type        = number
  default     = 4
}

variable "log_bucket_name" {
  description = "GCS bucket name for agent task logs (created if set)"
  type        = string
  default     = ""
}

# Secret names in Secret Manager (must be pre-populated)
variable "secret_names" {
  description = "Map of secret names in Secret Manager"
  type = object({
    anthropic_api_key = string
    github_token      = string
    google_api_key    = string
    openai_api_key    = string
    arcade_api_key    = string
  })
  default = {
    anthropic_api_key = "anthropic-api-key"
    github_token      = "github-token"
    google_api_key    = "google-api-key"
    openai_api_key    = "openai-api-key"
    arcade_api_key    = "arcade-api-key"
  }
}
