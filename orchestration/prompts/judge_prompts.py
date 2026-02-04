"""Prompt templates for the judge agent.

These prompts support evaluation tasks including reference-based scoring,
pairwise comparison, and bias detection. All evaluation prompts require
reasoning before scores (P3) and allow uncertainty expression (P16).
"""


def reference_eval_prompt(response: str, reference: str, rubric: str) -> str:
    """Generate a prompt for evaluating a response against a reference.

    Args:
        response: The response to evaluate.
        reference: The reference answer to compare against.
        rubric: The evaluation criteria and scoring guidelines.

    Returns:
        A formatted prompt string for reference-based evaluation.
    """
    return f"""You are an expert evaluator. Your task is to assess a response against a reference answer using the provided rubric.

## Reference Answer
{reference}

## Response to Evaluate
{response}

## Evaluation Rubric
{rubric}

## Instructions

1. **Analyze the response**: Carefully read and understand the response in relation to the reference.
2. **Apply the rubric**: Consider each criterion in the rubric systematically.
3. **Reason before scoring**: Explain your reasoning for each aspect of the evaluation BEFORE providing any scores. Think through:
   - What the response does well
   - Where the response falls short compared to the reference
   - Specific examples supporting your assessment
4. **Score**: Only after completing your reasoning, provide your final score(s) according to the rubric.

## Uncertainty Guidance

If you are uncertain about any aspect of your evaluation, state your uncertainty explicitly. It is better to acknowledge ambiguity than to provide false confidence. For example:
- "I am uncertain whether X meets criterion Y because..."
- "The rubric is ambiguous regarding Z, so I am interpreting it as..."

## Output Format

### Reasoning
[Your detailed reasoning here, addressing each rubric criterion]

### Uncertainty (if any)
[State any uncertainties or ambiguities]

### Final Evaluation
[Your scores and final judgment according to the rubric format]
"""


def pairwise_eval_prompt(response_a: str, response_b: str, rubric: str) -> str:
    """Generate a prompt for pairwise comparison of two responses.

    This prompt includes debiasing instructions to mitigate position bias
    and other common comparison pitfalls.

    Args:
        response_a: The first response to compare.
        response_b: The second response to compare.
        rubric: The evaluation criteria for comparison.

    Returns:
        A formatted prompt string for pairwise evaluation.
    """
    return f"""You are an expert evaluator. Your task is to compare two responses and determine which better satisfies the evaluation criteria.

## Response A
{response_a}

## Response B
{response_b}

## Evaluation Rubric
{rubric}

## Debiasing Instructions

Be aware of and actively counteract these common biases:
- **Position bias**: Do not favor a response simply because it appears first or second.
- **Length bias**: Longer responses are not automatically better. Evaluate substance over volume.
- **Verbosity bias**: Concise, accurate responses may be superior to verbose ones.
- **Style bias**: Focus on correctness and completeness, not superficial style preferences.

To counteract position bias specifically:
1. Evaluate each response independently against the rubric first.
2. Only then compare them directly.
3. Ask yourself: "Would my judgment change if the responses were presented in reverse order?"

## Instructions

1. **Evaluate Response A**: Apply the rubric to Response A, noting strengths and weaknesses.
2. **Evaluate Response B**: Apply the rubric to Response B, noting strengths and weaknesses.
3. **Reason before deciding**: Compare your evaluations and explain your reasoning for which response is superior. Think through:
   - How each response addresses the rubric criteria
   - Direct comparisons on specific points
   - Trade-offs between the responses
4. **Make your decision**: Only after completing your reasoning, declare which response is better (or if they are equivalent).

## Uncertainty Guidance

If you are uncertain about which response is better, state this explicitly. It is acceptable to conclude:
- "Both responses are roughly equivalent because..."
- "I cannot confidently distinguish between them due to..."
- "Response X is marginally better, but I have low confidence because..."

## Output Format

### Response A Analysis
[Your evaluation of Response A against the rubric]

### Response B Analysis
[Your evaluation of Response B against the rubric]

### Comparative Reasoning
[Your comparison and reasoning]

### Uncertainty (if any)
[State any uncertainties]

### Final Decision
[A, B, or Equivalent, with brief justification]
"""


def bias_checklist_prompt() -> str:
    """Generate a standalone bias checklist to append to any evaluation.

    This checklist can be appended to other prompts to reinforce
    bias awareness and mitigation.

    Returns:
        A formatted bias checklist string.
    """
    return """## Bias Checklist

Before finalizing your evaluation, review this checklist:

- [ ] **Position bias**: Have I favored content based on where it appeared rather than its merit?
- [ ] **Length bias**: Have I equated length with quality?
- [ ] **Familiarity bias**: Have I favored responses that match my training data more closely?
- [ ] **Authority bias**: Have I been swayed by confident tone over actual correctness?
- [ ] **Confirmation bias**: Have I sought evidence supporting my initial impression?
- [ ] **Anchoring bias**: Have I let my first observation disproportionately influence my judgment?
- [ ] **Halo effect**: Have I let one strong aspect of a response color my view of other aspects?

If you answered yes to any of these, revisit your evaluation and adjust accordingly.

Remember: If uncertain, state your uncertainty explicitly rather than defaulting to false confidence.
"""
