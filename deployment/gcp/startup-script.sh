#!/usr/bin/env bash
# deployment/gcp/startup-script.sh — GCP instance startup script for agent tasks.
#
# This script runs on first boot of an agent task instance. It:
#   1. Installs system dependencies (git, python3.12, uv, gh CLI, claude)
#   2. Pulls secrets from GCP Secret Manager
#   3. Clones the repo and checks out the specified branch
#   4. Writes .env from secrets
#   5. Runs `eco run` or `eco deploy` with the task from instance metadata
#   6. Posts status updates to the GitHub issue/PR
#   7. Shuts down the instance on completion
#
# Instance metadata keys:
#   task          — Task description (required)
#   repo          — Git repo URL (required)
#   branch        — Branch to checkout (default: main)
#   issue         — GitHub issue number (optional)
#   pr            — GitHub PR number (optional)
#   timeout_hours — Max runtime in hours (default: 4)
#   deploy_mode   — "true" to use eco deploy --watch instead of eco run

set -euo pipefail

WORKDIR="/opt/agents"
LOG_FILE="/var/log/agents-task.log"
METADATA_URL="http://metadata.google.internal/computeMetadata/v1"
METADATA_HEADER="Metadata-Flavor: Google"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log() {
    local msg="[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"
    echo "$msg" | tee -a "$LOG_FILE"
}

get_metadata() {
    local key="$1"
    curl -sf -H "$METADATA_HEADER" \
        "$METADATA_URL/instance/attributes/$key" 2>/dev/null || echo ""
}

get_project_id() {
    curl -sf -H "$METADATA_HEADER" \
        "$METADATA_URL/project/project-id" 2>/dev/null || echo ""
}

get_instance_name() {
    curl -sf -H "$METADATA_HEADER" \
        "$METADATA_URL/instance/name" 2>/dev/null || echo ""
}

get_zone() {
    local full
    full=$(curl -sf -H "$METADATA_HEADER" \
        "$METADATA_URL/instance/zone" 2>/dev/null || echo "")
    # Returns projects/PROJECT/zones/ZONE — extract just the zone
    basename "$full"
}

get_secret() {
    local name="$1"
    local project="$2"
    gcloud secrets versions access latest \
        --secret="$name" \
        --project="$project" 2>/dev/null || echo ""
}

post_github_comment() {
    local target="$1"
    local body="$2"
    if [[ -n "$ISSUE_NUM" ]]; then
        gh issue comment "$ISSUE_NUM" --body "$body" 2>/dev/null || true
    elif [[ -n "$PR_NUM" ]]; then
        gh pr comment "$PR_NUM" --body "$body" 2>/dev/null || true
    fi
}

shutdown_instance() {
    local instance zone
    instance=$(get_instance_name)
    zone=$(get_zone)
    log "Shutting down instance: $instance (zone: $zone)"
    # Use gcloud to delete the instance (self-destruct)
    gcloud compute instances delete "$instance" \
        --zone="$zone" \
        --quiet 2>/dev/null &
    # Give gcloud a moment to start the delete, then exit
    sleep 5
    exit 0
}

# ---------------------------------------------------------------------------
# Read instance metadata
# ---------------------------------------------------------------------------

log "=== Agent Task Startup ==="

TASK=$(get_metadata "task")
REPO=$(get_metadata "repo")
BRANCH=$(get_metadata "branch")
ISSUE_NUM=$(get_metadata "issue")
PR_NUM=$(get_metadata "pr")
TIMEOUT_HOURS=$(get_metadata "timeout_hours")
DEPLOY_MODE=$(get_metadata "deploy_mode")
PROJECT_ID=$(get_project_id)

BRANCH="${BRANCH:-main}"
TIMEOUT_HOURS="${TIMEOUT_HOURS:-4}"
DEPLOY_MODE="${DEPLOY_MODE:-false}"

if [[ -z "$TASK" ]]; then
    log "ERROR: No task specified in instance metadata."
    shutdown_instance
fi

if [[ -z "$REPO" ]]; then
    log "ERROR: No repo specified in instance metadata."
    shutdown_instance
fi

log "Task: $TASK"
log "Repo: $REPO"
log "Branch: $BRANCH"
log "Issue: ${ISSUE_NUM:-none}"
log "PR: ${PR_NUM:-none}"
log "Timeout: ${TIMEOUT_HOURS}h"
log "Deploy mode: $DEPLOY_MODE"

# ---------------------------------------------------------------------------
# Set auto-shutdown timer (cost safety net)
# ---------------------------------------------------------------------------

TIMEOUT_SECONDS=$((TIMEOUT_HOURS * 3600))
log "Setting auto-shutdown timer: ${TIMEOUT_HOURS}h (${TIMEOUT_SECONDS}s)"
(
    sleep "$TIMEOUT_SECONDS"
    log "TIMEOUT: Auto-shutdown after ${TIMEOUT_HOURS}h"
    post_github_comment "$ISSUE_NUM$PR_NUM" \
        "Agent task timed out after ${TIMEOUT_HOURS}h. Instance shutting down."
    shutdown_instance
) &
TIMER_PID=$!

