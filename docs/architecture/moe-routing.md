# Mixture-of-Experts Routing

This document explains the routing architecture that directs tasks to specialized agents. The system follows a Mixture-of-Experts (MoE) pattern where each agent is an expert in a narrow domain, and a routing layer selects which expert handles each task.

## Why MoE: Specialized Agents Over General Agents

A single general-purpose agent can do many things adequately but few things well. Specialized agents outperform general agents for three reasons:

1. **Focused context windows.** Each agent's system prompt is tuned for one job. The backend engineer's prompt focuses on schemas and data flows. The frontend engineer's prompt focuses on components and user experience. The reviewer's prompt focuses on rubrics and quality criteria. No agent's context is diluted by others' instructions.

2. **Distinct behavioral constraints.** The performance engineer cannot write implementation code (only tests). The architect cannot implement (only design). The infrastructure engineer cannot modify application code (only deployment configs). These constraints are impossible to enforce reliably in a single agent that does everything.

3. **Independent scaling and evaluation.** Each agent can be evaluated, calibrated, and improved independently. If review quality drops, you fix the reviewer prompt — you do not risk degrading backend or frontend code generation in the process.

The tradeoff is routing complexity: you need a mechanism to decide which agent handles which task. This document defines that mechanism.

## Routing Architecture

```
Task arrives (issue comment, PR event, CLI command)
    │
    ▼
┌─────────────────────────┐
│  Deterministic Router    │  ← Pattern match on labels, events, keywords
│  (code, no LLM)         │
└────────┬────────────────┘
         │
         │ match found? ──yes──▶ Route to agent sequence
         │
         no
         │
         ▼
┌─────────────────────────┐
│  LLM Classifier          │  ← Fallback: classify with language model
│  (prompt, confidence)    │
└────────┬────────────────┘
         │
         │ confidence ≥ 80%? ──yes──▶ Route to agent sequence
         │
         no
         │
         ▼
┌─────────────────────────┐
│  Orchestrator             │  ← Ask user for clarification
│  (escalate)              │
└──────────────────────────┘
```

### Layer 1: Deterministic Router (P6: Code Before Prompts)

The first routing layer uses pattern matching — no LLM, no probabilistic behavior, no token cost. This handles the common cases where the task type is obvious from metadata.

**Input signals:**
- GitHub issue labels (`bug`, `feature`, `docs`, `design`, `architecture`, `backend`, `frontend`, `ml`, `infra`, `integration`, `performance`)
- GitHub event type (PR opened, issue commented, review submitted)
- CLI command (`run`, `sync`, `deploy`; prepend `eco` for economy mode, e.g. `eco run`, `eco sync`, `eco deploy`)
- Keyword patterns in the first line of the task description

**Routing rules (evaluated in order):**

| Priority | Signal | Route |
|---|---|---|
| 1 | PR event: review submitted | Judge |
| 2 | PR event: opened or updated | Reviewer |
| 3 | Issue label: `feature` or `enhancement` | Architect > Performance Engineer > Orchestrator |
| 4 | Issue label: `bug` | Performance Engineer > Orchestrator > Reviewer |
| 5 | Issue label: `backend` or `api` or `database` | Performance Engineer > Backend Engineer > Reviewer |
| 6 | Issue label: `frontend` or `ui` or `component` | Performance Engineer > Frontend Engineer > Reviewer |
| 7 | Issue label: `ml` or `model` | ML Engineer > Performance Engineer > Reviewer |
| 8 | Issue label: `infra` or `ci` or `deploy` | Architect > Infrastructure Engineer > Reviewer |
| 9 | Issue label: `integration` or `e2e` | Integration Engineer > Reviewer |
| 10 | Issue label: `performance` or `optimize` | Performance Engineer > Orchestrator |
| 11 | Issue label: `design` or `ux` | Designer |
| 12 | Issue label: `architecture` | Architect |
| 13 | Issue label: `docs` or `documentation` | Architect |
| 14 | CLI: `sync` (or `eco sync`) | Process comments (no agent routing) |

