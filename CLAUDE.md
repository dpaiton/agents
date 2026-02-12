# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Principles

Follow these in order of priority:

1. **User Centricity** — Built around user goals, not tooling.
2. **The Foundational Algorithm** — Observe → Think → Plan → Build → Execute → Verify → Learn.
3. **Clear Thinking First** — Clarify the problem before writing the prompt.
4. **Scaffolding > Model** — System architecture matters more than which model you use.
5. **Deterministic Infrastructure** — AI is probabilistic; infrastructure shouldn't be. Use templates and patterns.
6. **Code Before Prompts** — If a bash script solves it, don't use AI.
7. **Spec / Test / Evals First** — Write tests before code. Measure if it works.
8. **UNIX Philosophy** — Do one thing well. Composable tools. Text interfaces.
9. **ENG / SRE Principles** — Version control, automation, monitoring. Treat AI infra like production.
10. **CLI as Interface** — CLI is faster, more scriptable, and more reliable than GUIs.
11. **Goal → Code → CLI → Prompts → Agents** — The decision hierarchy.
12. **Skill Management** — Modular capabilities that route intelligently based on context.
13. **Memory System** — Everything worth knowing gets captured. History feeds future context.
14. **Agent Personalities** — Different work needs different approaches.
15. **Science as Meta-Loop** — Hypothesis → Experiment → Measure → Iterate.
16. **Permission to Fail** — Say "I don't know" instead of guessing. Escalate when uncertain.

## Decision Hierarchy

When solving any problem, work down this list and stop at the simplest level that works:

```
Goal → Code → CLI → Prompts → Agents
```

1. Clarify the goal (what does the user need?)
2. Write code (Python, bash — deterministic solution)
3. Use CLI tools (`gh`, `git`, `pytest`, `ruff`)
4. Write prompts (only when judgment is needed)
5. Invoke agents (last resort, for multi-step reasoning)

## Working in This Repository

**CRITICAL: When the user asks you to perform work in this repository, you MUST use the existing agent orchestration system. Do NOT perform the work directly.**

### How to Handle User Requests

1. **Comment on the appropriate GitHub issue/PR** with the user's request
2. **Run the orchestration CLI** to deploy the appropriate named agent
3. **Let the specialized agent** perform the work using its defined skills

### Agent Deployment Commands

```bash
# For general tasks - let orchestrator route to the right specialist
agents run "task description"
agents run --issue <number>

# For issue/PR monitoring - deploy long-running agent
agents deploy --issue <number> --watch
agents deploy --pr <number> --watch

# For syncing comments - process all unresolved comments
agents sync                    # All open issues/PRs
agents sync --issue <number>   # Specific issue
agents sync --pr <number>      # Specific PR
```

### Named Agent Types (see README for full details)

**Coordination:**
- `orchestrator` - Routes tasks to specialists, decomposes multi-step work
- `project-manager` - Coordinates tasks, estimates costs, runs sync
- `reviewer` - PR evaluation against rubrics
- `judge` - Output quality evaluation via LLM-as-judge

**Design & Architecture:**
- `designer` - UI/UX design, wireframes, design specs
- `architect` - System architecture, API specs, tech selection

**Engineering Specialists:**
- `backend-engineer` - Databases, APIs, data pipelines
- `frontend-engineer` - React/Vue/Svelte, responsive UIs
- `ml-engineer` - Model training, prompt engineering
- `infrastructure-engineer` - CI/CD, containers, monitoring
- `integration-engineer` - E2E tests, cross-cutting concerns
- `performance-engineer` - TDD (tests first), profiling, benchmarks

### Agent Skills (see `.claude/skills/` for details)

- `create-issue` - Standardized GitHub issue creation
- `implement-feature` - TDD green phase (make tests pass)
- `write-tests` - TDD red phase + performance analysis
- `route-task` - Task classification and routing logic
- `evaluate` - LLM-as-judge evaluation
- `review-pr` - Pull request review process

### Routing Examples

When user asks for work, route through the orchestration system:

