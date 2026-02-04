"""Prompt templates for the reviewer agent.

These prompts support code review tasks including PR diff review and
test quality assessment. All prompts require reasoning before scores (P3)
and allow uncertainty expression (P16).
"""


def review_pr_prompt(diff: str, rubric: str) -> str:
    """Generate a prompt for reviewing a PR diff against a rubric.

    Args:
        diff: The git diff content to review.
        rubric: The review criteria and guidelines.

    Returns:
        A formatted prompt string for PR review.
    """
    return f"""You are an expert code reviewer. Your task is to review a pull request diff against the provided rubric.

## Pull Request Diff
```diff
{diff}
```

## Review Rubric
{rubric}

## Instructions

1. **Understand the changes**: Read through the diff to understand what is being modified and why.
2. **Apply the rubric**: Systematically evaluate each criterion in the rubric.
3. **Reason before judging**: For each aspect of the review, explain your reasoning:
   - What does the code do well?
   - What concerns or issues do you see?
   - Are there potential bugs, security issues, or maintainability problems?
   - Does the code follow best practices and conventions?
4. **Provide actionable feedback**: Only after reasoning, summarize your findings with specific, actionable suggestions.

## Review Categories

Consider these aspects during your review:
- **Correctness**: Does the code do what it's supposed to do?
- **Security**: Are there any security vulnerabilities?
- **Performance**: Are there obvious performance issues?
- **Maintainability**: Is the code readable and maintainable?
- **Testing**: Are changes appropriately tested?
- **Documentation**: Are changes appropriately documented?

## Uncertainty Guidance

If you are uncertain about any aspect of the code:
- State what you are uncertain about
- Explain why (missing context, unfamiliar pattern, etc.)
- Suggest what information would help clarify

For example:
- "I am uncertain whether this change handles edge case X because..."
- "Without seeing the full context of Y, I cannot determine if Z is correct..."

It is better to flag uncertainty than to approve problematic code or block good code.

## Output Format

### Summary
[Brief summary of what this PR does]

### Detailed Review

#### [Category/File/Section]
- **Observation**: [What you noticed]
- **Reasoning**: [Why this matters]
- **Suggestion**: [Specific actionable feedback, if any]

[Repeat for each significant finding...]

### Uncertainty (if any)
[Areas where you lack confidence or need more context]

### Overall Assessment
- **Approve / Request Changes / Comment**: [Your recommendation]
- **Key Issues**: [List critical issues that must be addressed]
- **Suggestions**: [List non-blocking improvements]
"""


def scrutinize_test_changes_prompt(test_diff: str) -> str:
    """Generate a prompt to evaluate test quality and TDD compliance.

    Args:
        test_diff: The git diff of test file changes.

    Returns:
        A formatted prompt string for test review.
    """
    return f"""You are an expert test reviewer. Your task is to evaluate test changes for quality and TDD (Test-Driven Development) compliance.

## Test Diff
```diff
{test_diff}
```

## Instructions

1. **Understand the test changes**: Identify what tests are being added, modified, or removed.
2. **Evaluate test quality**: Apply the quality criteria below systematically.
3. **Reason before judging**: For each criterion, explain your reasoning:
   - What makes these tests effective or ineffective?
   - Are there gaps in coverage?
   - Do the tests follow best practices?
4. **Assess TDD compliance**: Consider whether tests drive the implementation or merely validate it after the fact.
5. **Provide feedback**: Only after reasoning, summarize with actionable suggestions.

## Test Quality Criteria

- **Coverage**: Do tests cover the intended functionality, including edge cases?
- **Isolation**: Are tests independent and not reliant on external state?
- **Clarity**: Are test names and assertions clear about what they verify?
- **Maintainability**: Will these tests be easy to maintain as code evolves?
- **Speed**: Are tests appropriately fast (unit tests fast, integration tests acceptable)?
- **Determinism**: Are tests deterministic (no flaky tests)?

## TDD Compliance Indicators

Signs of good TDD practice:
- Tests clearly specify expected behavior
- Tests are written at the right abstraction level
- Tests fail for the right reasons
- Tests serve as documentation

Warning signs:
- Tests that merely mirror implementation details
- Tests added as an afterthought (testing what exists, not what should exist)
- Tests that are too tightly coupled to implementation
- Missing tests for error cases or edge cases

## Uncertainty Guidance

If you are uncertain about test quality:
- State what you cannot determine from the diff alone
- Explain what additional context would help
- Provide your best assessment while noting limitations

For example:
- "Without seeing the implementation, I cannot confirm if edge case X is adequately covered..."
- "I am uncertain whether this test is flaky because..."

## Output Format

### Summary
[Brief description of test changes]

### Test Quality Analysis

#### Coverage
- **Assessment**: [Your evaluation]
- **Reasoning**: [Why you reached this conclusion]
- **Gaps identified**: [Any missing coverage]

#### Isolation
- **Assessment**: [Your evaluation]
- **Reasoning**: [Evidence from the diff]

#### Clarity
- **Assessment**: [Your evaluation]
- **Specific examples**: [Good or problematic test names/assertions]

#### Maintainability
- **Assessment**: [Your evaluation]
- **Concerns**: [Any maintenance issues foreseen]

### TDD Compliance

- **Assessment**: [Compliant / Partially Compliant / Non-Compliant / Cannot Determine]
- **Reasoning**: [Evidence for your assessment]
- **Indicators observed**: [What suggests this assessment]

### Uncertainty (if any)
[What you cannot determine and what would help]

### Recommendations

#### Required Changes
[Issues that must be addressed]

#### Suggested Improvements
[Non-blocking suggestions to improve test quality]
"""
