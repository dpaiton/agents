"""Prompt templates for judge, router, and reviewer agents.

This module provides deterministic string templates for LLM prompts.
All prompts follow the design principles:
- P3: Clear thinking first (reasoning before scores)
- P5: Deterministic infrastructure (fixed templates with variable slots)
- P11: Goal -> Code -> CLI -> Prompts -> Agents hierarchy
- P16: Permission to fail (explicit uncertainty allowance)
"""

from orchestration.prompts.judge_prompts import (
    bias_checklist_prompt,
    pairwise_eval_prompt,
    reference_eval_prompt,
)
from orchestration.prompts.router_prompt import (
    classify_task_prompt,
    decompose_task_prompt,
)
from orchestration.prompts.review_prompts import (
    review_pr_prompt,
    scrutinize_test_changes_prompt,
)

__all__ = [
    "reference_eval_prompt",
    "pairwise_eval_prompt",
    "bias_checklist_prompt",
    "classify_task_prompt",
    "decompose_task_prompt",
    "review_pr_prompt",
    "scrutinize_test_changes_prompt",
]
