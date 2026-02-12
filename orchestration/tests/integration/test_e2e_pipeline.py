"""End-to-end integration tests for the orchestration pipeline.

These tests validate the full flow: task description → routing → agent
sequencing → model selection → evaluation. They use the real router,
judge, and rubrics modules with mocked LLM calls.

Each test follows the Foundational Algorithm (P2) as a scientific
experiment: hypothesis → setup → execute → verify.
"""

import pytest

from orchestration.judge import (
    CriterionScore,
    EvaluationReport,
    JudgeEngine,
)
from orchestration.router import (
    PRIORITY_TABLE,
    ROUTING_TABLE,
    TaskRouter,
    TaskType,
)
from orchestration.rubrics import (
    CODE_REVIEW_RUBRIC,
    TEST_QUALITY_RUBRIC,
    EvaluationCriterion,
)


pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Pipeline: Feature request
# ---------------------------------------------------------------------------


class TestFeatureRequestPipeline:
    """Hypothesis: A feature request routes through architect → performance-engineer
    → orchestrator with medium priority, selects the correct model, and
    produces a valid evaluation report."""

    def test_classifies_as_feature(self):
        router = TaskRouter()
        task_type = router.classify("Add input validation to the login form")
        assert task_type == TaskType.FEATURE

    def test_routes_to_architect_sequence(self):
        router = TaskRouter()
        decision = router.route("Add input validation to the login form")
        assert decision.agent_sequence == ["architect", "performance-engineer", "orchestrator"]

    def test_feature_has_medium_priority(self):
        router = TaskRouter()
        decision = router.route("Add input validation to the login form")
        assert decision.priority == "medium"

    def test_routing_table_enforces_architecture_first(self):
        """Architecture first: features must start with architect."""
        sequence = ROUTING_TABLE[TaskType.FEATURE]
        assert sequence[0] == "architect"

    def test_full_pipeline_with_mock_judge(self):
        """Full pipeline: route → evaluate with mock judge → valid report."""
        router = TaskRouter()
        engine = JudgeEngine()

        # Step 1: Route
        decision = router.route("Create a user registration feature")
        assert decision.task_type == TaskType.FEATURE

        # Step 2: Use CODE_REVIEW_RUBRIC (it's a list of EvaluationCriterion)
        rubric = CODE_REVIEW_RUBRIC

        # Step 3: Mock judge function that returns structured output
        def mock_judge(prompt: str) -> str:
            lines = []
            for criterion in rubric:
                lines.append(f"## {criterion.name}")
                lines.append(f"Score: {criterion.scale[1]}")
                lines.append(f"Reasoning: Meets {criterion.name} requirements.\n")
            lines.append("Overall: Good implementation.")
            return "\n".join(lines)

        # Step 4: Evaluate
        report = engine.evaluate(
            response="def register(user): ...",
            rubric=rubric,
            judge_fn=mock_judge,
            reference="def register(user): validate(user); save(user)",
        )

        # Step 5: Verify
        assert isinstance(report, EvaluationReport)
        assert report.total >= 0
        assert report.confidence >= 0
        assert len(report.scores) == len(rubric)
        assert report.reasoning != ""


# ---------------------------------------------------------------------------
# Pipeline: Bug fix
# ---------------------------------------------------------------------------


class TestBugFixPipeline:
    """Hypothesis: A bug report routes through performance-engineer → orchestrator
    → reviewer with high priority."""

    def test_classifies_as_bug_fix(self):
        router = TaskRouter()
        task_type = router.classify("Fix the null pointer error in auth module")
        assert task_type == TaskType.BUG_FIX

    def test_routes_to_performance_sequence(self):
        router = TaskRouter()
        decision = router.route("Fix the null pointer error in auth module")
        assert decision.agent_sequence == ["performance-engineer", "orchestrator", "reviewer"]

    def test_bug_fix_has_high_priority(self):
        router = TaskRouter()
        decision = router.route("Fix the null pointer error in auth module")
        assert decision.priority == "high"

    def test_tdd_enforced_for_bugs(self):
        """TDD enforcement: bugs must start with performance-engineer."""
        sequence = ROUTING_TABLE[TaskType.BUG_FIX]
        assert sequence[0] == "performance-engineer"

    def test_bug_fix_pipeline_with_judge(self):
        """Full pipeline: route → evaluate → verify score structure."""
        router = TaskRouter()
        engine = JudgeEngine()

        decision = router.route("Fix broken authentication flow")
        assert decision.task_type == TaskType.BUG_FIX
        assert decision.priority == "high"

        rubric = CODE_REVIEW_RUBRIC

        def mock_judge(prompt: str) -> str:
            return "\n".join(
                f"## {c.name}\nScore: {c.scale[1]}\nReasoning: Adequate.\n"
                for c in rubric
            ) + "\nOverall: Bug fixed adequately."

        report = engine.evaluate(
            response="def auth(): try: validate() except: handle()",
            rubric=rubric,
            judge_fn=mock_judge,
        )

        assert isinstance(report, EvaluationReport)
        assert all(isinstance(s, CriterionScore) for s in report.scores)


