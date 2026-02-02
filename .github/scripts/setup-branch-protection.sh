#!/bin/bash
# Setup branch protection rules for a GitHub repository
# Usage: ./setup-branch-protection.sh [owner] [repo] [branch]
#   owner: GitHub username/org (default: auto-detected from git remote)
#   repo: Repository name (default: auto-detected from git remote)
#   branch: Branch to protect (default: main)
#
# Authentication: Uses GITHUB_TOKEN env var if set, otherwise uses gh CLI

set -e

# Get repository info from git remote or arguments
OWNER="${1:-}"
REPO="${2:-}"
BRANCH="${3:-main}"

if [ -z "$OWNER" ] || [ -z "$REPO" ]; then
  REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
  if [ -n "$REMOTE_URL" ]; then
    if [ -z "$OWNER" ]; then
      OWNER=$(echo "$REMOTE_URL" | sed -E 's/.*github\.com[:/]([^/]+)\/.*/\1/')
    fi
    if [ -z "$REPO" ]; then
      REPO=$(echo "$REMOTE_URL" | sed -E 's/.*github\.com[:/][^/]+\/([^/]+)\.git$/\1/' | sed -E 's/.*github\.com[:/][^/]+\/([^/]+)$/\1/')
    fi
  fi
fi

if [ -z "$OWNER" ] || [ -z "$REPO" ]; then
  echo "Error: Could not determine owner/repo. Please provide as arguments:"
  echo "  Usage: $0 [owner] [repo] [branch]"
  echo "  Example: $0 dpaiton agents main"
  exit 1
fi

echo "Setting up branch protection for: $OWNER/$REPO (branch: $BRANCH)"
echo ""

# Get authentication token
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

if [ -z "$GITHUB_TOKEN" ]; then
  echo "GITHUB_TOKEN not set. Checking gh CLI authentication..."
  if gh auth status &>/dev/null; then
    echo "✓ GitHub CLI is authenticated"
    GITHUB_TOKEN=$(gh auth token 2>/dev/null || echo "")
  else
    echo "❌ GitHub CLI is not authenticated"
    echo ""
    echo "Please authenticate using one of these methods:"
    echo ""
    echo "Option 1: Set GITHUB_TOKEN environment variable (for automation):"
    echo "  export GITHUB_TOKEN=your_token_here"
    echo "  $0 $OWNER $REPO $BRANCH"
    echo ""
    echo "Option 2: Authenticate with GitHub CLI:"
    echo "  gh auth login"
    echo "  $0 $OWNER $REPO $BRANCH"
    exit 1
  fi
fi

if [ -z "$GITHUB_TOKEN" ]; then
  echo "❌ Could not get GitHub token"
  exit 1
fi

# Setup branch protection using GitHub API
echo "Configuring branch protection rules..."
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json" \
  -d "{
    \"required_status_checks\": null,
    \"enforce_admins\": false,
    \"required_pull_request_reviews\": {
      \"required_approving_review_count\": 1,
      \"dismiss_stale_reviews\": true,
      \"require_code_owner_reviews\": true,
      \"require_last_push_approval\": false
    },
    \"restrictions\": null,
    \"required_linear_history\": false,
    \"allow_force_pushes\": false,
    \"allow_deletions\": false,
    \"block_creations\": false,
    \"required_conversation_resolution\": false
  }" \
  "https://api.github.com/repos/$OWNER/$REPO/branches/$BRANCH/protection" 2>&1)

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
  echo "✓ Branch protection rules configured successfully!"
  echo ""
  echo "Rules enabled:"
  echo "  ✓ Require pull request reviews before merging"
  echo "  ✓ Require 1 approving review"
  echo "  ✓ Require review from Code Owners"
  echo "  ✓ Dismiss stale reviews when new commits are pushed"
  echo "  ✓ Prevent force pushes"
  echo "  ✓ Prevent branch deletion"
  echo ""
  echo "Agents can review PRs, but your approval (as code owner) is required to merge."
else
  echo "❌ Failed to configure branch protection (HTTP $HTTP_CODE)"
  echo ""
  echo "$BODY" | head -10
  echo ""
  echo "If you see a 403 error, branch protection requires:"
  echo "  • A public repository, or"
  echo "  • A private repository on GitHub Pro/Team/Enterprise"
  echo ""
  echo "To set up manually: https://github.com/$OWNER/$REPO/settings/branches"
  exit 1
fi
