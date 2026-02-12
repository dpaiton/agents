# Multi-Agent Orchestration System

A comment-driven development framework that coordinates 12 specialized AI agents to build software through GitHub issues and pull requests.

**Core concept:** Comment on a GitHub issue or PR → Run `sync` → Agents classify intent, execute tasks in parallel (edit issues, push code, update PRs), resolve comment threads, and post summaries.

---

## Quick Start

```bash
git clone https://github.com/dpaiton/agents.git && cd agents
uv sync                          # Install dependencies
cp .env.example .env             # Configure API keys (edit the file)
python authorize_arcade.py       # Authorize GitHub OAuth tools
sync --help                      # See available commands
sync --dry-run                   # Preview without executing
```

---

## CLI Commands

The system provides both **standard** and **economy** modes. Prepend `eco` to any command (e.g., `eco sync`) to use smaller, cheaper models for cost-efficient execution.

### Core Workflows

#### `sync` - Process GitHub Comments (Primary Workflow)
Fetches unresolved comments on issues/PRs, classifies intent, executes actions in parallel, resolves threads, posts summary.

```bash
sync                        # Process all unresolved comments
sync --issue 42             # Process specific issue
sync --pr 18                # Process specific PR
sync --dry-run              # Show plan without executing
sync comments               # Process comments only (skip worktree cleanup)
sync worktrees              # Clean merged worktrees only
```

#### `run` - Direct Task Execution
Execute a task through the orchestration pipeline without requiring a GitHub comment.

```bash
run "Add input validation"  # Route and execute task
run --issue 42              # Act on specific issue
run --dry-run               # Show execution plan
```

#### `deploy` - Long-Running Watch Mode
Deploy an agent that continuously monitors for new comments.

```bash
deploy --issue 42 --watch   # Watch issue for new comments
deploy --pr 18 --watch      # Watch PR for new comments
deploy --dry-run            # Preview deployment
```

### Remote Execution

#### `remote` - GCP Instance Management
Run agents on Google Cloud Platform with automatic shutdown.

```bash
remote run --issue 42       # Launch remote agent on GCP
remote status               # List running instances
remote logs <instance>      # Stream instance logs
remote stop <instance>      # Terminate instance
```

### Monitoring & Cost

#### `cost` - Token Usage Tracking
```bash
cost estimate "task"        # Estimate cost before execution
cost history                # Show usage by day
cost history --pr 18        # Filter by PR number
cost log --model sonnet --input-tokens 1500 --output-tokens 800 --command route
```

#### `status` - Running Agent Monitor
```bash
status                      # Show active agents and token usage
status --all                # Show all runs (not just active)
```

### Evaluation & Review

#### `judge` - Evaluate Outputs Using Rubrics
```bash
judge --response r.txt --reference ref.txt --rubric code_review
judge --provider anthropic --provider google   # Multi-model ensemble
```

#### `review` - Generate Review Prompts
```bash
review --diff <(git diff main)  # Create structured review prompt
review --diff -                 # Read diff from stdin
```

#### `rubric` - Manage Evaluation Rubrics
```bash
rubric list                     # List available rubrics
rubric show code_review         # Show rubric details
```

### Utility Commands

#### `route` - Classify and Route Tasks
```bash
route "Add login feature"   # Determine task type and agent sequence
route "Fix bug" --format json
```

#### `test` - Run Test Suite
```bash
test                        # Run all tests
test --integration          # Run integration tests only
```

**Additional tools:**
- Linting: `uv run ruff check .`
- Unit tests: `uv run pytest`
- Integration tests: `uv run pytest -m integration`

---

## Agent System

The orchestration framework coordinates **12 specialized agents**, each with focused expertise and clear constraints.

### Coordination Agents

| Agent | Role | Model | Key Responsibilities |
|-------|------|-------|---------------------|
| **Orchestrator** | Routes tasks to specialists | Sonnet | Analyzes context, decomposes multi-step work, coordinates agent sequences. Cannot write code. |
| **Project Manager** | Coordinates tasks, estimates costs | Haiku | Runs `eco sync`, builds epics, tracks dependencies, maintains documentation accuracy. |
| **Reviewer** | PR evaluation | Sonnet | Reviews against rubrics (correctness, testing, readability, consistency, scope). Cannot modify code. |
| **Judge** | Output quality evaluation | Opus | LLM-as-judge ensemble evaluation, debiased pairwise comparison, reasoning before scores. |

### Design & Architecture

| Agent | Role | Model | Key Responsibilities |
|-------|------|-------|---------------------|
| **Designer** | UI/UX design | Sonnet | Wireframes, design specs, minimalist principles. Cannot write production code. |
| **Architect** | System architecture | Sonnet | API specs, system design, tech selection. Follows UNIX philosophy. Cannot implement. |

### Engineering Specialists

