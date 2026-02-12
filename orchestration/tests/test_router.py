"""Tests for the task router module.

Tests define routing behavior before implementation (TDD - P7).
"""

import pytest

from orchestration.router import (
    TaskType,
    RoutingDecision,
    TaskRouter,
    ROUTING_TABLE,
)


class TestTaskTypeEnum:
    """Tests for TaskType enum values."""

    def test_task_type_has_feature(self):
        assert TaskType.FEATURE.value == "feature"

    def test_task_type_has_bug_fix(self):
        assert TaskType.BUG_FIX.value == "bug_fix"

    def test_task_type_has_review(self):
        assert TaskType.REVIEW.value == "review"

    def test_task_type_has_docs(self):
        assert TaskType.DOCS.value == "docs"

    def test_task_type_has_infrastructure(self):
        assert TaskType.INFRASTRUCTURE.value == "infrastructure"

    def test_task_type_has_unknown(self):
        assert TaskType.UNKNOWN.value == "unknown"


class TestRoutingDecision:
    """Tests for RoutingDecision dataclass."""

    def test_routing_decision_has_task_type(self):
        decision = RoutingDecision(
            task_type=TaskType.FEATURE,
            agent_sequence=["architect", "performance-engineer", "orchestrator"],
            priority="high",
            context={},
        )
        assert decision.task_type == TaskType.FEATURE

    def test_routing_decision_has_agent_sequence(self):
        decision = RoutingDecision(
            task_type=TaskType.FEATURE,
            agent_sequence=["architect", "performance-engineer", "orchestrator"],
            priority="high",
            context={},
        )
        assert decision.agent_sequence == ["architect", "performance-engineer", "orchestrator"]

    def test_routing_decision_has_priority(self):
        decision = RoutingDecision(
            task_type=TaskType.FEATURE,
            agent_sequence=["architect", "performance-engineer", "orchestrator"],
            priority="high",
            context={},
        )
        assert decision.priority == "high"

    def test_routing_decision_has_context(self):
        decision = RoutingDecision(
            task_type=TaskType.FEATURE,
            agent_sequence=["architect", "performance-engineer", "orchestrator"],
            priority="high",
            context={"files": ["router.py"]},
        )
        assert decision.context == {"files": ["router.py"]}


class TestRoutingTable:
    """Tests for the ROUTING_TABLE constant."""

    def test_routing_table_has_feature(self):
        assert TaskType.FEATURE in ROUTING_TABLE

    def test_routing_table_has_bug_fix(self):
        assert TaskType.BUG_FIX in ROUTING_TABLE

    def test_routing_table_has_review(self):
        assert TaskType.REVIEW in ROUTING_TABLE

    def test_routing_table_has_docs(self):
        assert TaskType.DOCS in ROUTING_TABLE

    def test_routing_table_has_infrastructure(self):
        assert TaskType.INFRASTRUCTURE in ROUTING_TABLE

    def test_routing_table_has_unknown(self):
        assert TaskType.UNKNOWN in ROUTING_TABLE


