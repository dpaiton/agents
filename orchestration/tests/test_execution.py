"""Tests for orchestration.execution — task execution engine."""

import os
from unittest.mock import MagicMock, patch

from orchestration.config import EcoConfig
from orchestration.execution import (
    AGENT_TOOLS,
    ECONOMY_DEMOTION,
    DeployEngine,
    ExecutionEngine,
    MODEL_SHORTHANDS,
    TaskRun,
    _agent_name_to_env_var,
    _estimate_tokens_for_task_type,
    _now_iso,
    _task_type_to_model_key,
    demote_model,
    resolve_model_shorthand,
)


# ---------------------------------------------------------------------------
# TaskRun tests
# ---------------------------------------------------------------------------


class TestTaskRun:
    def test_defaults(self):
        run = TaskRun(
            run_id="abc123",
            task="Add login",
            task_type="feature",
            agent_sequence=["architect", "performance-engineer", "orchestrator"],
            status="pending",
            model="claude-sonnet-4-20250514",
            started_at="2026-01-01T00:00:00Z",
        )
        assert run.run_id == "abc123"
        assert run.ended_at is None
        assert run.token_usage == {"input": 0, "output": 0}
        assert run.issue is None
        assert run.pr is None
        assert run.error is None
        assert run.dry_run is False

    def test_with_optional_fields(self):
        run = TaskRun(
            run_id="def456",
            task="Fix bug",
            task_type="bug_fix",
            agent_sequence=["performance-engineer", "orchestrator", "reviewer"],
            status="complete",
            model="claude-haiku-3-5-20241022",
            started_at="2026-01-01T00:00:00Z",
            ended_at="2026-01-01T00:01:00Z",
            token_usage={"input": 100, "output": 50},
            issue=42,
            pr=18,
        )
        assert run.issue == 42
        assert run.pr == 18
        assert run.token_usage == {"input": 100, "output": 50}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_now_iso_format(self):
        ts = _now_iso()
        assert ts.endswith("Z")
        assert "T" in ts
        assert len(ts) == 20  # YYYY-MM-DDTHH:MM:SSZ

    def test_task_type_to_model_key_feature(self):
        assert _task_type_to_model_key("feature") == "code-change"

    def test_task_type_to_model_key_bug_fix(self):
        assert _task_type_to_model_key("bug_fix") == "code-change"

    def test_task_type_to_model_key_review(self):
        assert _task_type_to_model_key("review") == "review"

    def test_task_type_to_model_key_docs(self):
        assert _task_type_to_model_key("docs") == "issue-body-edit"

    def test_task_type_to_model_key_unknown_falls_back(self):
        assert _task_type_to_model_key("something_else") == "code-change"

    def test_estimate_tokens_feature(self):
        result = _estimate_tokens_for_task_type("feature", 3)
        assert result["input_tokens"] == 6000  # 2000 * 3
        assert result["output_tokens"] == 4500  # 1500 * 3

    def test_estimate_tokens_unknown_type(self):
        result = _estimate_tokens_for_task_type("nonexistent", 1)
        assert result["input_tokens"] == 2000
        assert result["output_tokens"] == 1500


# ---------------------------------------------------------------------------
# Model shorthand and AGENT_TOOLS tests
# ---------------------------------------------------------------------------


class TestResolveModelShorthand:
    def test_opus(self):
        assert resolve_model_shorthand("opus") == MODEL_SHORTHANDS["opus"]

    def test_sonnet(self):
        assert resolve_model_shorthand("sonnet") == MODEL_SHORTHANDS["sonnet"]

    def test_haiku(self):
        assert resolve_model_shorthand("haiku") == MODEL_SHORTHANDS["haiku"]

    def test_full_model_id_passes_through(self):
        full_id = "claude-opus-4-20250514"
        assert resolve_model_shorthand(full_id) == full_id

    def test_unknown_passes_through(self):
        assert resolve_model_shorthand("custom-model") == "custom-model"


class TestDemoteModel:
    def test_opus_demotes_to_sonnet(self):
        assert demote_model("claude-opus-4-20250514") == "claude-sonnet-4-20250514"

    def test_sonnet_demotes_to_haiku(self):
        assert demote_model("claude-sonnet-4-20250514") == "claude-haiku-3-5-20241022"

    def test_haiku_stays_haiku(self):
        assert demote_model("claude-haiku-3-5-20241022") == "claude-haiku-3-5-20241022"

    def test_unknown_model_passes_through(self):
        assert demote_model("custom-model-v1") == "custom-model-v1"

    def test_all_shorthands_are_demotable(self):
        """Every model in MODEL_SHORTHANDS except haiku has a demotion entry."""
        for shorthand, model_id in MODEL_SHORTHANDS.items():
            if shorthand == "haiku":
                assert model_id not in ECONOMY_DEMOTION
            else:
                assert model_id in ECONOMY_DEMOTION