| Agent | Role | Model | Key Responsibilities |
|-------|------|-------|---------------------|
| **Backend Engineer** | Data & APIs | Sonnet | Databases, pipelines, REST/gRPC/GraphQL APIs. Cannot write frontend code. |
| **Frontend Engineer** | UI & UX implementation | Sonnet | React/Vue/Svelte components, responsive/accessible interfaces. Cannot write backend logic. |
| **ML Engineer** | Machine learning systems | Sonnet/Opus | Model training, prompt engineering, experiment tracking (W&B, MLFlow). |
| **Infrastructure Engineer** | Deployment & operations | Sonnet | CI/CD, containers (Docker/K8s), monitoring (Grafana/Prometheus). Cannot modify app code. |
| **Integration Engineer** | Cross-cutting concerns | Sonnet | E2E tests, API compatibility, glue code. Ensures components work together. |
| **Performance Engineer** | Testing & optimization | Sonnet | TDD (writes tests first), performance profiling, benchmarking. Cannot write implementation. |

### Routing Logic

Tasks are automatically routed based on keywords and context:

- **Features** → Architect → Performance Engineer → Orchestrator (picks specialist)
- **Bugs** → Performance Engineer (regression test) → Orchestrator (picks specialist) → Reviewer
- **Design** → Designer
- **Infrastructure** → Architect → Infrastructure Engineer → Reviewer
- **Performance** → Performance Engineer → Orchestrator

See [routing documentation](.claude/skills/route-task/SKILL.md) for detailed patterns.

---

## Documentation

### Project Guidance
- **[CLAUDE.md](CLAUDE.md)** - Agent instructions and 16 core principles
- **[Environment Setup](.env.example)** - Required environment variables

### Agent Definitions
All 12 agent role definitions with personalities, constraints, and tools:
- [`.claude/agents/`](.claude/agents/) - Individual agent markdown files

### Skills (Reusable Capabilities)
- [Create Issue](.claude/skills/create-issue/SKILL.md) - Standardized GitHub issue creation
- [Implement Feature](.claude/skills/implement-feature/SKILL.md) - TDD green phase (make tests pass)
- [Write Tests](.claude/skills/write-tests/SKILL.md) - TDD red phase + performance analysis
- [Route Task](.claude/skills/route-task/SKILL.md) - Task classification and routing logic
- [Evaluate](.claude/skills/evaluate/SKILL.md) - LLM-as-judge evaluation
- [Review PR](.claude/skills/review-pr/SKILL.md) - Pull request review process

### Architecture & Design
- [Agent Roles](docs/architecture/agent-roles.md) - Detailed agent responsibilities
- [MoE Routing](docs/architecture/moe-routing.md) - Mixture-of-Experts routing patterns

### Evaluation & Quality
- [Rubrics](docs/evaluation/rubrics.md) - Evaluation criteria and scoring
- [Judge Calibration](docs/evaluation/judge-calibration.md) - LLM-as-judge methodology
- [Bias Awareness](docs/evaluation/bias-awareness.md) - Bias mitigation strategies

### Rubrics
- [Code Review Rubric](.claude/skills/review-pr/rubrics/code-review-rubric.md)
- [General Evaluation Rubric](.claude/skills/evaluate/rubrics/general-rubric.md)
- [Bias Awareness Checklists](.claude/skills/evaluate/rubrics/bias-awareness.md)

---

## Prerequisites