class TestTaskRouterClassify:
    """Tests for TaskRouter.classify() method."""

    @pytest.fixture
    def router(self):
        return TaskRouter()

    # Feature classification tests
    def test_classify_feature_from_feature_keyword(self, router):
        assert router.classify("implement a new feature for login") == TaskType.FEATURE

    def test_classify_feature_from_add_keyword(self, router):
        assert router.classify("add user authentication") == TaskType.FEATURE

    def test_classify_feature_from_create_keyword(self, router):
        # "create" matches DESIGN first if it's about UI, but for backend components it's FEATURE
        assert router.classify("create a new authentication endpoint") == TaskType.FEATURE

    def test_classify_feature_from_implement_keyword(self, router):
        assert router.classify("implement password reset flow") == TaskType.FEATURE

    # Bug fix classification tests
    def test_classify_bug_fix_from_bug_keyword(self, router):
        assert router.classify("fix bug in login page") == TaskType.BUG_FIX

    def test_classify_bug_fix_from_fix_keyword(self, router):
        assert router.classify("fix the broken navbar") == TaskType.BUG_FIX

    def test_classify_bug_fix_from_broken_keyword(self, router):
        assert router.classify("the dashboard is broken") == TaskType.BUG_FIX

    def test_classify_bug_fix_from_error_keyword(self, router):
        assert router.classify("error when submitting form") == TaskType.BUG_FIX

    def test_classify_bug_fix_from_issue_keyword(self, router):
        assert router.classify("issue with user registration") == TaskType.BUG_FIX

    # Review classification tests
    def test_classify_review_from_review_keyword(self, router):
        assert router.classify("review the pull request") == TaskType.REVIEW

    def test_classify_review_from_pr_keyword(self, router):
        assert router.classify("check PR #123") == TaskType.REVIEW

    def test_classify_review_from_pull_request_keyword(self, router):
        assert router.classify("pull request needs attention") == TaskType.REVIEW

    def test_classify_review_from_code_review_keyword(self, router):
        assert router.classify("code review for authentication module") == TaskType.REVIEW

    # Docs classification tests
    def test_classify_docs_from_docs_keyword(self, router):
        assert router.classify("update the docs") == TaskType.DOCS

    def test_classify_docs_from_documentation_keyword(self, router):
        # "documentation" with "api" matches ARCHITECTURE (api spec) first
        assert router.classify("improve documentation in README") == TaskType.DOCS

    def test_classify_docs_from_readme_keyword(self, router):
        assert router.classify("update the readme file") == TaskType.DOCS

    def test_classify_docs_from_docstring_keyword(self, router):
        assert router.classify("add docstrings to functions") == TaskType.DOCS

    # Infrastructure classification tests
    def test_classify_infrastructure_from_infra_keyword(self, router):
        assert router.classify("update infra for deployment") == TaskType.INFRASTRUCTURE

    def test_classify_infrastructure_from_infrastructure_keyword(self, router):
        assert router.classify("infrastructure changes needed") == TaskType.INFRASTRUCTURE

    def test_classify_infrastructure_from_ci_keyword(self, router):
        assert router.classify("update CI pipeline") == TaskType.INFRASTRUCTURE

    def test_classify_infrastructure_from_cd_keyword(self, router):
        assert router.classify("setup CD workflow") == TaskType.INFRASTRUCTURE

    def test_classify_infrastructure_from_deploy_keyword(self, router):
        assert router.classify("deploy to production") == TaskType.INFRASTRUCTURE

    def test_classify_infrastructure_from_pipeline_keyword(self, router):
        assert router.classify("update the pipeline") == TaskType.INFRASTRUCTURE

    def test_classify_infrastructure_from_devops_keyword(self, router):
        assert router.classify("devops task required") == TaskType.INFRASTRUCTURE

    # Unknown classification tests
    def test_classify_unknown_for_ambiguous_input(self, router):
        assert router.classify("something needs to happen") == TaskType.UNKNOWN

    def test_classify_unknown_for_empty_input(self, router):
        assert router.classify("") == TaskType.UNKNOWN

    def test_classify_is_case_insensitive(self, router):
        assert router.classify("FIX THE BUG") == TaskType.BUG_FIX
        assert router.classify("Add New Feature") == TaskType.FEATURE