class TestAgentNameToEnvVar:
    def test_simple_agent(self):
        assert _agent_name_to_env_var("architect") == "ARCHITECT_MODEL"

    def test_hyphenated_agent(self):
        assert _agent_name_to_env_var("backend-engineer") == "BACKEND_ENGINEER_MODEL"

    def test_project_agent(self):
        assert _agent_name_to_env_var("blender-engineer") == "BLENDER_ENGINEER_MODEL"

    def test_multi_hyphen_agent(self):
        assert _agent_name_to_env_var("gamedev-integration-engineer") == "GAMEDEV_INTEGRATION_ENGINEER_MODEL"


class TestAgentTools:
    def test_engineering_agents_have_write_tools(self):
        for agent in [
            "backend-engineer",
            "blender-engineer",
            "unity-engineer",
            "orchestrator",
        ]:
            tools = AGENT_TOOLS[agent]
            assert "Bash" in tools
            assert "Write" in tools
            assert "Edit" in tools

    def test_readonly_agents_lack_write_tools(self):
        for agent in ["architect", "reviewer", "designer"]:
            tools = AGENT_TOOLS[agent]
            assert "Bash" not in tools
            assert "Write" not in tools
            assert "Read" in tools


# ---------------------------------------------------------------------------
# ExecutionEngine tests
# ---------------------------------------------------------------------------