Rules are evaluated top-to-bottom. First match wins. This is deterministic and auditable (P5).

**Note:** The Orchestrator dynamically selects specialized engineers (Backend, Frontend, ML, Infrastructure, Integration) based on context analysis when it appears in a sequence.

### Layer 2: LLM Classifier (Fallback)

When the deterministic router finds no match (no labels, no clear event type, ambiguous input), the LLM classifier analyzes the task description.

**Prompt structure:**

```
Given the following task description, classify it into one of these categories:
- feature: New functionality requiring architecture and design
- bug: Something is broken and needs fixing
- backend: Database, API, data pipeline, or server-side work
- frontend: UI components, user experience, or client-side work
- ml: Machine learning models, experiments, or prompt engineering
- infrastructure: CI/CD, deployment, containers, or monitoring
- integration: End-to-end tests, API compatibility, or cross-component glue
- performance: Performance profiling, optimization, or benchmarking
- design: UI/UX design, wireframes, or user experience specs
- architecture: System design, API specifications, or technology selection
- docs: Documentation only
- unclear: Cannot determine

Task: {task_description}

Respond with: category, confidence (0-100), one-sentence reasoning.
```

**Decision logic:**
- If confidence >= 80%: route using the classified category.
- If confidence < 80%: escalate to orchestrator, which asks the user for clarification.
- The LLM classification is logged with the confidence score for future analysis.

### Layer 3: Escalation

If neither deterministic routing nor LLM classification produces a confident result, the orchestrator asks the user for clarification:

```
I'm not sure how to categorize this task. Could you add one of these labels
to the issue: feature, bug, backend, frontend, ml, infrastructure, integration,
performance, design, architecture, docs?

Alternatively, clarify what outcome you're looking for and I'll route it.
```

This follows P16 (Permission to Fail): the system asks rather than guessing.

## Routing Table with Examples

| Task Description | Deterministic Match | LLM Fallback | Final Route |
|---|---|---|---|
| Issue #42 labeled `bug`: "Login fails with empty password" | `bug` label | Not needed | Performance Engineer > Orchestrator > Reviewer |
| PR #18 opened | PR opened event | Not needed | Reviewer |
| Issue #55 labeled `feature`: "Add CSV export" | `feature` label | Not needed | Architect > Performance Engineer > Orchestrator |
| Issue #60 (no labels): "Clean up the database module" | No match | `backend` (92%) | Performance Engineer > Backend Engineer > Reviewer |
| Issue #61 (no labels): "Improve things" | No match | `unclear` (35%) | Orchestrator asks user to clarify |
| `run "Add input validation"` | No label match | `feature` (88%) | Architect > Performance Engineer > Orchestrator |
| PR review submitted on #18 | Review submitted event | Not needed | Judge |
| Issue #70 labeled `docs`: "Write API reference" | `docs` label | Not needed | Architect |
| Issue #80 labeled `frontend`: "Add dark mode toggle" | `frontend` label | Not needed | Performance Engineer > Frontend Engineer > Reviewer |
| Issue #85 labeled `infra`: "Set up CI/CD pipeline" | `infra` label | Not needed | Architect > Infrastructure Engineer > Reviewer |
| Issue #90 labeled `ml`: "Fine-tune prompt templates" | `ml` label | Not needed | ML Engineer > Performance Engineer > Reviewer |
| `run "Optimize query performance"` | No label match | `performance` (95%) | Performance Engineer > Orchestrator |

## How to Add a New Agent or Route

### Adding a New Agent

1. **Define the role.** Write a one-sentence description of what this agent does that no other agent does. If you cannot write this sentence, the agent may not be needed — its responsibility might belong to an existing agent.

2. **Define constraints.** What must this agent **not** do? Constraints are as important as capabilities. An agent without constraints is a general-purpose agent, which defeats the purpose of MoE.

