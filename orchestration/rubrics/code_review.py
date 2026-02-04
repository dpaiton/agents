"""Code review evaluation rubric.

This rubric defines the criteria for evaluating code submissions.
Each criterion is scored on a 0-2 scale and weighted to produce
a maximum total score of 10.
"""

from typing import List

from orchestration.rubrics import EvaluationCriterion


# Correctness: Does the code work as intended?
_CORRECTNESS = EvaluationCriterion(
    name="Correctness",
    description=(
        "The code correctly implements the required functionality. "
        "Logic is sound, edge cases are handled, and the code produces "
        "expected outputs for valid inputs."
    ),
    scale=(0, 2),
    weight=1.0,
)

# Completeness: Does the code fully address the requirements?
_COMPLETENESS = EvaluationCriterion(
    name="Completeness",
    description=(
        "The implementation addresses all stated requirements. "
        "No required features are missing, and the solution is fully "
        "functional without TODO placeholders or incomplete sections."
    ),
    scale=(0, 2),
    weight=1.0,
)

# Code Quality: Is the code well-written and maintainable?
_CODE_QUALITY = EvaluationCriterion(
    name="Code Quality",
    description=(
        "The code follows best practices for readability and maintainability. "
        "Names are descriptive, functions are appropriately sized, "
        "and the code structure is clear and logical."
    ),
    scale=(0, 2),
    weight=1.0,
)

# Security: Is the code free from security vulnerabilities?
_SECURITY = EvaluationCriterion(
    name="Security",
    description=(
        "The code avoids common security vulnerabilities. "
        "Inputs are validated, sensitive data is protected, "
        "and there are no injection risks or unsafe operations."
    ),
    scale=(0, 2),
    weight=1.0,
)

# Test Quality: Are tests comprehensive and well-structured?
_TEST_QUALITY = EvaluationCriterion(
    name="Test Quality",
    description=(
        "Tests are comprehensive, covering happy paths and edge cases. "
        "Test code is readable, tests are independent, and assertions "
        "are meaningful and specific."
    ),
    scale=(0, 2),
    weight=1.0,
)


CODE_REVIEW_RUBRIC: List[EvaluationCriterion] = [
    _CORRECTNESS,
    _COMPLETENESS,
    _CODE_QUALITY,
    _SECURITY,
    _TEST_QUALITY,
]
