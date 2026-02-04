# deployment/gcp/main.tf — Core infrastructure for agent task instances.
#
# Manages:
#   - Instance template (Ubuntu 24.04, startup script, labels)
#   - Firewall rules (no inbound, allow outbound)
#   - Log bucket (optional)
#
# Usage:
#   cd deployment/gcp
#   terraform init
#   terraform plan -var="project_id=my-project"
#   terraform apply -var="project_id=my-project"

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ---------------------------------------------------------------------------
# Instance template
# ---------------------------------------------------------------------------

resource "google_compute_instance_template" "agent_task" {
  name_prefix  = "agents-task-"
  machine_type = var.machine_type
  region       = var.region

  labels = {
    app       = "agents"
    component = "remote-task"
    managed   = "terraform"
  }

  tags = ["agents-task"]

  disk {
    source_image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
    disk_type    = "pd-ssd"
    disk_size_gb = var.disk_size_gb
    auto_delete  = true
    boot         = true
  }

  network_interface {
    network = "default"
    # No access_config block = no external IP.
    # Outbound traffic goes through Cloud NAT (configured separately or
    # pre-existing). If direct egress is needed, uncomment:
    # access_config {}
  }

  scheduling {
    preemptible       = var.preemptible
    automatic_restart = var.preemptible ? false : true
  }

  metadata = {
    startup-script = file("${path.module}/startup-script.sh")
  }

  service_account {
    email  = google_service_account.agent_task.email
    scopes = ["cloud-platform"]
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ---------------------------------------------------------------------------
# Firewall — deny all inbound, agents only talk outbound
# ---------------------------------------------------------------------------

resource "google_compute_firewall" "agent_deny_inbound" {
  name    = "agents-deny-inbound"
  network = "default"

  direction = "INGRESS"

  deny {
    protocol = "all"
  }

  target_tags   = ["agents-task"]
  source_ranges = ["0.0.0.0/0"]

  description = "Deny all inbound traffic to agent task instances"
}

# ---------------------------------------------------------------------------
# Log bucket (optional)
# ---------------------------------------------------------------------------

resource "google_storage_bucket" "agent_logs" {
  count = var.log_bucket_name != "" ? 1 : 0

  name     = var.log_bucket_name
  location = var.region

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    app       = "agents"
    component = "logs"
  }
}
