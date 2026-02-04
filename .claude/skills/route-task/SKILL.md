# Route Task

## Purpose
Classify an incoming task and determine the agent execution sequence using deterministic pattern matching, with LLM fallback only for ambiguous input.

## When to Use
- A new issue is created or commented on
- A CLI command (`eco run`, `eco route`) is invoked with a task description
- The orchestrator needs to decide which agents handle a task

## Inputs
- Task description (issue body, comment text, or CLI argument)
- Optional: issue labels, event type (PR opened, review submitted, etc.)

## Steps

### 1. Check deterministic signals (P6: Code Before Prompts)

Check labels and event types first — no LLM needed for obvious cases.

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

Rules are evaluated top-to-bottom. First match wins.

### 2. Keyword pattern matching

If no label/event match, check the task description for keywords:
- `fix`, `bug`, `broken`, `error` → bug fix route
- `add`, `create`, `implement`, `feature` → feature route
- `review`, `PR`, `pull request` → reviewer
- `docs`, `readme`, `documentation` → docs route
- `refactor`, `clean`, `restructure` → refactor route
- `deploy`, `CI`, `infra`, `pipeline` → infrastructure route

### 3. LLM classification fallback

If pattern matching returns `unknown`, invoke the classify_task_prompt:
- If confidence >= 80%: route using the classified category
- If confidence < 80%: escalate to orchestrator for clarification (P16)

### 4. Log the decision

Record: task description, matched signal, classified type, confidence, and routed sequence.

## Outputs
- `task_type`: classified category (feature, bug, docs, refactor, review, infra, unknown)
- `agent_sequence`: ordered list of agents to execute
- `priority`: high, medium, or low
- `confidence`: how certain the classification is

## Principles
- **P6 Code Before Prompts** — Pattern matching handles the majority of cases. LLM is the fallback.
- **P5 Deterministic Infrastructure** — The routing table is static. Same input, same output.
- **P8 UNIX Philosophy** — This skill does one thing: route. It does not execute.
- **P16 Permission to Fail** — `unknown` is a valid classification. Escalate rather than guess.
