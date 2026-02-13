"""Task router module for classifying and routing tasks to agents.

This module implements deterministic pattern matching for task classification (P6).
The router does one thing well: map task descriptions to agent sequences (P8).
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskType(Enum):
    """Enumeration of supported task types."""

    FEATURE = "feature"
    BUG_FIX = "bug_fix"
    REVIEW = "review"
    DOCS = "docs"
    INFRASTRUCTURE = "infrastructure"
    DESIGN = "design"
    ARCHITECTURE = "architecture"
    BACKEND = "backend"
    FRONTEND = "frontend"
    ML = "ml"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    PROJECT_MANAGEMENT = "project_mgmt"
    # Unity Space Sim project-specific types
    UNITY_ASSET_DESIGN = "unity_asset_design"
    BLENDER_SCRIPTING = "blender_scripting"
    UNITY_SCRIPTING = "unity_scripting"
    GAMEDEV_INTEGRATION = "gamedev_integration"
    UNKNOWN = "unknown"


@dataclass
class RoutingDecision:
    """Represents a routing decision for a task.

    Attributes:
        task_type: The classified type of the task.
        agent_sequence: Ordered list of agents to execute the task.
        priority: Priority level (high, medium, low).
        context: Extracted context from the task description.
    """

    task_type: TaskType
    agent_sequence: list[str]
    priority: str
    context: dict[str, Any] = field(default_factory=dict)


# Deterministic routing table mapping TaskType to agent sequence (P5)
# TDD enforcement: features/bugs get performance-engineer first for tests
ROUTING_TABLE: dict[TaskType, list[str]] = {
    # Features get architect review, then orchestrator routes to specialized engineers
    TaskType.FEATURE: ["architect", "performance-engineer", "orchestrator"],
    # Bug fixes: performance engineer writes regression test, orchestrator picks engineer
    TaskType.BUG_FIX: ["performance-engineer", "orchestrator", "reviewer"],
    # Infrastructure: architect designs, infrastructure engineer implements
    TaskType.INFRASTRUCTURE: ["architect", "infrastructure-engineer", "reviewer"],
    # Design tasks go to designer
    TaskType.DESIGN: ["designer"],
    # Architecture tasks go to architect
    TaskType.ARCHITECTURE: ["architect"],
    # Backend-specific tasks
    TaskType.BACKEND: ["performance-engineer", "backend-engineer", "reviewer"],
    # Frontend-specific tasks
    TaskType.FRONTEND: ["performance-engineer", "frontend-engineer", "reviewer"],
    # ML tasks
    TaskType.ML: ["ml-engineer", "performance-engineer", "reviewer"],
    # Integration tasks
    TaskType.INTEGRATION: ["integration-engineer", "reviewer"],
    # Performance optimization
    TaskType.PERFORMANCE: ["performance-engineer", "orchestrator"],
    # Project management
    TaskType.PROJECT_MANAGEMENT: ["project-manager"],
    # Review tasks
    TaskType.REVIEW: ["reviewer"],
    # Docs (architect ensures API docs are complete)
    TaskType.DOCS: ["architect"],
    # Unity Space Sim project-specific agents
    TaskType.UNITY_ASSET_DESIGN: ["unity-asset-designer"],
    TaskType.BLENDER_SCRIPTING: ["blender-engineer", "gamedev-integration-engineer"],
    TaskType.UNITY_SCRIPTING: ["unity-engineer", "gamedev-integration-engineer"],
    TaskType.GAMEDEV_INTEGRATION: ["gamedev-integration-engineer"],
    # Unknown routes to orchestrator
    TaskType.UNKNOWN: ["orchestrator"],
}

# Priority mapping by task type
PRIORITY_TABLE: dict[TaskType, str] = {
    TaskType.FEATURE: "medium",
    TaskType.BUG_FIX: "high",
    TaskType.REVIEW: "medium",
    TaskType.DOCS: "low",
    TaskType.INFRASTRUCTURE: "medium",
    TaskType.DESIGN: "medium",
    TaskType.ARCHITECTURE: "high",  # Architectural decisions are high priority
    TaskType.BACKEND: "medium",
    TaskType.FRONTEND: "medium",
    TaskType.ML: "medium",
    TaskType.INTEGRATION: "high",  # Integration failures block releases
    TaskType.PERFORMANCE: "medium",
    TaskType.PROJECT_MANAGEMENT: "low",
    # Unity Space Sim project-specific priorities
    TaskType.UNITY_ASSET_DESIGN: "medium",
    TaskType.BLENDER_SCRIPTING: "medium",
    TaskType.UNITY_SCRIPTING: "medium",
    TaskType.GAMEDEV_INTEGRATION: "high",  # Pipeline validation is critical
    TaskType.UNKNOWN: "low",
}

# Classification patterns - ordered by specificity (most specific first)
# Pattern matching handles known task types (P6: Code Before Prompts)
CLASSIFICATION_PATTERNS: list[tuple[TaskType, re.Pattern]] = [
    # Architecture and documentation patterns (MUST come first, before project-specific)
    # These override project-specific routing when the task is clearly about architecture/docs
    (TaskType.ARCHITECTURE, re.compile(r"\barchitecture\b", re.IGNORECASE)),
    (TaskType.ARCHITECTURE, re.compile(r"\bsystem\s*design\b", re.IGNORECASE)),
    (TaskType.ARCHITECTURE, re.compile(r"\bapi\s*spec\b", re.IGNORECASE)),
    (TaskType.ARCHITECTURE, re.compile(r"\bfoundation\b.*\bdocumentation\b", re.IGNORECASE)),
    (TaskType.ARCHITECTURE, re.compile(r"\bproject\s+foundation\b", re.IGNORECASE)),
    (TaskType.DOCS, re.compile(r"\bwrite.*documentation\b", re.IGNORECASE)),
    (TaskType.DOCS, re.compile(r"\bcreate.*documentation\b", re.IGNORECASE)),
    (TaskType.DOCS, re.compile(r"\barchitectural\s+documentation\b", re.IGNORECASE)),
    # Unity Space Sim project-specific patterns (most specific, checked after architecture/docs)
    # Asset design patterns (most specific - must come before general Unity/Blender)
    (TaskType.UNITY_ASSET_DESIGN, re.compile(r"\bship\s+design\b", re.IGNORECASE)),
    (TaskType.UNITY_ASSET_DESIGN, re.compile(r"\basset\s+design\b", re.IGNORECASE)),
    (TaskType.UNITY_ASSET_DESIGN, re.compile(r"\b3d\s+design\b", re.IGNORECASE)),
    (TaskType.UNITY_ASSET_DESIGN, re.compile(r"\bdesign\s+a\s+.*\s+asset\b", re.IGNORECASE)),
    (TaskType.UNITY_ASSET_DESIGN, re.compile(r"\bnasa.inspired\b", re.IGNORECASE)),
    # Integration/pipeline patterns (before Blender/Unity keywords)
    (TaskType.GAMEDEV_INTEGRATION, re.compile(r"\bgamedev\s+integration\b", re.IGNORECASE)),
    (TaskType.GAMEDEV_INTEGRATION, re.compile(r"\basset\s+pipeline\b", re.IGNORECASE)),
    (TaskType.GAMEDEV_INTEGRATION, re.compile(r"\bblender\s+to\s+unity\b", re.IGNORECASE)),
    (TaskType.GAMEDEV_INTEGRATION, re.compile(r"\bend.to.end.*pipeline\b", re.IGNORECASE)),
    (TaskType.GAMEDEV_INTEGRATION, re.compile(r"\blod\s+validation\b", re.IGNORECASE)),
    (TaskType.GAMEDEV_INTEGRATION, re.compile(r"\bpoly\s+count\b", re.IGNORECASE)),
    # Blender scripting patterns
    (TaskType.BLENDER_SCRIPTING, re.compile(r"\bblender\s+python\b", re.IGNORECASE)),
    (TaskType.BLENDER_SCRIPTING, re.compile(r"\bbpy\b", re.IGNORECASE)),
    (TaskType.BLENDER_SCRIPTING, re.compile(r"\bblender\s+script\b", re.IGNORECASE)),
    (TaskType.BLENDER_SCRIPTING, re.compile(r"\bprocedural\s+modeling\b", re.IGNORECASE)),
    (TaskType.BLENDER_SCRIPTING, re.compile(r"\bfbx\s+export\b", re.IGNORECASE)),
    (TaskType.BLENDER_SCRIPTING, re.compile(r"\bblender\b", re.IGNORECASE)),
    # Unity scripting patterns
    (TaskType.UNITY_SCRIPTING, re.compile(r"\bunity\s+c#\b", re.IGNORECASE)),
    (TaskType.UNITY_SCRIPTING, re.compile(r"\bunity\s+script\b", re.IGNORECASE)),
    (TaskType.UNITY_SCRIPTING, re.compile(r"\bmonobehaviour\b", re.IGNORECASE)),
    (TaskType.UNITY_SCRIPTING, re.compile(r"\bscriptableobject\b", re.IGNORECASE)),
    (TaskType.UNITY_SCRIPTING, re.compile(r"\bunity\s+component\b", re.IGNORECASE)),
    (TaskType.UNITY_SCRIPTING, re.compile(r"\bunity\b", re.IGNORECASE)),
    # Design patterns
    (TaskType.DESIGN, re.compile(r"\bdesign\b", re.IGNORECASE)),
    (TaskType.DESIGN, re.compile(r"\bui\b", re.IGNORECASE)),
    (TaskType.DESIGN, re.compile(r"\bux\b", re.IGNORECASE)),
    (TaskType.DESIGN, re.compile(r"\bwireframe\b", re.IGNORECASE)),
    # Backend patterns
    (TaskType.BACKEND, re.compile(r"\bapi\b", re.IGNORECASE)),
    (TaskType.BACKEND, re.compile(r"\bdatabase\b", re.IGNORECASE)),
    (TaskType.BACKEND, re.compile(r"\bbackend\b", re.IGNORECASE)),
    (TaskType.BACKEND, re.compile(r"\bgrpc\b", re.IGNORECASE)),
    # Frontend patterns
    (TaskType.FRONTEND, re.compile(r"\bfrontend\b", re.IGNORECASE)),
    (TaskType.FRONTEND, re.compile(r"\bcomponent\b", re.IGNORECASE)),
    (TaskType.FRONTEND, re.compile(r"\breact\b", re.IGNORECASE)),
    # ML patterns
    (TaskType.ML, re.compile(r"\bmachine\s*learning\b", re.IGNORECASE)),
    (TaskType.ML, re.compile(r"\bml\b", re.IGNORECASE)),
    (TaskType.ML, re.compile(r"\bllm\b", re.IGNORECASE)),
    (TaskType.ML, re.compile(r"\bmodel\b", re.IGNORECASE)),
    # Integration patterns
    (TaskType.INTEGRATION, re.compile(r"\bintegration\b", re.IGNORECASE)),
    (TaskType.INTEGRATION, re.compile(r"\bend.to.end\b", re.IGNORECASE)),
    (TaskType.INTEGRATION, re.compile(r"\be2e\b", re.IGNORECASE)),
    # Performance patterns
    (TaskType.PERFORMANCE, re.compile(r"\bperformance\b", re.IGNORECASE)),
    (TaskType.PERFORMANCE, re.compile(r"\boptimize\b", re.IGNORECASE)),
    (TaskType.PERFORMANCE, re.compile(r"\bprofile\b", re.IGNORECASE)),
    (TaskType.PERFORMANCE, re.compile(r"\bbenchmark\b", re.IGNORECASE)),
    # Project management patterns
    (TaskType.PROJECT_MANAGEMENT, re.compile(r"\bepic\b", re.IGNORECASE)),
    (TaskType.PROJECT_MANAGEMENT, re.compile(r"\bcost\s*estimate\b", re.IGNORECASE)),
    (TaskType.PROJECT_MANAGEMENT, re.compile(r"\bsync\b", re.IGNORECASE)),
    # Review patterns (check first to avoid "fix" in "prefix" matching bug_fix)
    (TaskType.REVIEW, re.compile(r"\breview\b", re.IGNORECASE)),
    (TaskType.REVIEW, re.compile(r"\bpr\b", re.IGNORECASE)),
    (TaskType.REVIEW, re.compile(r"\bpull\s*request\b", re.IGNORECASE)),
    (TaskType.REVIEW, re.compile(r"\bcode\s*review\b", re.IGNORECASE)),
    # Bug fix patterns
    (TaskType.BUG_FIX, re.compile(r"\bbug\b", re.IGNORECASE)),
    (TaskType.BUG_FIX, re.compile(r"\bfix\b", re.IGNORECASE)),
    (TaskType.BUG_FIX, re.compile(r"\bbroken\b", re.IGNORECASE)),
    (TaskType.BUG_FIX, re.compile(r"\berror\b", re.IGNORECASE)),
    (TaskType.BUG_FIX, re.compile(r"\bissue\b", re.IGNORECASE)),
    # Docs patterns (additional fallback patterns - more specific ones are at top)
    (TaskType.DOCS, re.compile(r"\bdocs?\b", re.IGNORECASE)),
    (TaskType.DOCS, re.compile(r"\breadme\b", re.IGNORECASE)),
    (TaskType.DOCS, re.compile(r"\bdocstrings?\b", re.IGNORECASE)),
    # Infrastructure patterns
    (TaskType.INFRASTRUCTURE, re.compile(r"\binfra\b", re.IGNORECASE)),
    (TaskType.INFRASTRUCTURE, re.compile(r"\binfrastructure\b", re.IGNORECASE)),
    (TaskType.INFRASTRUCTURE, re.compile(r"\bci\b", re.IGNORECASE)),
    (TaskType.INFRASTRUCTURE, re.compile(r"\bcd\b", re.IGNORECASE)),
    (TaskType.INFRASTRUCTURE, re.compile(r"\bdeploy\b", re.IGNORECASE)),
    (TaskType.INFRASTRUCTURE, re.compile(r"\bpipeline\b", re.IGNORECASE)),
    (TaskType.INFRASTRUCTURE, re.compile(r"\bdevops\b", re.IGNORECASE)),
    # Feature patterns (last because they are the most general)
    (TaskType.FEATURE, re.compile(r"\bfeature\b", re.IGNORECASE)),
    (TaskType.FEATURE, re.compile(r"\badd\b", re.IGNORECASE)),
    (TaskType.FEATURE, re.compile(r"\bcreate\b", re.IGNORECASE)),
    (TaskType.FEATURE, re.compile(r"\bimplement\b", re.IGNORECASE)),
]

# Pattern for extracting file paths from task descriptions
FILE_PATH_PATTERN = re.compile(r"[\w./\-]+\.(?:py|js|ts|json|yaml|yml|md|txt|sh|cs|fbx|blend)")

# Pattern for detecting Unity Space Sim project paths
UNITY_SPACE_SIM_PATH_PATTERN = re.compile(r"projects/unity-space-sim/")


class TaskRouter:
    """Routes tasks to appropriate agents based on classification.

    The router uses deterministic pattern matching (P6) to classify tasks
    and maps them to agent sequences via a static routing table (P5).
    """

    def classify(self, task_description: str) -> TaskType:
        """Classify a task description into a TaskType.

        Uses pattern matching (regex/keywords) for classification.
        This is deterministic code, not AI (P6: Code Before Prompts).

        Args:
            task_description: The task description to classify.

        Returns:
            The classified TaskType. Returns UNKNOWN for ambiguous input (P16).
        """
        if not task_description or not task_description.strip():
            return TaskType.UNKNOWN

        for task_type, pattern in CLASSIFICATION_PATTERNS:
            if pattern.search(task_description):
                return task_type

        # Permission to fail (P16): unknown is a valid classification
        return TaskType.UNKNOWN

    def route(self, task_description: str) -> RoutingDecision:
        """Route a task to the appropriate agent sequence.

        Args:
            task_description: The task description to route.

        Returns:
            A RoutingDecision containing task_type, agent_sequence,
            priority, and extracted context.
        """
        context = self._extract_context(task_description)
        task_type = self.classify(task_description)

        # Override task type based on file path context (monorepo routing)
        if context.get("project") == "unity-space-sim":
            task_type = self._detect_unity_space_sim_task_type(
                task_description, context, task_type
            )

        agent_sequence = ROUTING_TABLE[task_type].copy()
        priority = PRIORITY_TABLE[task_type]

        return RoutingDecision(
            task_type=task_type,
            agent_sequence=agent_sequence,
            priority=priority,
            context=context,
        )

    def _extract_context(self, task_description: str) -> dict[str, Any]:
        """Extract context (files, modules, project) from the task description.

        Args:
            task_description: The task description to extract context from.

        Returns:
            A dictionary containing extracted context like file paths and project.
        """
        context: dict[str, Any] = {}

        # Extract file paths
        files = FILE_PATH_PATTERN.findall(task_description)
        if files:
            context["files"] = files

        # Detect Unity Space Sim project context from file paths
        if UNITY_SPACE_SIM_PATH_PATTERN.search(task_description):
            context["project"] = "unity-space-sim"

        return context

    def _detect_unity_space_sim_task_type(
        self,
        task_description: str,
        context: dict[str, Any],
        fallback_type: TaskType,
    ) -> TaskType:
        """Detect specific Unity Space Sim task type based on file paths and keywords.

        Args:
            task_description: The task description.
            context: Extracted context (files, project).
            fallback_type: The default task type from classification.

        Returns:
            A Unity Space Sim specific TaskType if detected, otherwise fallback_type.
        """
        files = context.get("files", [])

        # Path-based routing for Unity Space Sim
        for file_path in files:
            if "projects/unity-space-sim/blender/" in file_path and file_path.endswith(".py"):
                return TaskType.BLENDER_SCRIPTING
            if "projects/unity-space-sim/unity/" in file_path and file_path.endswith(".cs"):
                return TaskType.UNITY_SCRIPTING

        # If already classified as Unity Space Sim type, keep it
        if fallback_type in (
            TaskType.UNITY_ASSET_DESIGN,
            TaskType.BLENDER_SCRIPTING,
            TaskType.UNITY_SCRIPTING,
            TaskType.GAMEDEV_INTEGRATION,
        ):
            return fallback_type

        # Default Unity Space Sim routing based on general classification
        # If no specific Unity type was detected but we're in the project, use fallback
        return fallback_type
