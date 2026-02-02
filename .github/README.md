# GitHub Configuration

This directory contains GitHub-specific configuration and automation scripts.

## Structure

- `scripts/` - Setup and automation scripts for GitHub repository configuration
  - `setup-branch-protection.sh` - Configures branch protection rules for the main branch

## Usage

To set up branch protection rules:

```bash
gh auth login  # If not already authenticated
./.github/scripts/setup-branch-protection.sh
```