class TestExecutionEngine:
    def test_plan_creates_pending_run(self, tmp_path):
        engine = ExecutionEngine(state_dir=tmp_path / "state")
        run = engine.plan("Add a login page")
        assert run.status == "pending"
        assert run.task == "Add a login page"
        assert run.task_type == "feature"
        assert "architect" in run.agent_sequence
        assert "performance-engineer" in run.agent_sequence
        assert "orchestrator" in run.agent_sequence
        assert run.run_id is not None
        assert len(run.run_id) == 12

    def test_plan_with_issue(self, tmp_path):
        engine = ExecutionEngine(state_dir=tmp_path / "state")
        run = engine.plan("Fix the bug", issue=42)
        assert run.issue == 42
        assert run.task_type == "bug_fix"

    def test_plan_with_pr(self, tmp_path):
        engine = ExecutionEngine(state_dir=tmp_path / "state")
        run = engine.plan("Review the changes", pr=18)
        assert run.pr == 18
        assert run.task_type == "review"

    def test_plan_economy_mode(self, tmp_path):
        engine = ExecutionEngine(state_dir=tmp_path / "state", economy=True)
        run = engine.plan("Add a feature")
        # Economy mode should select a cheaper model
        assert "haiku" in run.model

    def test_execute_dry_run(self, tmp_path):
        engine = ExecutionEngine(state_dir=tmp_path / "state")
        run = engine.plan("Add a login page")
        result = engine.execute(run, dry_run=True)
        assert result.status == "complete"
        assert result.dry_run is True
        assert result.ended_at is not None

    def test_execute_real_run(self, tmp_path):
        engine = ExecutionEngine(state_dir=tmp_path / "state")

        def mock_agent(agent, run):
            return {"agent": agent, "input_tokens": 50, "output_tokens": 30, "output": "done"}

        engine._run_agent = mock_agent  # type: ignore[assignment]

        run = engine.plan("Add a login page")
        result = engine.execute(run)
        assert result.status == "complete"
        assert result.dry_run is False
        assert result.token_usage["input"] > 0
        assert result.token_usage["output"] > 0

    def test_execute_records_run(self, tmp_path):
        state_dir = tmp_path / "state"
        engine = ExecutionEngine(state_dir=state_dir)

        def mock_agent(agent, run):
            return {"agent": agent, "input_tokens": 10, "output_tokens": 10, "output": "ok"}

        engine._run_agent = mock_agent  # type: ignore[assignment]

        run = engine.plan("Add a login page")
        engine.execute(run)
        assert (state_dir / "runs.jsonl").exists()

    def test_execute_budget_abort(self, tmp_path):
        config = EcoConfig(token_budget=1)  # Extremely low budget
        engine = ExecutionEngine(config=config, state_dir=tmp_path / "state")

        # Mock _run_agent to return tokens
        def mock_agent(agent, run):
            return {"agent": agent, "input_tokens": 100, "output_tokens": 100}

        engine._run_agent = mock_agent  # type: ignore[assignment]

        run = engine.plan("Add a login page")
        # First agent returns 200 tokens, which exceeds budget of 1
        # But the budget check happens BEFORE each agent call, so
        # the first agent runs (0 < 1) and the second agent is blocked
        result = engine.execute(run)
        assert result.status == "aborted"
        assert "Token budget exceeded" in (result.error or "")

    def test_execute_agent_failure(self, tmp_path):
        engine = ExecutionEngine(state_dir=tmp_path / "state")

        def mock_agent(agent, run):
            return {"agent": agent, "input_tokens": 0, "output_tokens": 0, "error": "Agent crashed"}

        engine._run_agent = mock_agent  # type: ignore[assignment]

        run = engine.plan("Add a login page")
        result = engine.execute(run)
        assert result.status == "failed"
        assert result.error == "Agent crashed"

    def test_get_active_runs_empty(self, tmp_path):
        engine = ExecutionEngine(state_dir=tmp_path / "state")
        assert engine.get_active_runs() == []

    def test_get_active_runs_filters(self, tmp_path):
        state_dir = tmp_path / "state"
        engine = ExecutionEngine(state_dir=state_dir)

        def mock_agent(agent, run):
            return {"agent": agent, "input_tokens": 10, "output_tokens": 10, "output": "ok"}

        engine._run_agent = mock_agent  # type: ignore[assignment]

        # Execute two runs: one complete, one we'll leave as running
        run1 = engine.plan("Task 1")
        engine.execute(run1)  # Completes

        run2 = engine.plan("Task 2")
        run2.status = "running"
        engine._record_run(run2)

        active = engine.get_active_runs()
        assert len(active) == 1
        assert active[0].run_id == run2.run_id

    def test_get_all_runs(self, tmp_path):
        state_dir = tmp_path / "state"
        engine = ExecutionEngine(state_dir=state_dir)

        def mock_agent(agent, run):
            return {"agent": agent, "input_tokens": 10, "output_tokens": 10, "output": "ok"}

        engine._run_agent = mock_agent  # type: ignore[assignment]

        run1 = engine.plan("Task 1")
        engine.execute(run1)
        run2 = engine.plan("Task 2")
        engine.execute(run2)

        all_runs = engine.get_all_runs()
        assert len(all_runs) == 2

    def test_estimate_cost(self, tmp_path):
        engine = ExecutionEngine(state_dir=tmp_path / "state")
        estimate = engine.estimate_cost("Add a login page")
        assert "estimated_cost_usd" in estimate
        assert "estimated_input_tokens" in estimate
        assert "estimated_output_tokens" in estimate
        assert estimate["task_type"] == "feature"
        assert estimate["estimated_cost_usd"] > 0
        assert estimate["token_budget"] == 50_000

    def test_estimate_cost_with_issue(self, tmp_path):
        engine = ExecutionEngine(state_dir=tmp_path / "state")
        estimate = engine.estimate_cost("Fix the bug", issue=42)
        assert estimate["task_type"] == "bug_fix"

    def test_read_all_runs_deduplicates(self, tmp_path):
        state_dir = tmp_path / "state"
        engine = ExecutionEngine(state_dir=state_dir)

        run = engine.plan("Task 1")
        engine._record_run(run)  # Record initial state
        run.status = "running"
        engine._record_run(run)  # Record updated state

        all_runs = engine._read_all_runs()
        assert len(all_runs) == 1
        assert all_runs[0].status == "running"

    def test_model_override_resolves_shorthand(self, tmp_path):
        engine = ExecutionEngine(
            state_dir=tmp_path / "state",
            model_override="opus",
        )
        assert engine.model_override == MODEL_SHORTHANDS["opus"]

    def test_model_override_passes_through_full_id(self, tmp_path):
        engine = ExecutionEngine(
            state_dir=tmp_path / "state",
            model_override="claude-opus-4-20250514",
        )
        assert engine.model_override == "claude-opus-4-20250514"

    def test_model_override_used_in_run_agent(self, tmp_path):
        engine = ExecutionEngine(
            state_dir=tmp_path / "state",
            model_override="opus",
        )

        captured_model = {}

        def mock_cli(agent, model, system_prompt, user_message, allowed_tools=None):
            captured_model["model"] = model
            return {"agent": agent, "input_tokens": 10, "output_tokens": 5, "output": "ok"}

        engine._run_agent_cli = mock_cli  # type: ignore[assignment]

        run = engine.plan("Add a feature")
        # Remove SDK path by ensuring no API key
        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            engine._run_agent(run.agent_sequence[0], run)

        assert captured_model["model"] == MODEL_SHORTHANDS["opus"]

    def test_allowed_tools_passed_to_cli(self, tmp_path):
        engine = ExecutionEngine(state_dir=tmp_path / "state")

        captured_tools = {}

        def mock_cli(agent, model, system_prompt, user_message, allowed_tools=None):
            captured_tools["tools"] = allowed_tools
            return {"agent": agent, "input_tokens": 10, "output_tokens": 5, "output": "ok"}

        engine._run_agent_cli = mock_cli  # type: ignore[assignment]

        run = engine.plan("Add a feature")
        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            engine._run_agent("backend-engineer", run)

        assert "Bash" in captured_tools["tools"]
        assert "Write" in captured_tools["tools"]

    def test_verbose_flag_stored(self, tmp_path):
        engine = ExecutionEngine(
            state_dir=tmp_path / "state",
            verbose=True,
        )
        assert engine.verbose is True

    def test_execute_prints_progress(self, tmp_path, capsys):
        engine = ExecutionEngine(state_dir=tmp_path / "state")

        def mock_agent(agent, run):
            return {"agent": agent, "input_tokens": 10, "output_tokens": 5, "output": "ok"}

        engine._run_agent = mock_agent  # type: ignore[assignment]

        run = engine.plan("Add a login page")
        engine.execute(run)

        captured = capsys.readouterr()
        assert "Running" in captured.err
        assert "[1/" in captured.err

    def test_env_var_overrides_model_table(self, tmp_path):
        """Per-agent env var (e.g. BACKEND_ENGINEER_MODEL=opus) overrides MODEL_TABLE."""
        engine = ExecutionEngine(state_dir=tmp_path / "state")

        captured = {}

        def mock_cli(agent, model, system_prompt, user_message, allowed_tools=None):
            captured["model"] = model
            return {"agent": agent, "input_tokens": 10, "output_tokens": 5, "output": "ok"}

        engine._run_agent_cli = mock_cli  # type: ignore[assignment]

        run = engine.plan("Add a feature")
        with patch.dict("os.environ", {"BACKEND_ENGINEER_MODEL": "opus"}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            engine._run_agent("backend-engineer", run)

        assert captured["model"] == MODEL_SHORTHANDS["opus"]

    def test_env_var_with_economy_demotes(self, tmp_path):
        """Economy mode demotes env-var model (opus→sonnet)."""
        engine = ExecutionEngine(state_dir=tmp_path / "state", economy=True)

        captured = {}

        def mock_cli(agent, model, system_prompt, user_message, allowed_tools=None):
            captured["model"] = model
            return {"agent": agent, "input_tokens": 10, "output_tokens": 5, "output": "ok"}

        engine._run_agent_cli = mock_cli  # type: ignore[assignment]

        run = engine.plan("Add a feature")
        with patch.dict("os.environ", {"BACKEND_ENGINEER_MODEL": "opus"}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            engine._run_agent("backend-engineer", run)

        # opus should be demoted to sonnet in economy mode
        assert captured["model"] == MODEL_SHORTHANDS["sonnet"]

    def test_model_flag_beats_env_var(self, tmp_path):
        """--model flag overrides per-agent env var."""
        engine = ExecutionEngine(
            state_dir=tmp_path / "state",
            model_override="haiku",
        )

        captured = {}

        def mock_cli(agent, model, system_prompt, user_message, allowed_tools=None):
            captured["model"] = model
            return {"agent": agent, "input_tokens": 10, "output_tokens": 5, "output": "ok"}

        engine._run_agent_cli = mock_cli  # type: ignore[assignment]

        run = engine.plan("Add a feature")
        with patch.dict("os.environ", {"BACKEND_ENGINEER_MODEL": "opus"}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            engine._run_agent("backend-engineer", run)

        # --model flag wins over env var
        assert captured["model"] == MODEL_SHORTHANDS["haiku"]

    def test_model_flag_not_demoted_by_economy(self, tmp_path):
        """--model flag is absolute — economy mode does not demote it."""
        engine = ExecutionEngine(
            state_dir=tmp_path / "state",
            model_override="opus",
            economy=True,
        )

        captured = {}

        def mock_cli(agent, model, system_prompt, user_message, allowed_tools=None):
            captured["model"] = model
            return {"agent": agent, "input_tokens": 10, "output_tokens": 5, "output": "ok"}

        engine._run_agent_cli = mock_cli  # type: ignore[assignment]

        run = engine.plan("Add a feature")
        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            engine._run_agent("backend-engineer", run)

        # --model flag is absolute, no demotion
        assert captured["model"] == MODEL_SHORTHANDS["opus"]

    def test_env_var_full_model_id(self, tmp_path):
        """Env var can specify a full model ID instead of a shorthand."""
        engine = ExecutionEngine(state_dir=tmp_path / "state")

        captured = {}

        def mock_cli(agent, model, system_prompt, user_message, allowed_tools=None):
            captured["model"] = model
            return {"agent": agent, "input_tokens": 10, "output_tokens": 5, "output": "ok"}

        engine._run_agent_cli = mock_cli  # type: ignore[assignment]

        run = engine.plan("Add a feature")
        full_id = "claude-opus-4-20250514"
        with patch.dict("os.environ", {"ARCHITECT_MODEL": full_id}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            engine._run_agent("architect", run)

        assert captured["model"] == full_id

    def test_no_env_var_falls_through_to_model_table(self, tmp_path):
        """Without env var or --model, falls back to MODEL_TABLE via select_model."""
        engine = ExecutionEngine(state_dir=tmp_path / "state")

        captured = {}

        def mock_cli(agent, model, system_prompt, user_message, allowed_tools=None):
            captured["model"] = model
            return {"agent": agent, "input_tokens": 10, "output_tokens": 5, "output": "ok"}

        engine._run_agent_cli = mock_cli  # type: ignore[assignment]

        run = engine.plan("Add a feature")
        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("BACKEND_ENGINEER_MODEL", None)
            engine._run_agent("backend-engineer", run)

        # Should use the MODEL_TABLE default (sonnet for backend)
        assert captured["model"] == "claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# DeployEngine tests
# ---------------------------------------------------------------------------


class TestDeployEngine:
    def test_deploy_once_requires_issue_or_pr(self):
        deploy = DeployEngine()
        result = deploy.deploy_once()
        assert "error" in result
        assert result["actions"] == []

    @patch("orchestration.sync_engine.CommentFetcher")
    @patch("orchestration.sync_engine.IntentClassifier")
    @patch("orchestration.sync_engine.ActionExecutor")
    @patch("orchestration.sync_engine.SyncHistory")
    def test_deploy_once_with_issue(
        self, mock_history_cls, mock_executor_cls, mock_classifier_cls, mock_fetcher_cls,
    ):
        mock_fetcher = mock_fetcher_cls.return_value
        mock_fetcher.fetch_issue_comments.return_value = []

        deploy = DeployEngine()
        result = deploy.deploy_once(issue=42)
        assert result["total_comments"] == 0
        assert result["new_comments"] == 0
        mock_fetcher.fetch_issue_comments.assert_called_once_with(42)

    @patch("orchestration.sync_engine.CommentFetcher")
    @patch("orchestration.sync_engine.IntentClassifier")
    @patch("orchestration.sync_engine.ActionExecutor")
    @patch("orchestration.sync_engine.SyncHistory")
    def test_deploy_once_with_pr(
        self, mock_history_cls, mock_executor_cls, mock_classifier_cls, mock_fetcher_cls,
    ):
        mock_fetcher = mock_fetcher_cls.return_value
        mock_fetcher.fetch_pr_comments.return_value = []
        mock_fetcher.fetch_pr_review_threads.return_value = []

        deploy = DeployEngine()
        result = deploy.deploy_once(pr=18)
        assert result["total_comments"] == 0
        mock_fetcher.fetch_pr_comments.assert_called_once_with(18)
        mock_fetcher.fetch_pr_review_threads.assert_called_once_with(18)

    @patch("orchestration.execution.time")
    @patch.object(DeployEngine, "deploy_once")
    def test_watch_respects_max_iterations(self, mock_deploy, mock_time, capsys):
        mock_deploy.return_value = {
            "total_comments": 0,
            "new_comments": 0,
            "actions": [],
        }
        mock_time.sleep = MagicMock()

        deploy = DeployEngine()
        deploy.watch(issue=42, max_iterations=2)

        assert mock_deploy.call_count == 2
        assert mock_time.sleep.call_count == 1  # sleep between iterations, not after last