class TestTaskRouterRoute:
    """Tests for TaskRouter.route() method."""

    @pytest.fixture
    def router(self):
        return TaskRouter()

    def test_new_feature_routes_to_architect_first(self, router):
        """New feature requests route to architect first for design."""
        decision = router.route("implement a new login feature")
        assert decision.task_type == TaskType.FEATURE
        assert decision.agent_sequence[0] == "architect"
        assert "performance-engineer" in decision.agent_sequence
        assert decision.agent_sequence.index("architect") < decision.agent_sequence.index("performance-engineer")

    def test_bug_fix_routes_to_performance_engineer_first(self, router):
        """Bug fixes route to performance-engineer first (reproduce with test)."""
        decision = router.route("fix bug in authentication")
        assert decision.task_type == TaskType.BUG_FIX
        assert decision.agent_sequence[0] == "performance-engineer"
        assert "orchestrator" in decision.agent_sequence
        assert decision.agent_sequence.index("performance-engineer") < decision.agent_sequence.index("orchestrator")

    def test_code_review_routes_to_reviewer(self, router):
        """Review requests go directly to reviewer agent."""
        decision = router.route("review the pull request #42")
        assert decision.task_type == TaskType.REVIEW
        assert decision.agent_sequence == ["reviewer"]

    def test_unknown_task_falls_back_to_orchestrator(self, router):
        """Unclassifiable tasks return to orchestrator for clarification (P16)."""
        decision = router.route("something unclear")
        assert decision.task_type == TaskType.UNKNOWN
        assert decision.agent_sequence == ["orchestrator"]

    def test_routing_returns_priority(self, router):
        """Routing decisions include a priority level."""
        decision = router.route("implement new feature")
        assert decision.priority in ["high", "medium", "low"]

    def test_routing_extracts_context(self, router):
        """Router extracts relevant context (files, modules) from the task description."""
        decision = router.route("fix bug in orchestration/router.py module")
        assert "files" in decision.context or "modules" in decision.context

    def test_routing_extracts_file_paths(self, router):
        """Router extracts file paths from task description."""
        decision = router.route("update the file src/utils/helpers.py")
        assert "files" in decision.context
        assert "src/utils/helpers.py" in decision.context["files"]

    def test_routing_extracts_multiple_files(self, router):
        """Router extracts multiple file paths from task description."""
        decision = router.route("refactor main.py and utils.py")
        assert "files" in decision.context
        assert "main.py" in decision.context["files"]
        assert "utils.py" in decision.context["files"]

    def test_docs_routes_to_architect(self, router):
        """Documentation tasks route to architect for API docs."""
        decision = router.route("update the documentation")
        assert decision.task_type == TaskType.DOCS
        assert decision.agent_sequence == ["architect"]

    def test_infrastructure_routes_to_architect_and_infra_engineer(self, router):
        """Infrastructure tasks route to architect then infrastructure-engineer."""
        decision = router.route("update CI pipeline")
        assert decision.task_type == TaskType.INFRASTRUCTURE
        assert decision.agent_sequence == ["architect", "infrastructure-engineer", "reviewer"]

    def test_feature_routes_to_orchestrator(self, router):
        """Feature tasks route to orchestrator who picks specialist."""
        decision = router.route("implement new authentication")
        assert decision.agent_sequence[-1] == "orchestrator"

    def test_bug_fix_includes_reviewer(self, router):
        """Bug fix tasks include reviewer at the end."""
        decision = router.route("fix login error")
        assert decision.agent_sequence[-1] == "reviewer"


