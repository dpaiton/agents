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
# TDD enforcement: feature/bug -> [test-writer, engineer, reviewer]
ROUTING_TABLE: dict[TaskType, list[str]] = {
    TaskType.FEATURE: ["test-writer", "engineer", "reviewer"],
    TaskType.BUG_FIX: ["test-writer", "engineer", "reviewer"],
    TaskType.REVIEW: ["reviewer"],
    TaskType.DOCS: ["engineer"],
    TaskType.INFRASTRUCTURE: ["engineer"],
    TaskType.UNKNOWN: ["orchestrator"],
}

# Priority mapping by task type
PRIORITY_TABLE: dict[TaskType, str] = {
    TaskType.FEATURE: "medium",
    TaskType.BUG_FIX: "high",
    TaskType.REVIEW: "medium",
    TaskType.DOCS: "low",
    TaskType.INFRASTRUCTURE: "medium",
    TaskType.UNKNOWN: "low",
}

# Classification patterns - ordered by specificity (most specific first)
# Pattern matching handles known task types (P6: Code Before Prompts)
CLASSIFICATION_PATTERNS: list[tuple[TaskType, re.Pattern]] = [
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
    # Docs patterns
    (TaskType.DOCS, re.compile(r"\bdocs?\b", re.IGNORECASE)),
    (TaskType.DOCS, re.compile(r"\bdocumentation\b", re.IGNORECASE)),
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
FILE_PATH_PATTERN = re.compile(r"[\w./\-]+\.(?:py|js|ts|json|yaml|yml|md|txt|sh)")


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
        task_type = self.classify(task_description)
        agent_sequence = ROUTING_TABLE[task_type].copy()
        priority = PRIORITY_TABLE[task_type]
        context = self._extract_context(task_description)

        return RoutingDecision(
            task_type=task_type,
            agent_sequence=agent_sequence,
            priority=priority,
            context=context,
        )

    def _extract_context(self, task_description: str) -> dict[str, Any]:
        """Extract context (files, modules) from the task description.

        Args:
            task_description: The task description to extract context from.

        Returns:
            A dictionary containing extracted context like file paths.
        """
        context: dict[str, Any] = {}

        # Extract file paths
        files = FILE_PATH_PATTERN.findall(task_description)
        if files:
            context["files"] = files

        return context
