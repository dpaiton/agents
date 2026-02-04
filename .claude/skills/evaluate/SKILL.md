# Evaluate

## Purpose
Run a full LLM-as-judge evaluation with pairwise debiasing, ensemble voting, and structured scoring against a rubric.

## When to Use
- Evaluating code submissions against a rubric
- Comparing two responses (pairwise evaluation)
- Calibrating judge prompts against gold-standard examples
- Quality assessment before merge decisions

## Inputs
- Response(s) to evaluate
- Rubric (from rubrics/ directory)
- Optional: reference answer (ground truth)
- Optional: second response (for pairwise comparison)

## Steps

### 1. Check for ground truth (P6: simpler approach first)
If a reference answer exists, use direct reference-based evaluation. Skip pairwise comparison — it's unnecessary when ground truth is available.

### 2. Build evaluation prompt
Use the appropriate prompt template:
- `reference_eval_prompt()` for reference-based evaluation
- `pairwise_eval_prompt()` for pairwise comparison
- Append `bias_checklist_prompt()` to all evaluations

### 3. Require reasoning before scores (P3)
The judge MUST write reasoning for each criterion before assigning any numeric score. Scores without reasoning are invalid and must be re-requested.

### 4. Validate scores (P5: deterministic validation)
- Scores must be integers within the rubric scale
- No partial scores (3.5 is not valid)
- Scores outside the defined range are rejected

### 5. Pairwise debiasing (if comparing two responses)
Run the comparison twice:
1. Original order: Response A, Response B
2. Swapped order: Response B, Response A

If the winner changes after swapping, flag as **unstable** (position bias detected). Unstable results are scored as ties or escalated for human review (P16).

### 6. Ensemble voting
Run evaluation N times (default 3) with the same prompt. Aggregate by majority vote:
- If all judges agree: high confidence
- If 2/3 agree: moderate confidence
- If all disagree: low confidence, flag for review

### 7. Safety check
Scan judge output for safety concerns. If detected, set `safety_flag=True` regardless of score. Safety-flagged evaluations require human review.

### 8. Compile report
Produce an `EvaluationReport` with:
- Per-criterion scores and reasoning
- Total score
- Confidence level
- Bias checklist (completed)
- Safety flag

## Outputs
- `EvaluationReport` with scores, reasoning, confidence, bias checklist, safety flag
- For pairwise: winner (A, B, or tie), stability flag

## References
- [rubrics/general-rubric.md](rubrics/general-rubric.md)
- [rubrics/bias-awareness.md](rubrics/bias-awareness.md)

## Principles
- **P4 Scaffolding > Model** — The value is in the structure (validation, debiasing, aggregation), not the model.
- **P5 Deterministic Infrastructure** — Score validation, swap logic, and ensemble aggregation are pure code.
- **P15 Science as Meta-Loop** — Each calibration round is: hypothesis → score → compare to gold → adjust → repeat.
- **P16 Permission to Fail** — Unstable results are flagged, not hidden. Low confidence is reported honestly.
