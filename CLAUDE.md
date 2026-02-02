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

## Project Overview

Multi-agent orchestration meta-repository. Coordinates AI agents (orchestrator, engineer, test-writer, reviewer, judge) to develop software with built-in evaluation. GitHub issues are the primary coordination mechanism.

Arcade/MCP authorization handles OAuth-based write permissions for GitHub tools via the Arcade API.

## Commands

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run linter
uv run ruff check .

# Run authorization for all configured services
python authorize_arcade.py

# Authorize a specific service only
python authorize_arcade.py github

# Set up GitHub branch protection rules
./.github/scripts/setup-branch-protection.sh
```

## Architecture

Deterministic scaffolding around probabilistic models:

```
User goal
    → Orchestrator (deterministic routing: pattern match first, LLM fallback)
        → Test-Writer (specs/tests before code)
        → Engineer (code before prompts)
        → Reviewer (deterministic rubrics)
        → Judge (structured evaluation, ensemble aggregation)
    → Memory (captured in issues/docs)
```

**authorize_arcade.py** handles service auth:
1. Loads config from `.env` via `python-dotenv`
2. Iterates `SERVICES` dict (each has `verify_tool`, `extract_name`, `auth_tools`)
3. Authorizes tools via `Arcade.tools.authorize()` (triggers OAuth)
4. Verifies connection via each service's verify tool

## Environment Configuration

Required in `.env`:
- `ARCADE_API_KEY` — Arcade API key for authentication
- `ARCADE_USER_ID` — Agent identity (defaults to "agent@local")

Also configured:
- `GITHUB_REPO`, `GITHUB_TOKEN` — GitHub integration
- `ORCHESTRATOR_AGENT_MODEL`, `GITHUB_AGENT_MODEL`, `CODING_AGENT_MODEL` — Model selection
