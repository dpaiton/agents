"""Evaluation rubrics for code review and quality assessment.

This module provides the EvaluationCriterion dataclass and exports
rubric definitions for different evaluation contexts.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class EvaluationCriterion:
    """A single evaluation criterion within a rubric.

    Attributes:
        name: Short identifier for the criterion (e.g., "Correctness")
        description: Detailed explanation of what this criterion measures
        scale: Tuple of (min_score, max_score) for this criterion
        weight: Multiplier applied to raw score (default 1.0)
    """

    name: str
    description: str
    scale: Tuple[int, int]
    weight: float = 1.0

    @property
    def max_score(self) -> float:
        """Maximum possible score for this criterion (scale max * weight)."""
        return self.scale[1] * self.weight

    @property
    def min_score(self) -> float:
        """Minimum possible score for this criterion (scale min * weight)."""
        return self.scale[0] * self.weight


from orchestration.rubrics.code_review import CODE_REVIEW_RUBRIC
from orchestration.rubrics.test_quality import TEST_QUALITY_RUBRIC

__all__ = [
    "EvaluationCriterion",
    "CODE_REVIEW_RUBRIC",
    "TEST_QUALITY_RUBRIC",
]
