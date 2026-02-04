# deployment/gcp/secrets.tf — Secret Manager resources for API keys.
#
# This file creates the Secret Manager secret *shells*. The actual secret
# values must be populated manually or via CI:
#
#   echo -n "sk-..." | gcloud secrets versions add anthropic-api-key --data-file=-
#
# Terraform only manages the secret resources and IAM — never the values.

resource "google_secret_manager_secret" "anthropic_api_key" {
  secret_id = var.secret_names.anthropic_api_key

  replication {
    auto {}
  }

  labels = {
    app = "agents"
  }
}

resource "google_secret_manager_secret" "github_token" {
  secret_id = var.secret_names.github_token

  replication {
    auto {}
  }

  labels = {
    app = "agents"
  }
}

resource "google_secret_manager_secret" "google_api_key" {
  secret_id = var.secret_names.google_api_key

  replication {
    auto {}
  }

  labels = {
    app = "agents"
  }
}

resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = var.secret_names.openai_api_key

  replication {
    auto {}
  }

  labels = {
    app = "agents"
  }
}

resource "google_secret_manager_secret" "arcade_api_key" {
  secret_id = var.secret_names.arcade_api_key

  replication {
    auto {}
  }

  labels = {
    app = "agents"
  }
}
