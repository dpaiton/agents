"""Task execution engine for the orchestration framework.

Coordinates task routing, agent execution, token tracking, and state
persistence. Provides the runtime for ``eco run``, ``eco deploy``, and
``eco status``.

Design Principles:
- P2 Foundational Algorithm: plan → execute → verify per task
- P5 Deterministic Infrastructure: routing and model selection are code
- P6 Code Before Prompts: orchestration logic is Python, not prompts
- P8 UNIX Philosophy: JSONL state, composable with grep/jq
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from orchestration.config import EcoConfig, load_config, select_model
from orchestration.cost import CostCalculator, UsageRecord, UsageStore
from orchestration.router import TaskRouter

logger = logging.getLogger(__name__)

# Map agent names to model selection keys in config.MODEL_TABLE
AGENT_MODEL_KEY: dict[str, str] = {
    "architect": "architecture",
    "performance-engineer": "performance-analysis",
    "orchestrator": "code-change",
    "reviewer": "review",
    "backend-engineer": "backend",
    "frontend-engineer": "frontend",
    "ml-engineer": "ml",
    "infrastructure-engineer": "infrastructure",
    "integration-engineer": "integration",
    "designer": "design",
    "project-manager": "project-management",
}

# Directories for agent definitions
_REPO_ROOT = Path(__file__).resolve().parent.parent
_GLOBAL_AGENTS_DIR = _REPO_ROOT / ".claude" / "agents"
_PROJECTS_DIR = _REPO_ROOT / "projects"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TaskRun:
    """A tracked task execution.

    Attributes:
        run_id: Unique identifier for this run.
        task: The original task description.
        task_type: Classified task type from the router.
        agent_sequence: Ordered list of agents to execute.
        status: Current status (pending, running, complete, failed, aborted).
        model: Selected model for this task.
        started_at: ISO 8601 timestamp when the run started.
        ended_at: ISO 8601 timestamp when the run ended.
        token_usage: Accumulated token counts.
        issue: Associated GitHub issue number.
        pr: Associated GitHub PR number.
        error: Error message if the run failed.
        dry_run: Whether this was a dry run (no real execution).
    """

    run_id: str
    task: str
    task_type: str
    agent_sequence: list[str]
    status: str
    model: str
    started_at: str
    ended_at: Optional[str] = None
    token_usage: dict[str, int] = field(
        default_factory=lambda: {"input": 0, "output": 0},
    )
    issue: Optional[int] = None
    pr: Optional[int] = None
    error: Optional[str] = None
    dry_run: bool = False


# ---------------------------------------------------------------------------
# Execution engine
# ---------------------------------------------------------------------------

class ExecutionEngine:
    """Manages task execution lifecycle.

    Responsibilities:
    - Plan: classify task, select model, build agent sequence
    - Execute: run agents in sequence, track tokens
    - Persist: write run state to JSONL
    - Budget: abort if token budget exceeded
    """

    STATE_DIR = ".eco-state"
    RUNS_FILE = "runs.jsonl"

    def __init__(
        self,
        config: EcoConfig | None = None,
        state_dir: str | Path | None = None,
        economy: bool = False,
    ) -> None:
        self.config = config or load_config()
        self.economy = economy
        self.state_dir = Path(state_dir or self.STATE_DIR)
        self.runs_path = self.state_dir / self.RUNS_FILE
        self._router = TaskRouter()

    def plan(
        self,
        task: str,
        issue: int | None = None,
        pr: int | None = None,
    ) -> TaskRun:
        """Create an execution plan for a task.

        Classifies the task, selects the model, and builds the agent
        sequence. Does not execute anything.

        Args:
            task: The task description.
            issue: Associated GitHub issue number.
            pr: Associated GitHub PR number.

        Returns:
            A TaskRun in "pending" status.
        """
        decision = self._router.route(task)
        model = select_model(
            _task_type_to_model_key(decision.task_type.value),
            config=self.config,
            economy=self.economy,
        )

        return TaskRun(
            run_id=uuid.uuid4().hex[:12],
            task=task,
            task_type=decision.task_type.value,
            agent_sequence=decision.agent_sequence,
            status="pending",
            model=model,
            started_at=_now_iso(),
            issue=issue,
            pr=pr,
        )

    def execute(self, run: TaskRun, dry_run: bool = False) -> TaskRun:
        """Execute a planned run.

        For each agent in the sequence, delegates to ``_run_agent()``.
        Tracks token usage and enforces the token budget.

        In dry-run mode, prints the plan but does not invoke agents.

        Args:
            run: A TaskRun from ``plan()``.
            dry_run: If True, show plan without executing.

        Returns:
            The updated TaskRun with final status.
        """
        run.dry_run = dry_run
        run.status = "running"
        self._record_run(run)

        if dry_run:
            run.status = "complete"
            run.ended_at = _now_iso()
            self._record_run(run)
            return run

        budget = self.config.token_budget
        total_tokens = 0

        for agent in run.agent_sequence:
            # Budget check
            if budget > 0 and total_tokens >= budget:
                run.status = "aborted"
                run.error = (
                    f"Token budget exceeded: {total_tokens} >= {budget}"
                )
                run.ended_at = _now_iso()
                self._record_run(run)
                return run

            result = self._run_agent(agent, run)
            input_tokens = result.get("input_tokens", 0)
            output_tokens = result.get("output_tokens", 0)
            run.token_usage["input"] += input_tokens
            run.token_usage["output"] += output_tokens
            total_tokens = run.token_usage["input"] + run.token_usage["output"]

            if result.get("error"):
                run.status = "failed"
                run.error = result["error"]
                run.ended_at = _now_iso()
                self._record_run(run)
                return run

        run.status = "complete"
        run.ended_at = _now_iso()
        self._record_run(run)

        # Log usage to cost tracker
        self._log_usage(run)

        return run

    def get_active_runs(self) -> list[TaskRun]:
        """List all runs with status 'running'."""
        return [r for r in self._read_all_runs() if r.status == "running"]

    def get_all_runs(self) -> list[TaskRun]:
        """List all recorded runs."""
        return self._read_all_runs()

    def estimate_cost(
        self,
        task: str,
        issue: int | None = None,
        pr: int | None = None,
    ) -> dict:
        """Estimate the token cost for a task without executing.

        Uses historical averages per task type when available,
        otherwise provides a rough estimate based on agent count.

        Args:
            task: The task description.
            issue: Associated GitHub issue number.
            pr: Associated GitHub PR number.

        Returns:
            A dict with estimated tokens and cost.
        """
        run = self.plan(task, issue=issue, pr=pr)
        avg = _estimate_tokens_for_task_type(run.task_type, len(run.agent_sequence))
        cost = CostCalculator.estimate_cost(
            run.model, avg["input_tokens"], avg["output_tokens"],
        )

        return {
            "task": task,
            "task_type": run.task_type,
            "model": run.model,
            "agent_sequence": run.agent_sequence,
            "estimated_input_tokens": avg["input_tokens"],
            "estimated_output_tokens": avg["output_tokens"],
            "estimated_cost_usd": cost,
            "token_budget": self.config.token_budget,
        }

    # --- internal helpers ---------------------------------------------------

    def _run_agent(self, agent: str, run: TaskRun) -> dict:
        """Run a single agent step via the Anthropic API.

        Loads the agent definition from ``.claude/agents/{agent}.md``,
        selects a model based on agent role, and calls the Anthropic
        Messages API.  Token usage is extracted from the API response.

        Args:
            agent: The agent name (e.g. "architect", "reviewer").
            run: The parent TaskRun for context.

        Returns:
            A dict with keys: agent, input_tokens, output_tokens,
            output (str), and optionally error (str).
        """
        try:
            import anthropic
        except ImportError:
            return {
                "agent": agent,
                "input_tokens": 0,
                "output_tokens": 0,
                "error": "anthropic SDK not installed — run: uv sync --group dev",
            }

        # Resolve the agent definition file (project-aware)
        system_prompt = _load_agent_definition(agent, run)

        # Select model for this agent's role
        model_key = AGENT_MODEL_KEY.get(agent, "code-change")
        model = select_model(model_key, config=self.config, economy=self.economy)

        # Build the user message with task context
        parts = [f"## Task\n{run.task}"]
        if run.issue:
            parts.append(f"GitHub Issue: #{run.issue}")
        if run.pr:
            parts.append(f"GitHub PR: #{run.pr}")
        parts.append(f"Task type: {run.task_type}")
        parts.append(f"Agent sequence: {' → '.join(run.agent_sequence)}")
        user_message = "\n\n".join(parts)

        # Call the Anthropic API
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return {
                "agent": agent,
                "input_tokens": 0,
                "output_tokens": 0,
                "error": "ANTHROPIC_API_KEY not set",
            }

        try:
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            output_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    output_text += block.text

            logger.info(
                "Agent %s completed: %d input, %d output tokens",
                agent,
                response.usage.input_tokens,
                response.usage.output_tokens,
            )

            return {
                "agent": agent,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "output": output_text,
            }
        except Exception as exc:
            return {
                "agent": agent,
                "input_tokens": 0,
                "output_tokens": 0,
                "error": f"Agent {agent} failed: {exc}",
            }

    def _record_run(self, run: TaskRun) -> None:
        """Append run state to the JSONL file."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with open(self.runs_path, "a") as f:
            f.write(json.dumps(asdict(run)) + "\n")

    def _read_all_runs(self) -> list[TaskRun]:
        """Read all runs from the JSONL file.

        Returns the most recent state for each run_id.
        """
        if not self.runs_path.exists():
            return []

        latest: dict[str, TaskRun] = {}
        with open(self.runs_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                latest[data["run_id"]] = TaskRun(**data)

        return list(latest.values())

    def _log_usage(self, run: TaskRun) -> None:
        """Log the run's token usage to the cost tracker."""
        if run.token_usage["input"] == 0 and run.token_usage["output"] == 0:
            return

        record = UsageRecord(
            timestamp=run.ended_at or _now_iso(),
            model=run.model,
            input_tokens=run.token_usage["input"],
            output_tokens=run.token_usage["output"],
            command="run",
            pr=run.pr,
            issue=run.issue,
            session_id=run.run_id,
        )
        store = UsageStore()
        store.append(record)


# ---------------------------------------------------------------------------
# Deploy engine (watch mode)
# ---------------------------------------------------------------------------

class DeployEngine:
    """Manages long-running agent deployment on issues/PRs.

    ``eco deploy --issue 42 --watch`` polls for new comments at a
    configurable interval and processes them via the sync engine.
    """

    def __init__(
        self,
        config: EcoConfig | None = None,
        economy: bool = False,
    ) -> None:
        self.config = config or load_config()
        self.economy = economy

    def deploy_once(
        self,
        issue: int | None = None,
        pr: int | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Read latest comments and act once.

        Args:
            issue: GitHub issue number.
            pr: GitHub PR number.
            dry_run: If True, show plan without executing.

        Returns:
            A summary dict.
        """
        from orchestration.sync_engine import (
            ActionExecutor,
            CommentFetcher,
            IntentClassifier,
            SyncHistory,
        )

        fetcher = CommentFetcher()
        classifier = IntentClassifier()
        executor = ActionExecutor()
        history = SyncHistory()

        if pr:
            comments = fetcher.fetch_pr_comments(pr)
            comments.extend(fetcher.fetch_pr_review_threads(pr))
        elif issue:
            comments = fetcher.fetch_issue_comments(issue)
        else:
            return {"error": "Must specify --issue or --pr", "actions": []}

        new_comments = [c for c in comments if not history.is_processed(c.id)]
        results = []
        for comment in new_comments:
            classified = classifier.classify(comment)
            result = executor.execute(classified, dry_run=dry_run)
            results.append(asdict(result))
            if not dry_run:
                history.record(result)

        return {
            "total_comments": len(comments),
            "new_comments": len(new_comments),
            "actions": results,
        }

    def watch(
        self,
        issue: int | None = None,
        pr: int | None = None,
        dry_run: bool = False,
        max_iterations: int = 0,
    ) -> None:
        """Poll for new comments in a loop.

        Args:
            issue: GitHub issue number.
            pr: GitHub PR number.
            dry_run: If True, show plan without executing.
            max_iterations: Max poll cycles (0 = infinite).
        """
        interval = self.config.poll_interval
        target = f"issue #{issue}" if issue else f"PR #{pr}"
        print(f"Watching {target} (poll every {interval}s, Ctrl+C to stop)")

        iteration = 0
        while True:
            iteration += 1
            result = self.deploy_once(issue=issue, pr=pr, dry_run=dry_run)

            new = result["new_comments"]
            if new > 0:
                success = sum(1 for a in result["actions"] if a.get("success"))
                print(f"  [{_now_iso()}] Processed {success}/{new} comment(s)")
            else:
                print(f"  [{_now_iso()}] No new comments")

            if max_iterations > 0 and iteration >= max_iterations:
                break

            time.sleep(interval)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_project(run: TaskRun | None) -> str | None:
    """Detect which project this task belongs to.

    Detection strategy (in order):
    1. Check for project labels on the associated GitHub issue
    2. Detect project keywords in the task description
    3. Scan available project directories and match against task

    Args:
        run: The TaskRun with context (task, issue, pr).

    Returns:
        Project name (e.g. "unity-space-sim") or None if not detected.
    """
    if not run:
        return None

    # Strategy 1: Check GitHub issue labels
    if run.issue:
        try:
            import subprocess
            result = subprocess.run(
                ["gh", "issue", "view", str(run.issue), "--json", "labels", "--jq", ".labels[].name"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                labels = result.stdout.strip().split("\n")
                # Check if any label matches a project directory
                if _PROJECTS_DIR.exists():
                    for project_dir in _PROJECTS_DIR.iterdir():
                        if project_dir.is_dir() and project_dir.name in labels:
                            logger.info("Detected project from issue label: %s", project_dir.name)
                            return project_dir.name
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug("Could not fetch issue labels: %s", e)

    # Strategy 2: Check for project keywords in task description
    task_lower = run.task.lower()
    if _PROJECTS_DIR.exists():
        for project_dir in _PROJECTS_DIR.iterdir():
            if project_dir.is_dir():
                # Match against project name (with underscores or hyphens)
                project_name = project_dir.name
                keywords = [
                    project_name,
                    project_name.replace("-", " "),
                    project_name.replace("_", " "),
                ]
                if any(keyword.lower() in task_lower for keyword in keywords):
                    logger.info("Detected project from task keywords: %s", project_name)
                    return project_name

    return None


def _find_agent_file(agent: str, project: str | None = None) -> Path | None:
    """Find the agent definition file, checking project-specific directories first.

    Search order:
    1. projects/{project}/.claude/agents/{agent}.md (if project specified)
    2. .claude/agents/{agent}.md (global fallback)

    Args:
        agent: Agent name (e.g. "architect", "unity-asset-designer").
        project: Optional project name (e.g. "unity-space-sim").

    Returns:
        Path to the agent definition file, or None if not found.
    """
    # Check project-specific agent first
    if project:
        project_agent_file = _PROJECTS_DIR / project / ".claude" / "agents" / f"{agent}.md"
        if project_agent_file.is_file():
            logger.info("Using project-specific agent: %s", project_agent_file)
            return project_agent_file

    # Fall back to global agent
    global_agent_file = _GLOBAL_AGENTS_DIR / f"{agent}.md"
    if global_agent_file.is_file():
        logger.info("Using global agent: %s", global_agent_file)
        return global_agent_file

    return None


def _load_agent_definition(agent: str, run: TaskRun | None = None) -> str:
    """Load the agent definition markdown file as a system prompt.

    Checks project-specific directories first, then falls back to global.

    Args:
        agent: Agent name (e.g. "architect", "unity-asset-designer").
        run: Optional TaskRun for project detection context.

    Returns:
        The system prompt string.
    """
    project = _detect_project(run)
    agent_file = _find_agent_file(agent, project)

    if agent_file:
        return agent_file.read_text()

    # Fall back to generic prompt
    logger.warning(
        "Agent definition not found for %s (project: %s). Using generic prompt.",
        agent,
        project or "none",
    )
    return f"You are a {agent} agent. Complete the assigned task thoroughly."


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _task_type_to_model_key(task_type: str) -> str:
    """Map a TaskType value to a model table key.

    The router produces values like "feature", "bug_fix", etc.
    The model table uses keys like "code-change", "review", etc.
    """
    mapping = {
        "feature": "code-change",
        "bug_fix": "code-change",
        "review": "review",
        "docs": "issue-body-edit",
        "infrastructure": "code-change",
        "unknown": "code-change",
    }
    return mapping.get(task_type, "code-change")


# Rough token estimates per task type (for cost estimation)
_TOKEN_ESTIMATES: dict[str, dict[str, int]] = {
    "feature": {"input_per_agent": 2000, "output_per_agent": 1500},
    "bug_fix": {"input_per_agent": 1500, "output_per_agent": 1000},
    "review": {"input_per_agent": 3000, "output_per_agent": 2000},
    "docs": {"input_per_agent": 1000, "output_per_agent": 800},
    "infrastructure": {"input_per_agent": 1500, "output_per_agent": 1000},
    "unknown": {"input_per_agent": 2000, "output_per_agent": 1500},
}


def _estimate_tokens_for_task_type(
    task_type: str,
    agent_count: int,
) -> dict[str, int]:
    """Estimate total tokens for a task based on type and agent count."""
    estimates = _TOKEN_ESTIMATES.get(task_type, _TOKEN_ESTIMATES["unknown"])
    return {
        "input_tokens": estimates["input_per_agent"] * agent_count,
        "output_tokens": estimates["output_per_agent"] * agent_count,
    }
