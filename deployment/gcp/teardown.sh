#!/usr/bin/env bash
# deployment/gcp/teardown.sh — Clean shutdown for an agent task instance.
#
# Usage:
#   ./teardown.sh <instance-name> [--zone ZONE] [--project PROJECT]
#
# This script:
#   1. Posts a final status comment on the associated GitHub issue/PR
#   2. Uploads logs to GCP Cloud Storage (if bucket configured)
#   3. Deletes the GCP instance
#
# Can be run from the instance itself (for graceful shutdown) or from
# a local machine to forcefully tear down a remote instance.

set -euo pipefail

METADATA_URL="http://metadata.google.internal/computeMetadata/v1"
METADATA_HEADER="Metadata-Flavor: Google"

usage() {
    cat <<EOF
Usage: $(basename "$0") <instance-name> [OPTIONS]

Gracefully tear down a GCP agent task instance.

Arguments:
  instance-name           Name of the GCP instance to tear down

Options:
  --zone ZONE             Compute zone (default: from gcloud config or us-central1-a)
  --project PROJECT       GCP project (default: from gcloud config)
  --log-bucket BUCKET     GCS bucket for log upload (optional)
  --skip-comment          Don't post a shutdown comment to GitHub
  -h, --help              Show this help
EOF
}

INSTANCE=""
ZONE="${GCP_ZONE:-}"
PROJECT="${GCP_PROJECT:-}"
LOG_BUCKET=""
SKIP_COMMENT="false"

if [[ $# -lt 1 ]]; then
    usage
    exit 1
fi

INSTANCE="$1"
shift

while [[ $# -gt 0 ]]; do
    case "$1" in
        --zone)         ZONE="$2"; shift 2 ;;
        --project)      PROJECT="$2"; shift 2 ;;
        --log-bucket)   LOG_BUCKET="$2"; shift 2 ;;
        --skip-comment) SKIP_COMMENT="true"; shift ;;
        -h|--help)      usage; exit 0 ;;
        *)              echo "Error: Unknown option: $1" >&2; usage; exit 1 ;;
    esac
done

# Resolve defaults from gcloud config
if [[ -z "$PROJECT" ]]; then
    PROJECT=$(gcloud config get-value project 2>/dev/null || true)
    if [[ -z "$PROJECT" ]]; then
        echo "Error: GCP project not set. Use --project or set GCP_PROJECT." >&2
        exit 1
    fi
fi

if [[ -z "$ZONE" ]]; then
    ZONE=$(gcloud config get-value compute/zone 2>/dev/null || true)
    ZONE="${ZONE:-us-central1-a}"
fi

echo "Tearing down instance: $INSTANCE"
echo "  Project: $PROJECT"
echo "  Zone:    $ZONE"

# ---------------------------------------------------------------------------
# Step 1: Retrieve instance metadata (issue/PR numbers for status comment)
# ---------------------------------------------------------------------------

get_instance_metadata() {
    local key="$1"
    gcloud compute instances describe "$INSTANCE" \
        --zone="$ZONE" \
        --project="$PROJECT" \
        --format="value(metadata.items['$key'])" 2>/dev/null || echo ""
}

ISSUE_NUM=$(get_instance_metadata "issue")
PR_NUM=$(get_instance_metadata "pr")

# ---------------------------------------------------------------------------
# Step 2: Post final status comment
# ---------------------------------------------------------------------------

if [[ "$SKIP_COMMENT" != "true" ]]; then
    BODY="Agent instance \`$INSTANCE\` is being shut down (manual teardown)."

    if [[ -n "$ISSUE_NUM" ]]; then
        echo "Posting shutdown comment to issue #$ISSUE_NUM..."
        gh issue comment "$ISSUE_NUM" --body "$BODY" 2>/dev/null || \
            echo "Warning: Could not post comment to issue #$ISSUE_NUM"
    elif [[ -n "$PR_NUM" ]]; then
        echo "Posting shutdown comment to PR #$PR_NUM..."
        gh pr comment "$PR_NUM" --body "$BODY" 2>/dev/null || \
            echo "Warning: Could not post comment to PR #$PR_NUM"
    fi
fi

# ---------------------------------------------------------------------------
# Step 3: Upload logs (if bucket configured)
# ---------------------------------------------------------------------------

if [[ -n "$LOG_BUCKET" ]]; then
    TIMESTAMP=$(date -u '+%Y%m%dT%H%M%SZ')
    LOG_PATH="gs://$LOG_BUCKET/agents-logs/$INSTANCE/$TIMESTAMP.log"

    echo "Uploading logs to $LOG_PATH..."

    # Try to pull the log file from the instance via SSH
    TEMP_LOG=$(mktemp)
    gcloud compute ssh "$INSTANCE" \
        --zone="$ZONE" \
        --project="$PROJECT" \
        --command="cat /var/log/agents-task.log 2>/dev/null || echo 'No log file found'" \
        > "$TEMP_LOG" 2>/dev/null || echo "Warning: Could not retrieve logs via SSH"

    if [[ -s "$TEMP_LOG" ]]; then
        gcloud storage cp "$TEMP_LOG" "$LOG_PATH" 2>/dev/null || \
            echo "Warning: Could not upload logs to GCS"
        echo "Logs uploaded to: $LOG_PATH"
    fi

    rm -f "$TEMP_LOG"
fi

# ---------------------------------------------------------------------------
# Step 4: Delete the instance
# ---------------------------------------------------------------------------

echo "Deleting instance $INSTANCE..."
gcloud compute instances delete "$INSTANCE" \
    --zone="$ZONE" \
    --project="$PROJECT" \
    --quiet

echo ""
echo "Instance '$INSTANCE' deleted."