- **"Add a new feature"** → Comment on issue → `agents run --issue <number>` → Orchestrator routes to Architect → Performance Engineer (tests) → Appropriate specialist
- **"Fix a bug"** → Comment on issue → `agents run --issue <number>` → Performance Engineer (regression test) → Orchestrator routes to specialist
- **"Review this PR"** → Comment on PR → `agents sync --pr <number>` → Reviewer evaluates against rubrics
- **"Design a UI"** → Comment on issue → `agents run --issue <number>` → Designer creates wireframes
- **"Set up CI/CD"** → Comment on issue → `agents run --issue <number>` → Architect → Infrastructure Engineer

### What NOT to Do

❌ **Do NOT directly implement code** when asked to perform work in this repository
❌ **Do NOT bypass the agent system** for software development tasks
❌ **Do NOT use your own Task tool** when specialized agents with skills are available
❌ **Do NOT perform multi-step work** without going through the orchestrator

### What TO Do

✅ **Comment on the relevant GitHub issue/PR** with the user's request
✅ **Use the CLI commands** (`agents run`, `agents sync`, `agents deploy`) to invoke specialized agents
✅ **Let the named agents** use their defined skills to perform the work
✅ **Monitor the output** and report results to the user

### Example Workflow

User: "Add input validation to the API"

**Correct approach:**
1. Identify or create issue for this work
2. Comment on issue: "@orchestrator: Add input validation to the API endpoints as described in acceptance criteria"
3. Run: `agents sync --issue <number>` or `agents run --issue <number>`
4. Orchestrator routes: Architect → Performance Engineer → Backend Engineer → Reviewer
5. Report results to user

**Incorrect approach:**
❌ Directly reading code files and implementing validation yourself
❌ Using your Task tool to spawn a generic agent
❌ Bypassing the specialized agent system

## Project Overview

Multi-agent orchestration meta-repository. Coordinates 12 specialized AI agents (orchestrator, architect, 6 engineering specialists, designer, reviewer, judge, project manager) to develop software with built-in evaluation.

**Primary interaction model:** Comment on GitHub issues and PRs, then run `agents sync`. Agents parse comments, act in parallel (edit issue bodies, push PR code, update descriptions), and resolve comment threads when done.

**IMPORTANT FOR CLAUDE CODE SESSIONS:** When working in this repository, always use the existing CLI (`agents run`, `agents sync`, `agents deploy`) to orchestrate and deploy the named agent types with their defined skills. Do NOT perform software development work directly—route it through the specialized agent system as outlined in the README and "Working in This Repository" section below.

Arcade/MCP authorization handles OAuth-based write permissions for GitHub tools via the Arcade API.

## Model Selection

**IMPORTANT: Always use standard models (Opus/Sonnet) by default. Do NOT use economy mode unless explicitly requested.**

- **Standard mode** (default): `agents <command>` — Uses Opus/Sonnet models as defined in `config.py`
- **Economy mode**: `eco <command>` or `agents --economy <command>` — Uses Haiku/cheaper models for cost efficiency
- **Model configuration**: See `orchestration/config.py` for `MODEL_TABLE` (standard) and `ECONOMY_MODEL_TABLE` (economy)

When spawning agents or running commands, use standard models unless the user explicitly requests economy mode.

## Commands

```bash
# Primary workflow: sync comments on issues/PRs
agents sync                     # Process all unresolved comments
agents sync --issue 42          # Just this issue
agents sync --pr 18             # Just this PR
agents sync --dry-run           # Show plan without executing

# Run a task through the orchestration pipeline
agents run "Add input validation"
agents run --issue 42

# Deploy an agent on an issue/PR (long-running)
agents deploy --issue 42 --watch

# Token cost estimation
agents cost --pr 18

# Show running agents and token usage
agents status

# Install dependencies
uv sync

# Run tests
uv run pytest                           # Unit tests
uv run pytest -m integration            # Integration tests
agents test --integration               # Same, via agents CLI

# Run linter
uv run ruff check .

# Run authorization for all configured services
python authorize_arcade.py

# Set up GitHub branch protection rules
./.github/scripts/setup-branch-protection.sh
```

## Architecture

Deterministic scaffolding around probabilistic models:

