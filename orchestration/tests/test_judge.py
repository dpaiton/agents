"""Tests for the judge engine.

These tests define the specification for correct behavior.
They are written first, following TDD principles (P7: Spec / Test / Evals First).
"""

import pytest

from orchestration.judge import (
    BiasChecklistItem,
    CriterionScore,
    EvaluationCriterion,
    EvaluationReport,
    JudgeEngine,
    PairwiseResult,
)


class TestEvaluationCriterion:
    """Tests for EvaluationCriterion dataclass."""

    def test_criterion_has_required_fields(self):
        """Criterion must have name, description, scale, and weight."""
        criterion = EvaluationCriterion(
            name="accuracy",
            description="How accurate is the response?",
            scale=(1, 5),
            weight=1.0,
        )
        assert criterion.name == "accuracy"
        assert criterion.description == "How accurate is the response?"
        assert criterion.scale == (1, 5)
        assert criterion.weight == 1.0

    def test_criterion_default_weight(self):
        """Weight should default to 1.0."""
        criterion = EvaluationCriterion(
            name="clarity",
            description="How clear is the response?",
            scale=(1, 5),
        )
        assert criterion.weight == 1.0


class TestCriterionScore:
    """Tests for CriterionScore dataclass."""

    def test_score_has_required_fields(self):
        """Score must have criterion, score, and reasoning."""
        criterion = EvaluationCriterion(
            name="accuracy",
            description="How accurate?",
            scale=(1, 5),
        )
        score = CriterionScore(
            criterion=criterion,
            score=4,
            reasoning="The response is mostly accurate with minor issues.",
        )
        assert score.criterion == criterion
        assert score.score == 4
        assert score.reasoning == "The response is mostly accurate with minor issues."


class TestEvaluationReport:
    """Tests for EvaluationReport dataclass."""

    def test_report_has_required_fields(self):
        """Report must have scores, total, reasoning, bias_checklist, safety_flag, confidence."""
        criterion = EvaluationCriterion(
            name="accuracy",
            description="How accurate?",
            scale=(1, 5),
        )
        score = CriterionScore(
            criterion=criterion,
            score=4,
            reasoning="Good accuracy.",
        )
        checklist = [
            BiasChecklistItem(
                name="position_bias",
                checked=True,
                notes="Evaluated in both positions",
            )
        ]
        report = EvaluationReport(
            scores=[score],
            total=4.0,
            reasoning="Overall good response.",
            bias_checklist=checklist,
            safety_flag=False,
            confidence=0.9,
        )
        assert len(report.scores) == 1
        assert report.total == 4.0
        assert report.reasoning == "Overall good response."
        assert len(report.bias_checklist) == 1
        assert report.safety_flag is False
        assert report.confidence == 0.9