- **Python 3.12+** (project uses 3.13 via `.python-version`)
- **[uv](https://docs.astral.sh/uv/)** - Fast Python package manager
- **[gh CLI](https://cli.github.com/)** - GitHub command-line tool (`gh auth login`)
- **API Keys:**
  - Anthropic API key (required) - Claude models
  - Arcade API key (required) - OAuth for GitHub tools
  - Google/OpenAI API keys (optional) - Alternative model backends

---

## Installation

### 1. Install Dependencies

```bash
uv sync
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in required values:

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Claude API access | ✓ |
| `ARCADE_API_KEY` | OAuth tool authorization | ✓ |
| `ARCADE_USER_ID` | Agent identity (default: `agent@local`) | |
| `GITHUB_REPO` | Target repository (e.g., `dpaiton/agents`) | ✓ |
| `GITHUB_TOKEN` | GitHub personal access token | ✓ |
| `ORCHESTRATOR_AGENT_MODEL` | Orchestrator/Architect model | |
| `CODING_AGENT_MODEL` | Engineer models | |
| `GITHUB_AGENT_MODEL` | GitHub agent model | |
| `GOOGLE_API_KEY` | Gemini models (optional) | |
| `OPENAI_API_KEY` | GPT models (optional) | |

### 3. Authorize GitHub Tools

```bash
python authorize_arcade.py          # All services
python authorize_arcade.py github   # GitHub only
```

This triggers OAuth flows for 7 GitHub write tools. Follow the printed URLs to complete authorization.

### 4. Optional: Branch Protection

```bash
./.github/scripts/setup-branch-protection.sh
```

Requires public repo or GitHub Pro/Team/Enterprise for private repos.

---

## Development Workflows

### Adding a Feature

1. **Create issue** with `[Feature]` prefix and acceptance criteria
2. **Architect** designs system architecture and API specs
3. **Performance Engineer** writes failing tests (TDD red phase)
4. **Orchestrator** routes to appropriate specialist (Backend/Frontend/ML/Infrastructure)
5. **Specialist Engineer** implements until tests pass (TDD green phase)
6. **Reviewer** evaluates PR against rubric
7. **Human** (code owner) gives final approval and merges

### Fixing a Bug

1. **Performance Engineer** writes failing regression test
2. **Orchestrator** routes to appropriate specialist
3. **Specialist Engineer** implements fix
4. Verify all tests pass including regression test

### Reviewing a PR

**Reviewer** agent evaluates using 5 criteria (each scored 0-10):

1. **Correctness** - Does the code do what it claims?
2. **Test Coverage** - Are edge cases and error states tested?
3. **Readability** - Clear structure, good naming, appropriate comments?
4. **Consistency** - Follows existing patterns and conventions?
5. **Scope** - Minimal, focused, single responsibility?

Bias checklist flags: over-engineering, missing error handling, unclear naming, unnecessary dependencies.

---

## Git Workflow

**Golden Rules:**
- ✅ **Always rebase, never merge** (`git rebase origin/main`)
- ✅ **Small, isolated commits** (one logical change per commit)
- ✅ **Minimal PRs** (single idea/component, reviewable in isolation)
- ✅ **Descriptive commit messages** (commit history is documentation)

**Branch Naming:**
```
<type>/<description>

Examples:
  feat/add-input-validation
  fix/null-pointer-in-parser
  infra/ci-pipeline-setup
  docs/update-readme
```

**PR Title Prefixes:**
- `[Feature]` - New functionality
- `[Bug]` - Bug fix
- `[Test]` - Test-only changes
- `[Infrastructure]` - CI, tooling, deployment
- `[Docs]` - Documentation
- `[Epic]` - High-level tracking issue

---

## Architecture

```
User comments on issue/PR
    ↓
sync (fetch unresolved comments via gh CLI)
    ↓
Classify intent (pattern match → LLM fallback)
    ↓
Parallel execution:
    ├─ gh issue edit (update issue body)
    ├─ git commit + push (change PR code)
    ├─ gh pr edit (update PR description)
    └─ gh comment (reply to questions)
    ↓
Resolve comment threads (GraphQL)
    ↓
Post summary

Execution Modes:
  • Local:  sync / run / deploy
  • Remote: remote run (GCP with auto-shutdown)
  • CI:     GitHub Actions (@claude mentions)
```

**Key Principles:**
1. **Deterministic scaffolding** around probabilistic models
2. **Code before prompts** - Use bash/CLI tools when possible
3. **UNIX philosophy** - Do one thing well, composable tools
4. **TDD-first** - Tests before implementation
5. **Comment-driven** - GitHub as coordination layer
6. **Parallel execution** - Independent tasks run concurrently

See [CLAUDE.md](CLAUDE.md) for all 16 principles.

---

## Project Structure

```
agents/
├── .claude/
│   ├── agents/              # 12 agent role definitions (.md)
│   └── skills/              # 6 reusable skills with rubrics
│
├── .github/
│   ├── workflows/           # CI: @claude mentions, PR reviews
│   └── scripts/             # Branch protection setup
│
├── orchestration/           # Core engine
│   ├── cli.py              # CLI entry point
│   ├── sync_engine.py      # Comment-driven sync
│   ├── router.py           # Task routing logic
│   ├── execution.py        # Execution engine
│   ├── judge.py            # LLM-as-judge evaluation
│   ├── backends.py         # Multi-model abstraction
│   ├── cost.py             # Token tracking
│   ├── remote.py           # GCP deployment
│   ├── prompts/            # Prompt definitions
│   ├── rubrics/            # Evaluation rubrics
│   └── tests/              # Comprehensive test suite
│
├── docs/
│   ├── architecture/       # System design
│   └── evaluation/         # Judge & rubrics
│
├── deployment/
│   └── gcp/                # Cloud configs
│
├── authorize_arcade.py     # OAuth authorization
├── CLAUDE.md               # Agent instructions
├── README.md               # This file
└── pyproject.toml          # Dependencies
```

---

## Testing

```bash
# Unit tests
uv run pytest

# Integration tests
uv run pytest -m integration
# or
test --integration

# Specific test file
uv run pytest orchestration/tests/test_router.py -v

# With coverage
uv run pytest --cov=orchestration

# Linting
uv run ruff check .
```

**Test Organization:**
- `orchestration/tests/` - Unit tests (router, config, execution, judge, cost)
- `orchestration/tests/integration/` - E2E pipeline and sync tests
- Markers: `@pytest.mark.integration` for integration tests

---

## Contributing

1. **Read the principles** - [CLAUDE.md](CLAUDE.md) defines the project philosophy
2. **Follow the workflow** - TDD, small PRs, rebase not merge
3. **Use the agents** - Comment on issues/PRs and let agents help
4. **Write tests first** - Red → Green → Refactor
5. **Keep PRs minimal** - Single idea, reviewable in isolation

All PRs require approval from `@dpaiton` (see [CODEOWNERS](CODEOWNERS)).

---

## License

See repository for license information.

---

## Links

- **Repository:** https://github.com/dpaiton/agents
- **Issues:** https://github.com/dpaiton/agents/issues
- **Pull Requests:** https://github.com/dpaiton/agents/pulls

For questions or support, open an issue.