3. **Add to the agent table** in [agent-roles.md](agent-roles.md):
   - Agent name
   - Role (one sentence)
   - Model (environment variable name)
   - Tools (what it can access)
   - Personality (how it approaches work)
   - Constraints (what it cannot do)

4. **Define communication interfaces.** How does this agent receive input? How does it produce output? All communication should go through GitHub artifacts (issues, PRs, comments) — not direct agent-to-agent calls.

5. **Write calibration examples.** If the agent produces evaluated output, create gold-standard examples for its task type (see [judge-calibration.md](../evaluation/judge-calibration.md)).

### Adding a New Route

1. **Add a deterministic rule first.** Can the new task type be identified by a label, event type, or keyword? If yes, add a pattern match rule to the deterministic router. Assign it a priority relative to existing rules.

2. **Update the LLM classifier.** Add the new category to the classifier prompt's category list with a one-sentence definition.

3. **Define the agent sequence.** Which agents handle this task type, and in what order? Follow the existing patterns:
   - Features: Architect > Performance Engineer > Orchestrator (Orchestrator picks specialist)
   - Bugs: Performance Engineer (writes regression test) > Orchestrator (picks specialist) > Reviewer
   - Backend work: Performance Engineer > Backend Engineer > Reviewer
   - Frontend work: Performance Engineer > Frontend Engineer > Reviewer
   - ML work: ML Engineer > Performance Engineer > Reviewer
   - Infrastructure: Architect (designs) > Infrastructure Engineer (implements) > Reviewer
   - Integration: Integration Engineer > Reviewer
   - Performance: Performance Engineer > Orchestrator
   - Design: Designer (only)
   - Architecture: Architect (only)
   - Documentation: Architect (ensures API docs are complete)

4. **Add routing table examples.** Add at least two examples of the new route to the routing table above — one that matches deterministically and one that requires LLM classification.

5. **Test the route.** Run the new task type through the router and verify it reaches the correct agent sequence. Log the routing decision for audit.

## Monitoring and Iteration

Track these metrics to evaluate routing quality:

| Metric | Target | Action if Below Target |
|---|---|---|
| Deterministic match rate | >70% of tasks | Add more labels/patterns |
| LLM classification accuracy | >90% on labeled holdout | Revise classifier prompt |
| Escalation rate | <10% of tasks | Add patterns for common unclear cases |
| Routing latency (deterministic) | <100ms | Optimize pattern matching |
| Routing latency (LLM fallback) | <2s | Use smaller/faster classifier model |

Review routing logs weekly. When the LLM classifier is frequently classifying a particular pattern, promote it to a deterministic rule. The goal is to maximize the deterministic match rate over time (P6: Code Before Prompts).

## Agent Specialization Summary

The system uses **12 specialized agents** organized in three categories:

**Coordination Agents:**
- **Orchestrator** - Routes tasks to specialists, cannot write code
- **Project Manager** - Manages tasks and runs `eco sync`, cannot write code
- **Reviewer** - Evaluates PRs using rubrics, cannot modify code
- **Judge** - LLM-as-judge evaluation with ensemble methods

**Design & Architecture:**
- **Designer** - UI/UX design, wireframes (cannot write production code)
- **Architect** - System design, API specs (cannot write implementation)

**Engineering Specialists:**
- **Backend Engineer** - Databases, APIs, data pipelines
- **Frontend Engineer** - UI components, responsive design
- **ML Engineer** - Model training, experiment tracking
- **Infrastructure Engineer** - CI/CD, containers, monitoring (cannot modify app code)
- **Integration Engineer** - E2E tests, API compatibility (cannot modify core logic)
- **Performance Engineer** - TDD testing + performance profiling (cannot write implementation)

See [agent-roles.md](agent-roles.md) for detailed constraints, tools, and personalities.

## References

- [Agent Roles](agent-roles.md) — Detailed agent definitions and communication patterns
- [Rubrics](../evaluation/rubrics.md) — Evaluation criteria for reviews