class TestJudgeEnginePromptBuilding:
    """Tests for JudgeEngine prompt building functionality."""

    def test_build_evaluation_prompt_includes_rubric(self):
        """Evaluation prompt must include the rubric criteria."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="accuracy",
                description="How accurate is the response?",
                scale=(1, 5),
            ),
            EvaluationCriterion(
                name="clarity",
                description="How clear is the response?",
                scale=(1, 3),
            ),
        ]
        prompt = engine.build_evaluation_prompt(
            response="Test response",
            rubric=rubric,
        )
        assert "accuracy" in prompt
        assert "How accurate is the response?" in prompt
        assert "1-5" in prompt or "(1, 5)" in prompt or "1 to 5" in prompt
        assert "clarity" in prompt
        assert "How clear is the response?" in prompt

    def test_build_evaluation_prompt_includes_reference_when_provided(self):
        """Prompt must include reference answer when available."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="accuracy",
                description="How accurate?",
                scale=(1, 5),
            ),
        ]
        prompt = engine.build_evaluation_prompt(
            response="Test response",
            rubric=rubric,
            reference="Reference answer",
        )
        assert "Reference answer" in prompt

    def test_build_pairwise_prompt_includes_both_responses(self):
        """Pairwise prompt must include both responses."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="accuracy",
                description="How accurate?",
                scale=(1, 5),
            ),
        ]
        prompt = engine.build_pairwise_prompt(
            response_a="Response A content",
            response_b="Response B content",
            rubric=rubric,
        )
        assert "Response A content" in prompt
        assert "Response B content" in prompt


class TestReasoningRequiredBeforeScore:
    """Test that judge must provide reasoning before any numeric score (P5)."""

    def test_reasoning_required_before_score(self):
        """Judge must provide reasoning before any numeric score."""
        engine = JudgeEngine()
        criterion = EvaluationCriterion(
            name="accuracy",
            description="How accurate?",
            scale=(1, 5),
        )

        # Valid: reasoning comes before score
        valid_response = """
        Reasoning: The response accurately addresses the question with clear examples.
        Score: 4
        """
        score = engine.parse_criterion_score(valid_response, criterion)
        assert score.reasoning is not None
        assert len(score.reasoning) > 0
        assert score.score == 4

        # Invalid: score without reasoning should raise
        invalid_response = "Score: 4"
        with pytest.raises(ValueError, match="[Rr]easoning.*required|[Rr]easoning.*before"):
            engine.parse_criterion_score(invalid_response, criterion)


class TestDiscreteScoringOnly:
    """Test that scores must be integers from the rubric scale (P5: deterministic validation)."""

    def test_discrete_scoring_only(self):
        """Scores must be integers from the rubric scale, no partial scores."""
        engine = JudgeEngine()
        criterion = EvaluationCriterion(
            name="accuracy",
            description="How accurate?",
            scale=(1, 5),
        )

        # Valid integer score within range
        valid_response = "Reasoning: Good response.\nScore: 3"
        score = engine.parse_criterion_score(valid_response, criterion)
        assert score.score == 3
        assert isinstance(score.score, int)

        # Invalid: decimal score
        decimal_response = "Reasoning: Good response.\nScore: 3.5"
        with pytest.raises(ValueError, match="[Ii]nteger|[Dd]iscrete|[Ww]hole"):
            engine.parse_criterion_score(decimal_response, criterion)

        # Invalid: score out of range (too high)
        out_of_range_high = "Reasoning: Excellent.\nScore: 6"
        with pytest.raises(ValueError, match="[Rr]ange|[Ss]cale|[Bb]etween"):
            engine.parse_criterion_score(out_of_range_high, criterion)

        # Invalid: score out of range (too low)
        out_of_range_low = "Reasoning: Terrible.\nScore: 0"
        with pytest.raises(ValueError, match="[Rr]ange|[Ss]cale|[Bb]etween"):
            engine.parse_criterion_score(out_of_range_low, criterion)


class TestPairwiseDebiasing:
    """Tests for pairwise comparison debiasing (P4: scaffolding structures the ensemble)."""

    def test_pairwise_debiasing_swaps_positions(self):
        """Pairwise comparison runs twice with swapped positions (bias mitigation)."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="quality",
                description="Overall quality",
                scale=(1, 5),
            ),
        ]

        # Mock judge function that returns consistent results
        call_log = []

        def mock_judge(prompt: str) -> str:
            call_log.append(prompt)
            # Always prefer whichever is labeled "Response A" (simulating position bias)
            return "Reasoning: Response A is better.\nWinner: A"

        result = engine.pairwise_compare(
            response_a="First response",
            response_b="Second response",
            rubric=rubric,
            judge_fn=mock_judge,
        )

        # Should have been called twice (original and swapped)
        assert len(call_log) == 2

        # First call should have original order
        assert "First response" in call_log[0]
        assert "Second response" in call_log[0]

        # Second call should have swapped order
        # The second prompt should have responses in opposite positions
        first_positions = (
            call_log[0].find("First response"),
            call_log[0].find("Second response"),
        )
        second_positions = (
            call_log[1].find("First response"),
            call_log[1].find("Second response"),
        )
        # In first call, First response should come before Second response
        # In second call, Second response should come before First response
        assert first_positions[0] < first_positions[1]
        assert second_positions[1] < second_positions[0]

    def test_pairwise_flags_unstable_preference(self):
        """If swapping positions changes the winner, flag as unstable (P16)."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="quality",
                description="Overall quality",
                scale=(1, 5),
            ),
        ]

        # Mock judge that exhibits position bias (always picks A)
        def biased_judge(prompt: str) -> str:
            return "Reasoning: Response A is clearly better.\nWinner: A"

        result = engine.pairwise_compare(
            response_a="First response",
            response_b="Second response",
            rubric=rubric,
            judge_fn=biased_judge,
        )

        # Result should be flagged as unstable since swapping changed winner
        assert isinstance(result, PairwiseResult)
        assert result.stable is False
        assert result.confidence < 1.0

    def test_pairwise_stable_when_consistent(self):
        """When both orderings agree, result should be stable with high confidence."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="quality",
                description="Overall quality",
                scale=(1, 5),
            ),
        ]

        # Mock judge that consistently prefers the actual first response
        def consistent_judge(prompt: str) -> str:
            if "First response" in prompt.split("Response A")[1].split("Response B")[0]:
                return "Reasoning: Response A is better.\nWinner: A"
            else:
                return "Reasoning: Response B is better.\nWinner: B"

        result = engine.pairwise_compare(
            response_a="First response",
            response_b="Second response",
            rubric=rubric,
            judge_fn=consistent_judge,
        )

        assert result.stable is True
        assert result.confidence == 1.0
        assert result.winner == "A"  # The original response_a


