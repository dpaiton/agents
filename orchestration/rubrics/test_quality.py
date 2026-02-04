"""Test quality evaluation rubric.

This rubric defines criteria for evaluating test suites.
Each criterion is scored on a 0-2 scale.
"""

from typing import List

from orchestration.rubrics import EvaluationCriterion


# Coverage: How much of the code is exercised by tests?
_COVERAGE = EvaluationCriterion(
    name="Coverage",
    description=(
        "Tests exercise a comprehensive portion of the codebase. "
        "Critical paths, branches, and functions are covered. "
        "Coverage gaps in important areas are minimized."
    ),
    scale=(0, 2),
    weight=1.0,
)

# Edge Cases: Are boundary conditions and unusual inputs tested?
_EDGE_CASES = EvaluationCriterion(
    name="Edge Cases",
    description=(
        "Tests include boundary conditions, empty inputs, null values, "
        "and other edge cases. Unusual but valid inputs are tested "
        "alongside typical use cases."
    ),
    scale=(0, 2),
    weight=1.0,
)

# Error Handling: Are error conditions and exceptions tested?
_ERROR_HANDLING = EvaluationCriterion(
    name="Error Handling",
    description=(
        "Tests verify that errors are handled gracefully. "
        "Expected exceptions are raised for invalid inputs, "
        "and error messages are meaningful and accurate."
    ),
    scale=(0, 2),
    weight=1.0,
)

# Naming: Are test names clear and descriptive?
_NAMING = EvaluationCriterion(
    name="Naming",
    description=(
        "Test names clearly describe what is being tested and expected outcomes. "
        "Names follow consistent conventions and make test failures "
        "immediately understandable without reading the test body."
    ),
    scale=(0, 2),
    weight=1.0,
)

# Isolation: Are tests independent and free from side effects?
_ISOLATION = EvaluationCriterion(
    name="Isolation",
    description=(
        "Tests are independent and can run in any order. "
        "Each test sets up its own state and cleans up after itself. "
        "Tests do not share mutable state or depend on external resources."
    ),
    scale=(0, 2),
    weight=1.0,
)


TEST_QUALITY_RUBRIC: List[EvaluationCriterion] = [
    _COVERAGE,
    _EDGE_CASES,
    _ERROR_HANDLING,
    _NAMING,
    _ISOLATION,
]