class TestUnitySpaceSimRouting:
    """Tests for Unity Space Sim project-specific routing."""

    @pytest.fixture
    def router(self):
        return TaskRouter()

    # Unity Space Sim task type tests
    def test_unity_space_sim_task_types_exist(self):
        """Verify Unity Space Sim task types are defined."""
        assert TaskType.UNITY_ASSET_DESIGN.value == "unity_asset_design"
        assert TaskType.BLENDER_SCRIPTING.value == "blender_scripting"
        assert TaskType.UNITY_SCRIPTING.value == "unity_scripting"
        assert TaskType.GAMEDEV_INTEGRATION.value == "gamedev_integration"

    def test_unity_space_sim_task_types_in_routing_table(self):
        """Verify Unity Space Sim task types have routing entries."""
        assert TaskType.UNITY_ASSET_DESIGN in ROUTING_TABLE
        assert TaskType.BLENDER_SCRIPTING in ROUTING_TABLE
        assert TaskType.UNITY_SCRIPTING in ROUTING_TABLE
        assert TaskType.GAMEDEV_INTEGRATION in ROUTING_TABLE

    # Keyword-based routing tests
    def test_blender_keyword_routes_to_blender_engineer(self, router):
        """Tasks mentioning Blender route to blender-engineer."""
        decision = router.route("Write Blender Python script to generate LODs")
        assert decision.task_type == TaskType.BLENDER_SCRIPTING
        assert "blender-engineer" in decision.agent_sequence

    def test_unity_keyword_routes_to_unity_engineer(self, router):
        """Tasks mentioning Unity route to unity-engineer."""
        decision = router.route("Create Unity C# script for ship flight controls")
        assert decision.task_type == TaskType.UNITY_SCRIPTING
        assert "unity-engineer" in decision.agent_sequence

    def test_asset_design_keyword_routes_to_unity_asset_designer(self, router):
        """Tasks about asset design route to unity-asset-designer."""
        decision = router.route("Design a cargo ship asset for Unity Space Sim")
        assert decision.task_type == TaskType.UNITY_ASSET_DESIGN
        assert decision.agent_sequence == ["unity-asset-designer"]

    def test_asset_pipeline_routes_to_gamedev_integration(self, router):
        """Asset pipeline validation routes to gamedev-integration-engineer."""
        decision = router.route("Test Blender to Unity asset pipeline end-to-end")
        assert decision.task_type == TaskType.GAMEDEV_INTEGRATION
        assert "gamedev-integration-engineer" in decision.agent_sequence

    def test_poly_count_validation_routes_to_gamedev_integration(self, router):
        """Poly count validation routes to gamedev-integration-engineer."""
        decision = router.route("Validate poly count meets budget requirements")
        assert decision.task_type == TaskType.GAMEDEV_INTEGRATION

    # Path-based routing tests
    def test_blender_path_routes_to_blender_engineer(self, router):
        """Files in projects/unity-space-sim/blender/ route to blender-engineer."""
        decision = router.route("Fix bug in projects/unity-space-sim/blender/generate_ship.py")
        assert decision.context.get("project") == "unity-space-sim"
        assert decision.task_type == TaskType.BLENDER_SCRIPTING
        assert "blender-engineer" in decision.agent_sequence

    def test_unity_path_routes_to_unity_engineer(self, router):
        """Files in projects/unity-space-sim/unity/ route to unity-engineer."""
        decision = router.route("Update projects/unity-space-sim/unity/FlightController.cs")
        assert decision.context.get("project") == "unity-space-sim"
        assert decision.task_type == TaskType.UNITY_SCRIPTING
        assert "unity-engineer" in decision.agent_sequence

    def test_unity_space_sim_project_context_detected(self, router):
        """Tasks with unity-space-sim paths set project context."""
        decision = router.route("Update file in projects/unity-space-sim/docs/README.md")
        assert decision.context.get("project") == "unity-space-sim"

    # Agent sequence tests
    def test_blender_engineer_includes_integration_testing(self, router):
        """Blender tasks include gamedev-integration-engineer for validation."""
        decision = router.route("Implement Blender script for procedural modeling")
        assert decision.task_type == TaskType.BLENDER_SCRIPTING
        assert "gamedev-integration-engineer" in decision.agent_sequence

    def test_unity_engineer_includes_integration_testing(self, router):
        """Unity tasks include gamedev-integration-engineer for validation."""
        decision = router.route("Add Unity component for ship controls")
        assert decision.task_type == TaskType.UNITY_SCRIPTING
        assert "gamedev-integration-engineer" in decision.agent_sequence

    def test_gamedev_integration_high_priority(self, router):
        """Pipeline validation tasks have high priority."""
        decision = router.route("Validate asset pipeline end-to-end")
        assert decision.task_type == TaskType.GAMEDEV_INTEGRATION
        assert decision.priority == "high"

    # Case sensitivity tests
    def test_unity_routing_is_case_insensitive(self, router):
        """Unity Space Sim routing is case-insensitive."""
        decision_lower = router.route("write blender script")
        decision_upper = router.route("Write BLENDER Script")
        assert decision_lower.task_type == decision_upper.task_type
        assert decision_lower.task_type == TaskType.BLENDER_SCRIPTING

    # File extension tests
    def test_cs_file_extension_detected(self, router):
        """C# files (.cs) are extracted from task descriptions."""
        decision = router.route("Fix bug in ShipController.cs")
        assert "files" in decision.context
        assert "ShipController.cs" in decision.context["files"]

    def test_fbx_file_extension_detected(self, router):
        """FBX files are extracted from task descriptions."""
        decision = router.route("Update cargo_ship.fbx export settings")
        assert "files" in decision.context
        assert "cargo_ship.fbx" in decision.context["files"]

    def test_blend_file_extension_detected(self, router):
        """Blender files (.blend) are extracted from task descriptions."""
        decision = router.route("Fix issue in ship_model.blend")
        assert "files" in decision.context
        assert "ship_model.blend" in decision.context["files"]
