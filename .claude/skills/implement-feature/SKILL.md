# Implement Feature

## Purpose
Write the minimal production code that makes existing failing tests pass (TDD green phase).

## When to Use
- After the performance-engineer has created failing tests
- When a specialized engineer (backend, frontend, ML, infrastructure, integration) is assigned to implement a feature or fix a bug
- During the green phase of TDD (red → **green** → refactor)

## Inputs
- Failing test files (the spec)
- Issue description with acceptance criteria
- Existing codebase patterns and conventions

## Steps

### 1. Read failing tests first
The tests ARE the spec. Read every test to understand what the code must do. Do not read the issue description as a substitute for reading the tests.

### 2. Apply the decision hierarchy (P11)
Before writing code, ask:
1. **Can this be solved with existing code?** Check if a function or pattern already exists.
2. **Can this be solved with a CLI tool?** Use `gh`, `git`, `pytest`, `ruff` if applicable.
3. **Is code the right solution?** Only then write new code.

### 3. Write minimal code
Write the simplest code that makes all tests pass. Do not:
- Add features not required by tests
- Add error handling not tested
- Refactor unrelated code
- Add documentation beyond what's needed for clarity

### 4. Run tests
Run the test suite. All previously failing tests must now pass. No existing tests should break.

### 5. Minimal test changes only
If a test has a minor issue (e.g., wrong import path due to module structure), fix it. Do NOT rewrite tests or add new tests — that is the performance-engineer's job.

### 6. Commit and create PR
Follow git guidelines: small commits, descriptive messages, branch naming convention.

## Outputs
- Production code that makes all failing tests pass
- No regressions (all existing tests still pass)
- PR ready for review

## Principles
- **P6 Code Before Prompts** — Write code. Do not craft elaborate prompts.
- **P8 UNIX Philosophy** — This skill only implements. It does not write tests or review.
- **P11 Decision Hierarchy** — Prefer simpler solutions. Code > CLI > Prompts > Agents.
- **P9 ENG/SRE Principles** — Follow git best practices: rebase, small commits, minimal PRs.
