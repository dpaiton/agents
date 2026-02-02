# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Arcade/MCP authorization and orchestration project for integrating with GitHub services. It authorizes OAuth-based write permissions for GitHub tools (branches, PRs, issues) via the Arcade API. The project is part of a larger multi-agent system with orchestrator, GitHub, and coding agent roles configured via environment variables.

## Commands

```bash
# Install dependencies
uv sync

# Run authorization for all configured services
python authorize_arcade.py

# Authorize a specific service only
python authorize_arcade.py github

# Set up GitHub branch protection rules (auto-detects repo from git remote)
./.github/scripts/setup-branch-protection.sh
```

No test framework or linter is currently configured.

## Architecture

**authorize_arcade.py** is the single entry point. It follows this pattern:

1. Loads configuration from `.env` via `python-dotenv`
2. Iterates over a `SERVICES` dictionary where each service defines:
   - `verify_tool`: an Arcade tool to test the connection (e.g., `Github.WhoAmI`)
   - `extract_name`: a lambda to parse verification output
   - `auth_tools`: list of Arcade tools requiring write authorization
3. Authorizes each tool via `Arcade.tools.authorize()`, which triggers OAuth flows
4. Verifies the connection by executing the service's verify tool

The GitHub service authorizes 7 write tools: CreateBranch, CreatePullRequest, UpdatePullRequest, MergePullRequest, CreateIssueComment, CreateIssue, UpdateIssue.

## Environment Configuration

Required in `.env`:
- `ARCADE_API_KEY` - Arcade API key for authentication
- `ARCADE_USER_ID` - Agent identity (defaults to "agent@local")

Also configured:
- `GITHUB_REPO`, `GITHUB_TOKEN` - GitHub integration
- `ORCHESTRATOR_AGENT_MODEL`, `GITHUB_AGENT_MODEL`, `CODING_AGENT_MODEL` - Model selection for different agent roles