```
User comments on issue/PR
    → agents sync (fetches unresolved comments via gh CLI)
    → Classify intent per comment (pattern match first, LLM fallback)
    → Parallel execution:
        ├─ gh issue edit (update issue body)
        ├─ git commit + push (change PR code)
        ├─ gh pr edit (update PR description)
        └─ gh comment (reply to questions)
    → Resolve comment threads (GraphQL resolveReviewThread)
    → Post summary

Execution modes:
    Local:  agents sync / agents run / agents deploy
    Remote: agents remote run (GCP, auto-shutdown)
    CI:     GitHub Actions (@claude mentions)
```

**authorize_arcade.py** handles service auth:
1. Loads config from `.env` via `python-dotenv`
2. Iterates `SERVICES` dict (each has `verify_tool`, `extract_name`, `auth_tools`)
3. Authorizes tools via `Arcade.tools.authorize()` (triggers OAuth)
4. Verifies connection via each service's verify tool

## Git & PR Guidelines

- **Always rebase, never merge.** Use `git rebase origin/main` to resolve conflicts. This keeps PR diffs clean and reviewable.
- **Small, isolated commits.** Each commit should be one logical change. If a commit message needs "and", split it.
- **Minimal PRs.** A PR should do one thing. If an issue requires changes to unrelated areas, open multiple PRs and reference the issue from each. Prefer multiple small PRs that can be tested and reviewed independently over one large PR.
- **PR scope test:** Does this PR address a single idea or component that can be reviewed and tested in isolation? If not, split it.
- **Commit history is documentation.** Write descriptive commit messages. Future readers will `git log` before they read docs.

## Monorepo Structure

This repository uses a **monorepo** structure to host multiple projects alongside the core orchestration framework.

```
agents/
├── .claude/                      # Global orchestration agents and skills
│   ├── agents/                   # 12 core agent definitions
│   └── skills/                   # Reusable orchestration skills
├── orchestration/                # Core orchestration engine
├── projects/                     # Project-specific code (monorepo)
│   └── {project-name}/          # Each project has its own directory
│       ├── .claude/             # Project-specific agents and skills
│       │   ├── agents/          # Specialized agents for this project
│       │   └── skills/          # Project-specific skills
│       ├── src/                 # Project source code
│       ├── tests/               # Project tests
│       └── docs/                # Project documentation
└── CLAUDE.md                    # This file
```

**Routing Convention:**
- File paths in `projects/{project}/` automatically set project context
- Project-specific agents (in `projects/{project}/.claude/agents/`) are loaded for project work
- Global agents (in `.claude/agents/`) handle orchestration and cross-cutting concerns
- Use GitHub labels (e.g., `unity-space-sim`) to mark project-specific issues

## Unity Space Simulation Project

