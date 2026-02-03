# Code Review Rubric

This rubric defines what "correct" code looks like. It is a **specification** — it exists before the code that implements automated evaluation (P7: Spec / Test / Evals First). Given the same work product, two reviewers applying this rubric independently should converge on the same score (P5: Deterministic Infrastructure).

## Scoring Summary

Each submission is scored on 5 criteria. Each criterion receives a discrete integer score of 0, 1, or 2. The maximum total score is **10**.

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Correctness | Logical errors, broken functionality | Mostly correct, edge cases missed | Correct, handles edge cases |
| Completeness | Missing required functionality | Core present, gaps in coverage | Full functionality as specified |
| Code Quality | Poor naming, duplication, no patterns | Acceptable, minor issues | Clean, follows conventions, DRY |
| Security | Known vulnerabilities present | No obvious vulns, not hardened | Input validated, errors handled securely |
| Test Quality | No tests or meaningless tests | Happy-path only | Edge cases + error cases + integration |

## Criterion Definitions

### 1. Correctness (0-2)

Does the code produce the right output for all inputs?

- **0 — Logical errors, broken functionality.** The code fails on standard inputs, produces wrong results, or crashes during normal use. Core logic is flawed.
- **1 — Mostly correct, edge cases missed.** The code handles the common path correctly but fails on boundary conditions, empty inputs, large inputs, or concurrent access.
- **2 — Correct, handles edge cases.** The code produces correct output for all tested inputs including boundary conditions, malformed inputs, and edge cases documented in the spec.

### 2. Completeness (0-2)

Does the code implement everything the spec requires?

- **0 — Missing required functionality.** Major features or requirements from the spec are absent. The submission is partial or skeletal.
- **1 — Core present, gaps in coverage.** The main feature works but secondary requirements, error handling paths, or documented behaviors are missing.
- **2 — Full functionality as specified.** All requirements from the spec are implemented. No documented behavior is missing.

### 3. Code Quality (0-2)

Is the code readable, maintainable, and well-structured?

- **0 — Poor naming, duplication, no patterns.** Variable names are meaningless, logic is duplicated across locations, no consistent patterns or structure. A new developer would struggle to understand intent.
- **1 — Acceptable, minor issues.** Names are mostly descriptive, some minor duplication exists, structure is present but imperfect. Code is understandable with effort.
- **2 — Clean, follows conventions, DRY.** Names clearly communicate intent. No unnecessary duplication. Follows the project's established patterns and conventions. A new developer can understand intent without explanation.

### 4. Security (0-2)

Is the code safe from common vulnerabilities?

- **0 — Known vulnerabilities present.** Code has injection flaws, unvalidated inputs passed to sensitive operations, secrets in source, or other OWASP Top 10 issues.
- **1 — No obvious vulnerabilities, not hardened.** No glaring security issues but inputs are not validated, errors may leak implementation details, or security best practices are not followed.
- **2 — Input validated, errors handled securely.** All external inputs are validated and sanitized. Errors are caught and handled without leaking internals. Secrets are managed via environment variables, not code. Follows principle of least privilege.

### 5. Test Quality (0-2)

Do the tests prove the code works and catch regressions?

- **0 — No tests or meaningless tests.** Tests are absent, or they exist but test nothing meaningful (e.g., `assert True`, testing only that a function exists).
- **1 — Happy-path only.** Tests verify the common case but do not cover edge cases, error conditions, or integration with other components.
- **2 — Edge cases + error cases + integration.** Tests cover the happy path, edge cases (boundary values, empty inputs), error cases (invalid inputs, failures), and integration scenarios (components working together).

## Scoring Instructions

Follow this procedure for every evaluation. These steps enforce deliberate reasoning before scoring (P3: Clear Thinking First).

### Step 1: Read the Spec

Before looking at any code, read the specification or issue description. Understand what "done" means.

### Step 2: Read the Submission

Read the code and tests in full. Do not skim.

### Step 3: Reason Before Scoring

For each criterion, write 1-3 sentences of evidence **before** assigning a number. The reasoning is the primary output; the number is a summary of the reasoning.

Example format:

```
Correctness: The function correctly parses all documented input formats.
However, it does not handle the case where the input file is empty,
which is specified in requirement #3. Score: 1
```

### Step 4: Assign Discrete Integers Only

Each score must be exactly 0, 1, or 2. No half-points. No ranges. No "1-2". If you are uncertain between two scores, re-read the criterion definitions and pick the one whose description best matches the evidence.

### Step 5: Provide Evidence for Every Score

Every score must cite specific code, specific tests, or specific spec requirements. Scores without evidence are invalid.

Bad: `Code Quality: 2`
Good: `Code Quality: Functions are clearly named (parse_config, validate_input). No duplication — shared logic is extracted into helpers. Follows the project's existing pattern of dataclass-based configuration. Score: 2`

### Step 6: Compute Total

Sum the five scores. The total is out of 10.

## Score Interpretation

| Total | Interpretation |
|---|---|
| 9-10 | Ready to merge. Minor nits at most. |
| 7-8 | Good work. Address specific feedback before merging. |
| 5-6 | Needs revision. Core issues to fix. |
| 3-4 | Significant rework required. |
| 0-2 | Does not meet requirements. Start over or re-scope. |

## Applying This Rubric

This rubric is used by the **judge agent** in the evaluation pipeline. It is also used by human reviewers for calibration (see [judge-calibration.md](judge-calibration.md)).

When used in automated evaluation:
- The rubric text is included in the judge prompt as a fixed template (P5: Deterministic Infrastructure).
- The judge must output reasoning before each score.
- The judge must output discrete integers only.
- The judge's output is parsed programmatically — scores that do not conform to the schema are rejected and re-requested.