class TestGroundTruthBypass:
    """Test that reference answers enable direct evaluation (P6: simpler approach)."""

    def test_ground_truth_bypass(self):
        """When a reference answer exists, skip pairwise and evaluate directly."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="accuracy",
                description="How accurate compared to reference?",
                scale=(1, 5),
            ),
        ]

        def mock_judge(prompt: str) -> str:
            # Direct evaluation should include reference
            assert "Reference:" in prompt or "reference" in prompt.lower()
            return "Reasoning: Matches reference well.\nScore: 4"

        report = engine.evaluate(
            response="Test response",
            rubric=rubric,
            reference="The correct answer",
            judge_fn=mock_judge,
        )

        assert isinstance(report, EvaluationReport)
        assert len(report.scores) == 1
        assert report.scores[0].score == 4


class TestSafetyCriticalEscalation:
    """Test safety escalation (P16: escalate when uncertain)."""

    def test_safety_critical_escalation(self):
        """Safety issues escalate to human review regardless of score."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="helpfulness",
                description="How helpful?",
                scale=(1, 5),
            ),
        ]

        # Response that triggers safety concern
        def safety_detecting_judge(prompt: str) -> str:
            return """
            Reasoning: The response is helpful but contains potentially harmful instructions.
            Score: 4
            Safety: CONCERN - Contains instructions that could be misused
            """

        report = engine.evaluate(
            response="Here's how to do that dangerous thing...",
            rubric=rubric,
            judge_fn=safety_detecting_judge,
        )

        # Safety flag should be set regardless of high score
        assert report.safety_flag is True
        # Should include safety concern in reasoning or have safety notes
        assert "safety" in report.reasoning.lower() or report.safety_flag


