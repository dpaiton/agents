# Mixture-of-Experts Routing

This document explains the routing architecture that directs tasks to specialized agents. The system follows a Mixture-of-Experts (MoE) pattern where each agent is an expert in a narrow domain, and a routing layer selects which expert handles each task.

## Why MoE: Specialized Agents Over General Agents

A single general-purpose agent can do many things adequately but few things well. Specialized agents outperform general agents for three reasons:

1. **Focused context windows.** Each agent's system prompt is tuned for one job. The engineer's prompt focuses on code patterns and test satisfaction. The reviewer's prompt focuses on the rubric and security. Neither is diluted by the other's instructions.

2. **Distinct behavioral constraints.** The test writer cannot write implementation code. The engineer cannot self-review. These constraints are impossible to enforce reliably in a single agent that does everything.

3. **Independent scaling and evaluation.** Each agent can be evaluated, calibrated, and improved independently. If review quality drops, you fix the reviewer prompt — you do not risk degrading code generation in the process.

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
- GitHub issue labels (`bug`, `feature`, `docs`, `refactor`, `security`, `infra`)
- GitHub event type (PR opened, issue commented, review submitted)
- CLI command (`eco run`, `eco sync`, `eco deploy`)
- Keyword patterns in the first line of the task description

**Routing rules (evaluated in order):**

| Priority | Signal | Route |
|---|---|---|
| 1 | PR event: review submitted | Judge |
| 2 | PR event: opened or updated | Reviewer |
| 3 | Issue label: `security` | Orchestrator > Test Writer > Engineer > Reviewer > Judge |
| 4 | Issue label: `bug` | Orchestrator > Test Writer > Engineer > Reviewer |
| 5 | Issue label: `feature` or `enhancement` | Orchestrator > Test Writer > Engineer > Reviewer |
| 6 | Issue label: `refactor` | Orchestrator > Test Writer > Engineer > Reviewer |
| 7 | Issue label: `docs` or `documentation` | Orchestrator > Engineer > Reviewer |
| 8 | Issue label: `infra` or `ci` | Orchestrator > Engineer > Reviewer |
| 9 | CLI: `eco sync` | Process comments (no agent routing) |

Rules are evaluated top-to-bottom. First match wins. This is deterministic and auditable (P5).

### Layer 2: LLM Classifier (Fallback)

When the deterministic router finds no match (no labels, no clear event type, ambiguous input), the LLM classifier analyzes the task description.

**Prompt structure:**

```
Given the following task description, classify it into one of these categories:
- feature: New functionality
- bug: Something is broken
- docs: Documentation only
- refactor: Restructure without behavior change
- security: Security vulnerability or hardening
- infra: CI/CD, tooling, infrastructure
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
to the issue: feature, bug, docs, refactor, security, infra?

Alternatively, clarify what outcome you're looking for and I'll route it.
```

This follows P16 (Permission to Fail): the system asks rather than guessing.

## Routing Table with Examples

| Task Description | Deterministic Match | LLM Fallback | Final Route |
|---|---|---|---|
| Issue #42 labeled `bug`: "Login fails with empty password" | `bug` label | Not needed | Orchestrator > Test Writer > Engineer > Reviewer |
| PR #18 opened | PR opened event | Not needed | Reviewer |
| Issue #55 labeled `feature`: "Add CSV export" | `feature` label | Not needed | Orchestrator > Test Writer > Engineer > Reviewer |
| Issue #60 (no labels): "Clean up the database module" | No match | `refactor` (92%) | Orchestrator > Test Writer > Engineer > Reviewer |
| Issue #61 (no labels): "Improve things" | No match | `unclear` (35%) | Orchestrator asks user to clarify |
| `eco run "Add input validation"` | No label match | `feature` (88%) | Orchestrator > Test Writer > Engineer > Reviewer |
| PR review submitted on #18 | Review submitted event | Not needed | Judge |
| Issue #70 labeled `docs`: "Write API reference" | `docs` label | Not needed | Orchestrator > Engineer > Reviewer |

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
   - Tasks that produce code: include Test Writer before Engineer (TDD).
   - Tasks that need quality verification: end with Reviewer.
   - Tasks that need scoring: end with Judge.

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

## References

- [Agent Roles](agent-roles.md) — Detailed agent definitions and communication patterns
- [TDD Workflow](tdd-workflow.md) — The test-first pipeline that most routes follow
