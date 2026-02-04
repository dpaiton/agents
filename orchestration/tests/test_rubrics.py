"""Tests for rubric structure validation.

These tests validate structural invariants of the rubrics:
- Correct number of criteria
- Expected maximum scores
- Valid scale ranges
- Required fields are populated
"""

import pytest

from orchestration.rubrics import (
    CODE_REVIEW_RUBRIC,
    TEST_QUALITY_RUBRIC,
    EvaluationCriterion,
)


class TestCodeReviewRubric:
    """Tests for the code review rubric structure."""

    def test_code_review_rubric_has_five_criteria(self) -> None:
        """CODE_REVIEW_RUBRIC must contain exactly 5 criteria."""
        assert len(CODE_REVIEW_RUBRIC) == 5

    def test_code_review_rubric_max_score_is_ten(self) -> None:
        """Total maximum score across all criteria must equal 10."""
        total_max = sum(criterion.max_score for criterion in CODE_REVIEW_RUBRIC)
        assert total_max == 10.0

    def test_code_review_rubric_criteria_names(self) -> None:
        """Verify all expected criteria are present."""
        names = {criterion.name for criterion in CODE_REVIEW_RUBRIC}
        expected = {"Correctness", "Completeness", "Code Quality", "Security", "Test Quality"}
        assert names == expected


class TestTestQualityRubric:
    """Tests for the test quality rubric structure."""

    def test_test_quality_rubric_has_five_criteria(self) -> None:
        """TEST_QUALITY_RUBRIC must contain exactly 5 criteria."""
        assert len(TEST_QUALITY_RUBRIC) == 5

    def test_test_quality_rubric_criteria_names(self) -> None:
        """Verify all expected criteria are present."""
        names = {criterion.name for criterion in TEST_QUALITY_RUBRIC}
        expected = {"Coverage", "Edge Cases", "Error Handling", "Naming", "Isolation"}
        assert names == expected


class TestAllCriteria:
    """Tests that apply to all criteria across all rubrics."""

    @pytest.fixture
    def all_criteria(self) -> list[EvaluationCriterion]:
        """Collect all criteria from all rubrics."""
        return CODE_REVIEW_RUBRIC + TEST_QUALITY_RUBRIC

    def test_all_criteria_have_descriptions(
        self, all_criteria: list[EvaluationCriterion]
    ) -> None:
        """Every criterion must have a non-empty description."""
        for criterion in all_criteria:
            assert criterion.description, f"{criterion.name} has no description"
            assert len(criterion.description) >= 10, (
                f"{criterion.name} description is too short"
            )

    def test_all_criteria_scales_are_valid(
        self, all_criteria: list[EvaluationCriterion]
    ) -> None:
        """All criteria must have valid scales (min >= 0, max > min)."""
        for criterion in all_criteria:
            min_val, max_val = criterion.scale
            assert min_val >= 0, f"{criterion.name} has negative min scale"
            assert max_val > min_val, f"{criterion.name} has invalid scale range"

    def test_all_criteria_have_positive_weights(
        self, all_criteria: list[EvaluationCriterion]
    ) -> None:
        """All criteria must have positive weights."""
        for criterion in all_criteria:
            assert criterion.weight > 0, f"{criterion.name} has non-positive weight"

    def test_all_criteria_have_names(
        self, all_criteria: list[EvaluationCriterion]
    ) -> None:
        """Every criterion must have a non-empty name."""
        for criterion in all_criteria:
            assert criterion.name, "Found criterion with empty name"
            assert len(criterion.name) >= 2, "Criterion name is too short"


class TestEvaluationCriterionDataclass:
    """Tests for the EvaluationCriterion dataclass itself."""

    def test_criterion_is_frozen(self) -> None:
        """EvaluationCriterion instances should be immutable."""
        criterion = EvaluationCriterion(
            name="Test",
            description="Test description",
            scale=(0, 2),
            weight=1.0,
        )
        with pytest.raises(AttributeError):
            criterion.name = "Modified"  # type: ignore[misc]

    def test_max_score_property(self) -> None:
        """max_score should return scale[1] * weight."""
        criterion = EvaluationCriterion(
            name="Test",
            description="Test description",
            scale=(0, 5),
            weight=2.0,
        )
        assert criterion.max_score == 10.0

    def test_min_score_property(self) -> None:
        """min_score should return scale[0] * weight."""
        criterion = EvaluationCriterion(
            name="Test",
            description="Test description",
            scale=(1, 5),
            weight=2.0,
        )
        assert criterion.min_score == 2.0

    def test_default_weight_is_one(self) -> None:
        """Default weight should be 1.0."""
        criterion = EvaluationCriterion(
            name="Test",
            description="Test description",
            scale=(0, 2),
        )
        assert criterion.weight == 1.0
