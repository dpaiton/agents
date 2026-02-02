#!/bin/bash
# Script to set up branch protection rules for main branch
# Run this after: gh auth login

echo "Setting up branch protection rules for main branch..."

gh api repos/dpaiton/agents/branches/main/protection -X PUT \
  -f required_status_checks=null \
  -f enforce_admins=false \
  -f required_pull_request_reviews='{
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "require_last_push_approval": false
  }' \
  -f restrictions=null \
  -f required_linear_history=false \
  -f allow_force_pushes=false \
  -f allow_deletions=false \
  -f block_creations=false \
  -f required_conversation_resolution=false

echo "Branch protection rules configured!"
echo ""
echo "Rules enabled:"
echo "  ✓ Require pull request reviews before merging"
echo "  ✓ Require 1 approving review"
echo "  ✓ Require review from code owners (you must approve)"
echo "  ✓ Dismiss stale reviews when new commits are pushed"
echo "  ✓ Prevent force pushes"
echo "  ✓ Prevent branch deletion"
echo ""
echo "Agents can review PRs, but your approval (as code owner) is required to merge."
