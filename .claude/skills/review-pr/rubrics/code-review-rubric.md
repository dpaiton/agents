# Code Review Rubric

Each submission is scored on 5 criteria. Each criterion receives 0, 1, or 2. Maximum total: **10**.

## Criteria

### Correctness (0-2)
Does the code produce the right output for all inputs?

- **0** — Logical errors, broken functionality. Core logic is flawed.
- **1** — Mostly correct, edge cases missed. Works on common path but fails on boundaries.
- **2** — Correct, handles edge cases. Produces correct output for all tested inputs including boundaries and malformed input.

### Completeness (0-2)
Does the code implement everything the spec requires?

- **0** — Missing required functionality. Major requirements absent.
- **1** — Core present, gaps in coverage. Main feature works but secondary requirements missing.
- **2** — Full functionality as specified. All documented behaviors implemented.

### Code Quality (0-2)
Is the code readable, maintainable, and well-structured?

- **0** — Poor naming, duplication, no patterns. Hard to understand intent.
- **1** — Acceptable, minor issues. Understandable with effort.
- **2** — Clean, follows conventions, DRY. A new developer can understand without explanation.

### Security (0-2)
Is the code safe from common vulnerabilities?

- **0** — Known vulnerabilities present. Injection flaws, unvalidated inputs, secrets in source.
- **1** — No obvious vulnerabilities, not hardened. Inputs not validated, errors may leak details.
- **2** — Input validated, errors handled securely. Follows principle of least privilege.

### Test Quality (0-2)
Do the tests prove the code works and catch regressions?

- **0** — No tests or meaningless tests. Tests absent or test nothing meaningful.
- **1** — Happy-path only. Common case covered but no edge/error cases.
- **2** — Edge cases + error cases + integration. Comprehensive coverage.

## Scoring Instructions

1. Read the spec before the code
2. Write reasoning before each score
3. Assign discrete integers only (0, 1, or 2)
4. Cite specific code for every score
5. Sum for total out of 10

## Score Interpretation

| Total | Meaning |
|---|---|
| 9-10 | Ready to merge |
| 7-8 | Good work, address feedback |
| 5-6 | Needs revision |
| 3-4 | Significant rework |
| 0-2 | Does not meet requirements |
