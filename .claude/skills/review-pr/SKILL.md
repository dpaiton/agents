# Review PR

## Purpose
Review a pull request using a structured rubric with 5 criteria, producing evidence-based scores and actionable feedback.

## When to Use
- A PR is opened or updated
- A reviewer agent is invoked for code quality assessment
- A human requests a structured review

## Inputs
- PR diff (git diff content)
- Issue specification (what the PR is supposed to achieve)
- Rubric (defaults to code-review-rubric.md)

## Steps

### 1. Read the spec first
Before looking at code, read the issue or spec. Understand what "done" means.

### 2. Read the full diff
Read every changed file. Do not skim.

### 3. Reason before scoring (P3: Clear Thinking First)
For each of the 5 criteria, write 1-3 sentences of evidence BEFORE assigning a number:

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Correctness | Logical errors, broken | Mostly correct, edge cases missed | Correct, handles edge cases |
| Completeness | Missing required functionality | Core present, gaps | Full functionality |
| Code Quality | Poor naming, duplication | Acceptable, minor issues | Clean, follows conventions |
| Security | Known vulnerabilities | No obvious vulns, not hardened | Input validated, errors handled |
| Test Quality | No/meaningless tests | Happy-path only | Edge + error + integration |

### 4. Apply bias checklist
Before finalizing, check for biases (see rubrics/bias-awareness.md):
- [ ] Am I favoring this code because it's well-formatted? (format bias)
- [ ] Am I being lenient because the code is long/detailed? (verbosity bias)
- [ ] Am I influenced by confident comments in the code? (authority bias)

### 5. Score
Assign discrete integers only (0, 1, or 2). No half-points. Sum for total out of 10.

### 6. Provide actionable feedback
Every score must cite specific code. Include concrete suggestions for improvement.

## Outputs
- Per-criterion scores with evidence
- Total score (out of 10)
- Actionable feedback with line references
- Recommendation: Approve (9-10), Request Changes (< 7), or Comment (7-8)

## References
- [rubrics/code-review-rubric.md](rubrics/code-review-rubric.md)
- [rubrics/bias-awareness.md](rubrics/bias-awareness.md)

## Principles
- **P3 Clear Thinking First** — Reasoning before scores, always.
- **P5 Deterministic Infrastructure** — The rubric is fixed. Only the judgment varies.
- **P7 Spec / Test / Evals First** — Read the spec before the code.