**Epic:** [Issue #65](https://github.com/dpaiton/agents/issues/65)
**Location:** `projects/unity-space-sim/`
**Project Board:** [Unity Space Simulation](https://github.com/users/dpaiton/projects/2)

### Overview

Build a 3D space game using Unity with a deterministic, LLM-orchestrated asset generation pipeline powered by Blender Python scripting and multi-agent coordination.

**Key Features:**
- Realistic aesthetic that feels believable (like GTA's approach to realism - fun first, plausible second)
- Blender Python pipeline for procedural asset generation
- Unity engine integration with C# components
- CI/CD automation for headless Blender rendering
- Quality guidelines (poly budgets, LOD levels, reasonable constraints)

### Phase Structure

| Phase | Issue | Focus | Status |
|-------|-------|-------|--------|
| **Meta Phase** | [#73](https://github.com/dpaiton/agents/issues/73) | Orchestration repo setup | In Progress |
| Phase 1 | [#74](https://github.com/dpaiton/agents/issues/74) | Foundation & documentation | Pending |
| Phase 1.5 | [#79](https://github.com/dpaiton/agents/issues/79) | MVP - Drivable ship demo | Pending |
| Phase 2 | [#75](https://github.com/dpaiton/agents/issues/75) | Blender pipeline scripts | Pending |
| Phase 3 | [#76](https://github.com/dpaiton/agents/issues/76) | Unity integration scripts | Pending |
| Phase 4 | [#77](https://github.com/dpaiton/agents/issues/77) | CI/CD automation | Pending |
| Phase 5 | [#78](https://github.com/dpaiton/agents/issues/78) | End-to-end testing | Pending |

### Quality Guidelines

**Art Direction:**
- **Style:** Believable sci-fi aesthetic (feels realistic without being a simulation)
- **Philosophy:** Gameplay and visual appeal first, then plausibility
- **Scale:** Consistent units (1 Unity unit = 1 meter for reference)
- **Approach:** Like GTA does driving - feels right, doesn't need to be accurate

**Technical Guidelines (flexible, not strict rules):**
- **Poly Budgets (targets):**
  - Small ships: ~5k tris (LOD0)
  - Medium ships: ~15k tris (LOD0)
  - Large ships: ~40k tris (LOD0)
  - *(Adjust based on gameplay needs and performance)*
- **LOD Levels:** 2-3 levels recommended for performance
- **Materials:** Whatever looks good and performs well

### Technical Stack

| Tool | Version | Purpose |
|------|---------|---------|
| **Unity** | 2022.3 LTS+ | Game engine and runtime |
| **Blender** | 3.6+ | 3D asset generation (headless mode) |
| **Python** | 3.10+ | Blender scripting (bpy API) and automation |
| **C#** | .NET Standard 2.1 | Unity scripting |
| **uv** | Latest | Python package management |
| **Git** | Latest | Version control |

### Project-Specific Agents

Located in `projects/unity-space-sim/.claude/agents/`:

| Agent | Role | Responsibilities |
|-------|------|------------------|
| **unity-asset-designer** | 3D asset design | Wireframes, design specs, believable sci-fi aesthetic |
| **blender-engineer** | Blender Python scripting | bpy API, procedural modeling, materials, LOD generation, FBX export |
| **unity-engineer** | Unity C# scripting | Asset import pipelines, component systems, scene management |
| **gamedev-integration-engineer** | E2E pipeline testing | Blender→Unity validation, performance checks, visual quality |

### Routing Examples

Tasks are automatically routed based on labels, keywords, and file paths:

- **"Design a cargo ship asset"** → unity-asset-designer
- **"Write Blender script to generate thruster geometry"** → blender-engineer
- **"Create Unity component for ship flight controls"** → unity-engineer
- **"Validate FBX export has correct scale and LODs"** → gamedev-integration-engineer
- **Files in `projects/unity-space-sim/blender/`** → blender-engineer
- **Files in `projects/unity-space-sim/unity/`** → unity-engineer
- **Issues with `unity-space-sim` label** → Project-specific routing

### Labels

All Unity Space Sim work uses these labels:

| Label | Use When |
|-------|----------|
| `unity-space-sim` | Any Unity Space Sim work |
| `asset-pipeline` | Blender→Unity asset generation workflows |
| `blender` | Blender Python scripting, bpy API |
| `unity-engine` | Unity C# scripts, components, scenes |
| `gamedev` | Game development features (flight controls, camera, gameplay) |
| `unity-meta-phase` | Meta Phase orchestration setup work |
| `unity-phase-1` | Phase 1 foundation work |
| `unity-phase-1.5` | Phase 1.5 MVP work |
| `unity-phase-2` | Phase 2 Blender pipeline work |
| `unity-phase-3` | Phase 3 Unity integration work |
| `unity-phase-4` | Phase 4 CI/CD work |
| `unity-phase-5` | Phase 5 E2E testing work |

## Environment Configuration

Required in `.env`:
- `ARCADE_API_KEY` — Arcade API key for authentication
- `ARCADE_USER_ID` — Agent identity (defaults to "agent@local")

Also configured:
- `GITHUB_REPO`, `GITHUB_TOKEN` — GitHub integration
- `ORCHESTRATOR_AGENT_MODEL`, `GITHUB_AGENT_MODEL`, `CODING_AGENT_MODEL` — Model selection for agent types
  - Use `sonnet` for most agents (orchestrator, github agents)
  - Use `opus` for coding agents and when under-specified
  - **Never use economy mode (`eco` command) unless explicitly requested**
  - Maps to full model IDs in `orchestration/config.py:MODEL_TABLE` (standard) and `ECONOMY_MODEL_TABLE` (economy)
