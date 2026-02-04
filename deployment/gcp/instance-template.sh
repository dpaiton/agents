#!/usr/bin/env bash
# deployment/gcp/instance-template.sh — Create a GCP instance template for agent tasks.
#
# Usage:
#   ./instance-template.sh                          # Use defaults
#   ./instance-template.sh --machine-type e2-standard-4
#   ./instance-template.sh --project my-project --zone us-east1-b
#
# Environment variables (override defaults):
#   GCP_PROJECT       — GCP project ID (required if not passed via flag)
#   GCP_ZONE          — Compute zone (default: us-central1-a)
#   GCP_MACHINE_TYPE  — Machine type (default: e2-standard-2)
#   GCP_SERVICE_ACCOUNT — Service account email (auto-detected if not set)
#
# The template uses:
#   - Ubuntu 24.04 LTS (ubuntu-os-cloud/ubuntu-2404-lts)
#   - Preemptible instances by default (cost control)
#   - No external IP by default (all outbound via Cloud NAT)
#   - Metadata slots for: task, issue, pr, repo, branch

set -euo pipefail

TEMPLATE_NAME="agents-task-template"
IMAGE_FAMILY="ubuntu-2404-lts-amd64"
IMAGE_PROJECT="ubuntu-os-cloud"
DISK_SIZE="30GB"
SCOPES="cloud-platform"
STARTUP_SCRIPT="$(dirname "$0")/startup-script.sh"

# Defaults (overridable by env vars and flags)
PROJECT="${GCP_PROJECT:-}"
ZONE="${GCP_ZONE:-us-central1-a}"
MACHINE_TYPE="${GCP_MACHINE_TYPE:-e2-standard-2}"
SERVICE_ACCOUNT="${GCP_SERVICE_ACCOUNT:-}"
PREEMPTIBLE="true"

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Create a GCP instance template for running agent tasks.

Options:
  --project PROJECT         GCP project ID (or set GCP_PROJECT)
  --zone ZONE               Compute zone (default: us-central1-a)
  --machine-type TYPE       Machine type (default: e2-standard-2)
  --service-account EMAIL   Service account email (auto-detected if omitted)
  --no-preemptible          Use standard (non-preemptible) instances
  --template-name NAME      Template name (default: agents-task-template)
  -h, --help                Show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project)         PROJECT="$2"; shift 2 ;;
        --zone)            ZONE="$2"; shift 2 ;;
        --machine-type)    MACHINE_TYPE="$2"; shift 2 ;;
        --service-account) SERVICE_ACCOUNT="$2"; shift 2 ;;
        --no-preemptible)  PREEMPTIBLE="false"; shift ;;
        --template-name)   TEMPLATE_NAME="$2"; shift 2 ;;
        -h|--help)         usage; exit 0 ;;
        *)                 echo "Error: Unknown option: $1" >&2; usage; exit 1 ;;
    esac
done

# Validate project
if [[ -z "$PROJECT" ]]; then
    PROJECT=$(gcloud config get-value project 2>/dev/null || true)
    if [[ -z "$PROJECT" ]]; then
        echo "Error: GCP project not set. Use --project or set GCP_PROJECT." >&2
        exit 1
    fi
fi

echo "Creating instance template: $TEMPLATE_NAME"
echo "  Project:      $PROJECT"
echo "  Zone:         $ZONE"
echo "  Machine type: $MACHINE_TYPE"
echo "  Preemptible:  $PREEMPTIBLE"

# Build gcloud command
CMD=(
    gcloud compute instance-templates create "$TEMPLATE_NAME"
    --project "$PROJECT"
    --machine-type "$MACHINE_TYPE"
    --image-family "$IMAGE_FAMILY"
    --image-project "$IMAGE_PROJECT"
    --boot-disk-size "$DISK_SIZE"
    --boot-disk-type pd-ssd
    --scopes "$SCOPES"
    --metadata-from-file startup-script="$STARTUP_SCRIPT"
    --tags agents-task
    --labels app=agents,component=remote-task
)

if [[ "$PREEMPTIBLE" == "true" ]]; then
    CMD+=(--preemptible)
fi

if [[ -n "$SERVICE_ACCOUNT" ]]; then
    CMD+=(--service-account "$SERVICE_ACCOUNT")
fi

# No external IP — outbound via Cloud NAT
CMD+=(--no-address)

"${CMD[@]}"

echo ""
echo "Instance template '$TEMPLATE_NAME' created successfully."
echo ""
echo "Next steps:"
echo "  1. Ensure Secret Manager has: anthropic-api-key, github-token"
echo "  2. Grant the service account roles/secretmanager.secretAccessor"
echo "  3. Use 'eco remote run' to launch tasks"