class TestEnsembleMajorityVote:
    """Test ensemble voting (P4: scaffolding structures the ensemble)."""

    def test_ensemble_majority_vote(self):
        """Multiple judges vote, majority wins."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="quality",
                description="Overall quality",
                scale=(1, 5),
            ),
        ]

        # Simulate 3 judges with different opinions (2 agree, 1 disagrees)
        call_count = [0]

        def varied_judges(prompt: str) -> str:
            call_count[0] += 1
            if call_count[0] <= 2:
                return "Reasoning: Good response.\nScore: 4"
            else:
                return "Reasoning: Poor response.\nScore: 2"

        result = engine.ensemble_vote(
            response="Test response",
            rubric=rubric,
            n_judges=3,
            judge_fn=varied_judges,
        )

        # Majority (2/3) gave score 4
        assert result.total == 4.0 or abs(result.total - 4.0) < 0.5
        # Confidence should reflect agreement level
        assert result.confidence >= 0.66  # 2/3 agreement


class TestBiasChecklist:
    """Test that every evaluation includes a bias checklist."""

    def test_bias_checklist_included(self):
        """Every evaluation output includes a completed bias checklist."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="quality",
                description="Overall quality",
                scale=(1, 5),
            ),
        ]

        def mock_judge(prompt: str) -> str:
            return "Reasoning: Good response.\nScore: 4"

        report = engine.evaluate(
            response="Test response",
            rubric=rubric,
            judge_fn=mock_judge,
        )

        # Must have bias checklist
        assert report.bias_checklist is not None
        assert len(report.bias_checklist) > 0

        # Each checklist item must have name, checked status, and notes
        for item in report.bias_checklist:
            assert isinstance(item, BiasChecklistItem)
            assert item.name is not None
            assert isinstance(item.checked, bool)
            assert item.notes is not None

    def test_pairwise_bias_checklist_includes_position_check(self):
        """Pairwise evaluation checklist must include position bias check."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="quality",
                description="Overall quality",
                scale=(1, 5),
            ),
        ]

        def mock_judge(prompt: str) -> str:
            return "Reasoning: Response A is better.\nWinner: A"

        result = engine.pairwise_compare(
            response_a="First",
            response_b="Second",
            rubric=rubric,
            judge_fn=mock_judge,
        )

        # Should have position bias check in checklist
        position_bias_checked = any(
            "position" in item.name.lower() for item in result.bias_checklist
        )
        assert position_bias_checked


class TestConfidenceScoring:
    """Tests for confidence scoring based on agreement and stability."""

    def test_confidence_drops_on_ensemble_disagreement(self):
        """Low ensemble agreement should reduce confidence."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="quality",
                description="Overall quality",
                scale=(1, 5),
            ),
        ]

        # All judges disagree
        call_count = [0]

        def disagreeing_judges(prompt: str) -> str:
            call_count[0] += 1
            scores = [1, 3, 5]  # Maximum disagreement
            return f"Reasoning: My opinion.\nScore: {scores[(call_count[0] - 1) % 3]}"

        result = engine.ensemble_vote(
            response="Test response",
            rubric=rubric,
            n_judges=3,
            judge_fn=disagreeing_judges,
        )

        # Confidence should be lower due to disagreement
        assert result.confidence < 0.7

    def test_confidence_high_on_full_agreement(self):
        """Full ensemble agreement should yield high confidence."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="quality",
                description="Overall quality",
                scale=(1, 5),
            ),
        ]

        def agreeing_judges(prompt: str) -> str:
            return "Reasoning: Excellent response.\nScore: 5"

        result = engine.ensemble_vote(
            response="Test response",
            rubric=rubric,
            n_judges=3,
            judge_fn=agreeing_judges,
        )

        assert result.confidence >= 0.9


class TestMultiModelEnsemble:
    """Tests for multi_model_ensemble() with heterogeneous judge backends."""

    def test_multi_model_ensemble_basic(self):
        """Three judge_fns all succeed, returns aggregated report."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="quality",
                description="Overall quality",
                scale=(1, 5),
            ),
        ]

        def judge_a(prompt: str) -> str:
            return "Reasoning: Good.\nScore: 4"

        def judge_b(prompt: str) -> str:
            return "Reasoning: Decent.\nScore: 3"

        def judge_c(prompt: str) -> str:
            return "Reasoning: Great.\nScore: 4"

        report = engine.multi_model_ensemble(
            response="Test response",
            rubric=rubric,
            judge_fns=[judge_a, judge_b, judge_c],
        )

        assert isinstance(report, EvaluationReport)
        assert "3/3" in report.reasoning
        assert report.confidence > 0
        assert len(report.scores) == 1
        # Median of [4, 3, 4] = 4
        assert report.scores[0].score == 4

    def test_multi_model_ensemble_partial_failure(self):
        """1 of 3 judges fails, still returns a valid report from the other 2."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="quality",
                description="Overall quality",
                scale=(1, 5),
            ),
        ]

        def judge_ok(prompt: str) -> str:
            return "Reasoning: Fine.\nScore: 4"

        def judge_fail(prompt: str) -> str:
            raise RuntimeError("API error")

        report = engine.multi_model_ensemble(
            response="Test response",
            rubric=rubric,
            judge_fns=[judge_ok, judge_fail, judge_ok],
        )

        assert isinstance(report, EvaluationReport)
        assert "2/3" in report.reasoning
        assert report.confidence > 0

    def test_multi_model_ensemble_all_fail(self):
        """All judges fail, returns 0 confidence with empty scores."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="quality",
                description="Overall quality",
                scale=(1, 5),
            ),
        ]

        def judge_fail(prompt: str) -> str:
            raise RuntimeError("API error")

        report = engine.multi_model_ensemble(
            response="Test response",
            rubric=rubric,
            judge_fns=[judge_fail, judge_fail, judge_fail],
        )

        assert report.confidence == 0.0
        assert report.total == 0.0
        assert report.scores == []
        assert "0/3" in report.reasoning

    def test_multi_model_ensemble_agreement(self):
        """Identical judges should yield 100% agreement and high confidence."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="quality",
                description="Overall quality",
                scale=(1, 5),
            ),
        ]

        def judge_same(prompt: str) -> str:
            return "Reasoning: Excellent.\nScore: 5"

        report = engine.multi_model_ensemble(
            response="Test response",
            rubric=rubric,
            judge_fns=[judge_same, judge_same, judge_same],
        )

        assert "Agreement: 100%" in report.reasoning
        assert report.confidence >= 0.9
        assert report.total == 5.0

    def test_multi_model_ensemble_has_cross_model_bias_check(self):
        """Bias checklist should include cross_model_bias."""
        engine = JudgeEngine()
        rubric = [
            EvaluationCriterion(
                name="quality",
                description="Overall quality",
                scale=(1, 5),
            ),
        ]

        def judge(prompt: str) -> str:
            return "Reasoning: OK.\nScore: 3"

        report = engine.multi_model_ensemble(
            response="Test response",
            rubric=rubric,
            judge_fns=[judge],
        )

        cross_model_check = [
            item for item in report.bias_checklist
            if item.name == "cross_model_bias"
        ]
        assert len(cross_model_check) == 1
        assert cross_model_check[0].checked is True