# ---------------------------------------------------------------------------
# Install system dependencies
# ---------------------------------------------------------------------------

log "Installing system dependencies..."

export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y -qq \
    git \
    curl \
    software-properties-common \
    python3.12 \
    python3.12-venv \
    python3-pip \
    jq

# Install uv
log "Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Install GitHub CLI
log "Installing gh CLI..."
(type -p wget >/dev/null || apt-get install wget -y -qq) \
    && mkdir -p -m 755 /etc/apt/keyrings \
    && out=$(mktemp) \
    && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
    && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update -qq \
    && apt-get install gh -y -qq

# ---------------------------------------------------------------------------
# Pull secrets from GCP Secret Manager
# ---------------------------------------------------------------------------

log "Pulling secrets from Secret Manager..."

ANTHROPIC_API_KEY=$(get_secret "anthropic-api-key" "$PROJECT_ID")
GITHUB_TOKEN=$(get_secret "github-token" "$PROJECT_ID")
GOOGLE_API_KEY=$(get_secret "google-api-key" "$PROJECT_ID")
OPENAI_API_KEY=$(get_secret "openai-api-key" "$PROJECT_ID")
ARCADE_API_KEY=$(get_secret "arcade-api-key" "$PROJECT_ID")

if [[ -z "$GITHUB_TOKEN" ]]; then
    log "ERROR: Could not retrieve github-token from Secret Manager."
    shutdown_instance
fi

# Configure GitHub CLI auth
echo "$GITHUB_TOKEN" | gh auth login --with-token
log "GitHub CLI authenticated."

# ---------------------------------------------------------------------------
# Clone repo and set up environment
# ---------------------------------------------------------------------------

log "Cloning repository..."
mkdir -p "$WORKDIR"
git clone "$REPO" "$WORKDIR/repo"
cd "$WORKDIR/repo"
git checkout "$BRANCH"

log "Writing .env from secrets..."
cat > .env <<ENVEOF
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
GITHUB_TOKEN=${GITHUB_TOKEN}
GOOGLE_API_KEY=${GOOGLE_API_KEY}
OPENAI_API_KEY=${OPENAI_API_KEY}
ARCADE_API_KEY=${ARCADE_API_KEY}
ARCADE_USER_ID=agent@gcp-remote
ENVEOF
chmod 600 .env

log "Running uv sync..."
uv sync

# ---------------------------------------------------------------------------
# Post start notification
# ---------------------------------------------------------------------------

INSTANCE_NAME=$(get_instance_name)
post_github_comment "$ISSUE_NUM$PR_NUM" \
    "Agent task started on GCP instance \`$INSTANCE_NAME\`.
Task: $TASK
Branch: \`$BRANCH\`
Timeout: ${TIMEOUT_HOURS}h"

# ---------------------------------------------------------------------------
# Execute the task
# ---------------------------------------------------------------------------

log "Executing task..."
EXIT_CODE=0

if [[ "$DEPLOY_MODE" == "true" ]]; then
    # Deploy mode: poll for comments
    CMD=(uv run eco deploy)
    if [[ -n "$ISSUE_NUM" ]]; then
        CMD+=(--issue "$ISSUE_NUM")
    fi
    if [[ -n "$PR_NUM" ]]; then
        CMD+=(--pr "$PR_NUM")
    fi
    log "Running: ${CMD[*]}"
    "${CMD[@]}" 2>&1 | tee -a "$LOG_FILE" || EXIT_CODE=$?
else
    # Run mode: execute task once
    CMD=(uv run eco run "$TASK")
    if [[ -n "$ISSUE_NUM" ]]; then
        CMD+=(--issue "$ISSUE_NUM")
    fi
    if [[ -n "$PR_NUM" ]]; then
        CMD+=(--pr "$PR_NUM")
    fi
    log "Running: ${CMD[*]}"
    "${CMD[@]}" 2>&1 | tee -a "$LOG_FILE" || EXIT_CODE=$?
fi

# ---------------------------------------------------------------------------
# Post completion notification
# ---------------------------------------------------------------------------

if [[ "$EXIT_CODE" -eq 0 ]]; then
    STATUS="completed successfully"
else
    STATUS="failed (exit code: $EXIT_CODE)"
fi

log "Task $STATUS"

post_github_comment "$ISSUE_NUM$PR_NUM" \
    "Agent task $STATUS on instance \`$INSTANCE_NAME\`.
See logs with: \`eco remote logs $INSTANCE_NAME\`"

# ---------------------------------------------------------------------------
# Clean up and shut down
# ---------------------------------------------------------------------------

kill "$TIMER_PID" 2>/dev/null || true
log "Shutting down..."
shutdown_instance
