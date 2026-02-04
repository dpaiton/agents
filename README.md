# agents

Multi-agent orchestration system that uses GitHub issues and PR comments as the coordination layer.

## Overview

This project coordinates AI agents -- orchestrator, engineer, test-writer, reviewer, issue-creator, and judge -- to develop software through comment-driven development. You write a comment on a GitHub issue or PR, run `sync` (or `eco sync` for economy mode with smaller, cheaper models), and agents classify intent, execute tasks in parallel (editing issues, pushing code, updating PRs), resolve comment threads, and post a summary. The system wraps deterministic scaffolding around probabilistic models, preferring code and CLI tools over prompts and agents whenever possible.

## Quick Start

```bash
git clone https://github.com/dpaiton/agents.git && cd agents
uv sync
cp .env.example .env  # Fill in API keys
sync --help
sync --dry-run
```

## Prerequisites

- **Python 3.12+** (project uses 3.13 by default via `.python-version`)
- **[uv](https://docs.astral.sh/uv/)** -- Python package and project manager
- **[gh CLI](https://cli.github.com/)** -- GitHub command-line tool, authenticated via `gh auth login`
- **API keys:**
  - Anthropic (required) -- for Claude-based agents
  - Arcade (required) -- for OAuth-based GitHub tool authorization
  - Google / OpenAI (optional) -- for alternative model backends

## Installation

1. **Install dependencies:**

   ```bash
   uv sync
   ```

2. **Configure environment variables:**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and fill in the required values. See the [Environment Variables](#environment-variables) section for the full list.

3. **Authorize GitHub tools via Arcade:**

   ```bash
   python authorize_arcade.py          # Authorize all services
   python authorize_arcade.py github   # Authorize GitHub only
   ```

   This triggers OAuth flows for 7 GitHub write tools (CreateBranch, CreatePullRequest, UpdatePullRequest, MergePullRequest, CreateIssueComment, CreateIssue, UpdateIssue). Follow the printed URLs to complete authorization.

4. **Set up branch protection (optional):**

   ```bash
   ./.github/scripts/setup-branch-protection.sh
   ```

   Requires a public repo or GitHub Pro/Team/Enterprise for private repos.

## Running Agents

> **Economy mode:** Prepend `eco` to any command (e.g., `eco sync`, `eco run`) to use smaller, cheaper models for cost-efficient execution. The standard commands use the default (larger) models configured in your environment variables.

### `sync` -- Primary workflow

Fetches unresolved comments on issues and PRs, classifies intent, executes actions in parallel, resolves threads, and posts a summary.

```bash
sync                         # Process all unresolved comments
sync --issue 42              # Process comments on a specific issue
sync --pr 18                 # Process comments on a specific PR
sync --dry-run               # Show the execution plan without acting
```

### `run` -- Direct task execution

Runs a task through the orchestration pipeline without requiring a GitHub comment.

```bash
run "Add input validation"
run --issue 42
```

### `deploy` -- Long-running watch mode

Deploys an agent that continuously watches an issue or PR for new comments.

```bash
deploy --issue 42 --watch
```

### `remote run` -- GCP deployment

Runs an agent remotely on Google Cloud with automatic shutdown.

```bash
remote run --issue 42
```

### `cost` / `status` -- Monitoring

```bash
cost --pr 18                 # Estimate token cost for a PR
status                       # Show running agents and token usage
```

### Testing and linting

```bash
uv run pytest                           # Unit tests
uv run pytest -m integration            # Integration tests
test --integration                      # Same, via CLI
uv run ruff check .                     # Linter
```

## Development Workflows

### Adding a feature

1. Create a GitHub issue using the `[Feature]` title prefix and the issue body template (see [Creating an issue](#creating-an-issue)).
2. The **test-writer** agent writes failing tests that define the acceptance criteria.
3. The **engineer** agent implements the feature until tests pass.
4. The **reviewer** agent evaluates the PR against the rubric (see [Reviewing a PR](#reviewing-a-pr)).
5. A human (code owner) gives final approval and merges.

### Fixing a bug

1. Reproduce the bug with a failing test -- the **test-writer** writes a minimal test that demonstrates the failure.
2. The **engineer** implements the fix.
3. Verify all tests pass, including the new regression test.

### Reviewing a PR

The **reviewer** agent evaluates PRs using a rubric with 5 criteria, each scored out of 10:

1. **Correctness** -- Does the code do what it claims?
2. **Test coverage** -- Are edge cases tested?
3. **Readability** -- Is the code clear and well-structured?
4. **Consistency** -- Does it follow existing patterns?
5. **Scope** -- Is the PR minimal and focused?

The reviewer also applies a bias checklist to flag common issues: over-engineering, missing error handling, unclear naming, and unnecessary dependencies.

### Creating an issue

Use the `create-issue` skill or `gh issue create` directly. Follow these conventions:

**Title prefixes** (required):

- `[Feature]` -- New functionality
- `[Bug]` -- Bug fix
- `[Test]` -- Test-only changes
- `[Infrastructure]` -- Repo setup, CI, tooling
- `[Docs]` -- Documentation
- `[Epic]` -- High-level tracking issue

**Labels:**

| Label | Use when |
|---|---|
| `epic` | Top-level tracking epic |
| `infrastructure` | Repo structure, CI, tooling |
| `evaluation` | LLM-as-judge evaluation framework |
| `orchestration` | Multi-agent orchestration and routing |
| `agent` | Agent definitions and configuration |
| `tdd` | Test-driven development workflow |
| `placeholder` | Future work, not yet actionable |
| `priority:high` | Must be done first |
| `priority:medium` | Important but not blocking |
| `priority:low` | Nice to have |

**Example:**

```bash
gh issue create \
  --title "[Feature] Add input validation for user forms" \
  --label "agent,priority:medium" \
  --body "$(cat <<'EOF'
## Summary
Add server-side input validation to prevent malformed data.

## Acceptance Criteria
- [ ] All user inputs are validated before processing
- [ ] Validation errors return descriptive messages
- [ ] Unit tests cover all validation rules

## Verification
uv run pytest tests/test_validation.py -v
EOF
)"
```

## Git Workflow

- **Always rebase, never merge.** Use `git rebase origin/main` to resolve conflicts. This keeps PR diffs clean and reviewable.
- **Small, isolated commits.** Each commit should be one logical change. If a commit message needs "and", split it.
- **Minimal PRs.** A PR should do one thing. If an issue requires changes to unrelated areas, open multiple PRs and reference the issue from each.
- **PR scope test:** Does this PR address a single idea or component that can be reviewed and tested in isolation? If not, split it.
- **Commit history is documentation.** Write descriptive commit messages. Future readers will `git log` before they read docs.

**Branch naming:**

```
<type>/<description>

feat/add-input-validation
fix/null-pointer-in-parser
infra/ci-pipeline-setup
docs/readme
```

Types: `feat/`, `fix/`, `infra/`, `docs/`

## Agent Roles

| Agent | Role | Model | Personality |
|---|---|---|---|
| orchestrator | Routes tasks to appropriate agents | sonnet | Strategic, decisive |
| engineer | Writes production code | sonnet | Pragmatic, minimal |
| test-writer | Writes tests before implementation (TDD) | sonnet | Thorough, skeptical |
| reviewer | Reviews PRs against rubric | sonnet | Fair, evidence-based |
| issue-creator | Creates and manages GitHub issues | haiku | Organized, consistent |
| judge | Evaluates output quality (LLM-as-judge) | opus | Methodical, impartial |

Agent models are configured via environment variables (`ORCHESTRATOR_AGENT_MODEL`, `GITHUB_AGENT_MODEL`, `CODING_AGENT_MODEL`).

## Architecture

```
User comments on issue/PR
    |
    v
sync (fetches unresolved comments via gh CLI)
    |
    v
Classify intent per comment (pattern match first, LLM fallback)
    |
    v
Parallel execution:
    |-- gh issue edit (update issue body)
    |-- git commit + push (change PR code)
    |-- gh pr edit (update PR description)
    +-- gh comment (reply to questions)
    |
    v
Resolve comment threads (GraphQL resolveReviewThread)
    |
    v
Post summary

Execution modes:
    Local:  sync / run / deploy
    Remote: remote run (GCP, auto-shutdown)
    CI:     GitHub Actions (@claude mentions)
```

**authorize_arcade.py** handles OAuth-based service authorization:

1. Loads config from `.env` via `python-dotenv`
2. Iterates over a `SERVICES` dictionary (each service defines `verify_tool`, `extract_name`, `auth_tools`)
3. Authorizes each tool via `Arcade.tools.authorize()` (triggers OAuth flows)
4. Verifies the connection by executing the service's verify tool

## Project Structure

```
agents/
|-- .claude/
|   +-- skills/
|       +-- create-issue/        # Skill for creating standardized GitHub issues
|           +-- SKILL.md
|-- .github/
|   |-- scripts/
|   |   +-- setup-branch-protection.sh  # Configure branch protection rules
|   +-- workflows/
|       |-- claude.yml                  # CI: respond to @claude mentions
|       +-- claude-code-review.yml      # CI: automated PR code review
|-- authorize_arcade.py          # OAuth authorization for GitHub write tools
|-- CLAUDE.md                    # Agent instructions and project principles
|-- CODEOWNERS                   # Requires @dpaiton approval on all PRs
|-- pyproject.toml               # Project metadata and dependencies
|-- uv.lock                      # Locked dependency versions
|-- .env.example                 # Template for environment variables
|-- .gitignore                   # Standard Python gitignore
+-- README.md                    # This file
```

## Environment Variables

Configure these in `.env` (copy from `.env.example`):

| Variable | Description | Required |
|---|---|---|
| `ARCADE_API_KEY` | Arcade API key for OAuth-based tool authorization | Yes |
| `ARCADE_USER_ID` | Agent identity for Arcade (defaults to `agent@local`) | No |
| `GITHUB_REPO` | Target GitHub repository (e.g., `dpaiton/agents`) | Yes |
| `GITHUB_TOKEN` | GitHub personal access token for API calls | Yes |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models | Yes |
| `ORCHESTRATOR_AGENT_MODEL` | Model for the orchestrator agent | No |
| `GITHUB_AGENT_MODEL` | Model for the GitHub agent | No |
| `CODING_AGENT_MODEL` | Model for the coding agent | No |
| `GOOGLE_API_KEY` | Google API key (optional, for Gemini models) | No |
| `OPENAI_API_KEY` | OpenAI API key (optional, for GPT models) | No |

## Principles

This project follows 16 principles (see `CLAUDE.md` for full details):

1. **User Centricity** -- Built around user goals, not tooling.
2. **The Foundational Algorithm** -- Observe, Think, Plan, Build, Execute, Verify, Learn.
3. **Clear Thinking First** -- Clarify the problem before writing the prompt.
4. **Scaffolding > Model** -- System architecture matters more than which model you use.
5. **Deterministic Infrastructure** -- AI is probabilistic; infrastructure should not be.
6. **Code Before Prompts** -- If a bash script solves it, do not use AI.
7. **Spec / Test / Evals First** -- Write tests before code. Measure if it works.
8. **UNIX Philosophy** -- Do one thing well. Composable tools. Text interfaces.
9. **ENG / SRE Principles** -- Version control, automation, monitoring.
10. **CLI as Interface** -- CLI is faster, more scriptable, and more reliable than GUIs.
11. **Goal > Code > CLI > Prompts > Agents** -- The decision hierarchy.
12. **Skill Management** -- Modular capabilities that route intelligently based on context.
13. **Memory System** -- Everything worth knowing gets captured.
14. **Agent Personalities** -- Different work needs different approaches.
15. **Science as Meta-Loop** -- Hypothesis, Experiment, Measure, Iterate.
16. **Permission to Fail** -- Say "I don't know" instead of guessing. Escalate when uncertain.