# ---------------------------------------------------------------------------
# Pipeline: Unknown task escalation
# ---------------------------------------------------------------------------


class TestUnknownTaskEscalation:
    """Hypothesis: An unclassifiable task returns UNKNOWN type and routes
    to the orchestrator agent. This validates P16 (Permission to Fail)."""

    def test_classifies_as_unknown(self):
        router = TaskRouter()
        task_type = router.classify("Something completely ambiguous")
        assert task_type == TaskType.UNKNOWN

    def test_empty_input_is_unknown(self):
        router = TaskRouter()
        assert router.classify("") == TaskType.UNKNOWN
        assert router.classify("   ") == TaskType.UNKNOWN

    def test_routes_to_orchestrator(self):
        router = TaskRouter()
        decision = router.route("Something completely ambiguous")
        assert decision.agent_sequence == ["orchestrator"]

    def test_unknown_has_low_priority(self):
        router = TaskRouter()
        decision = router.route("Something completely ambiguous")
        assert decision.priority == "low"

    def test_all_task_types_have_routing(self):
        """Every TaskType must have an entry in the routing table."""
        for task_type in TaskType:
            assert task_type in ROUTING_TABLE, f"Missing routing for {task_type}"

    def test_all_task_types_have_priority(self):
        """Every TaskType must have an entry in the priority table."""
        for task_type in TaskType:
            assert task_type in PRIORITY_TABLE, f"Missing priority for {task_type}"


# ---------------------------------------------------------------------------
# Pipeline: Review
# ---------------------------------------------------------------------------


class TestReviewPipeline:
    """Hypothesis: A review request routes directly to the reviewer agent."""

    def test_classifies_as_review(self):
        router = TaskRouter()
        assert router.classify("Review PR #42") == TaskType.REVIEW

    def test_routes_to_reviewer_only(self):
        router = TaskRouter()
        decision = router.route("Review the pull request changes")
        assert decision.agent_sequence == ["reviewer"]

    def test_review_has_medium_priority(self):
        router = TaskRouter()
        decision = router.route("Review this code")
        assert decision.priority == "medium"


# ---------------------------------------------------------------------------
# Pipeline: Context extraction
# ---------------------------------------------------------------------------


class TestContextExtraction:
    """Hypothesis: The router extracts file paths from task descriptions."""

    def test_extracts_python_file(self):
        router = TaskRouter()
        decision = router.route("Add tests to orchestration/router.py")
        assert "orchestration/router.py" in decision.context.get("files", [])

    def test_extracts_multiple_files(self):
        router = TaskRouter()
        decision = router.route("Fix cli.py and update config.yaml")
        files = decision.context.get("files", [])
        assert "cli.py" in files
        assert "config.yaml" in files

    def test_no_files_extracted_for_plain_task(self):
        router = TaskRouter()
        decision = router.route("Add a new feature")
        assert "files" not in decision.context or decision.context["files"] == []


# ---------------------------------------------------------------------------
# Pipeline: Rubric integration
# ---------------------------------------------------------------------------


class TestRubricIntegration:
    """Hypothesis: Rubrics are valid and usable by the judge engine."""

    def test_code_review_rubric_is_valid(self):
        assert len(CODE_REVIEW_RUBRIC) > 0
        for c in CODE_REVIEW_RUBRIC:
            assert isinstance(c, EvaluationCriterion)
            assert c.name
            assert c.description
            assert c.scale[0] < c.scale[1]

    def test_test_quality_rubric_is_valid(self):
        assert len(TEST_QUALITY_RUBRIC) > 0
        for c in TEST_QUALITY_RUBRIC:
            assert isinstance(c, EvaluationCriterion)

    def test_judge_engine_accepts_rubric_criteria(self):
        engine = JudgeEngine()
        rubric = CODE_REVIEW_RUBRIC

        def mock_judge(prompt: str) -> str:
            return "Score: 1\nReasoning: OK."

        report = engine.evaluate(
            response="code here",
            rubric=rubric,
            judge_fn=mock_judge,
        )
        assert isinstance(report, EvaluationReport)

    def test_multi_model_ensemble_with_rubric(self):
        engine = JudgeEngine()
        rubric = CODE_REVIEW_RUBRIC

        def make_judge(score: int):
            def judge_fn(prompt: str) -> str:
                return f"Score: {score}\nReasoning: Rated {score}."
            return judge_fn

        report = engine.multi_model_ensemble(
            response="implementation code",
            rubric=rubric,
            judge_fns=[make_judge(1), make_judge(2), make_judge(1)],
        )

        assert isinstance(report, EvaluationReport)
        assert report.confidence >= 0
        assert "Multi-model ensemble" in report.reasoning
