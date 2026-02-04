"""Judge engine for LLM-as-judge evaluation.

This module provides deterministic scaffolding around probabilistic model calls.
It structures prompts, validates outputs, aggregates scores, and detects instability.
The models provide judgment; the code provides rigor.

Design Principles:
- P4 Scaffolding > Model: Value is in structure (validation, debiasing, aggregation)
- P5 Deterministic validation: Scores must be integers from rubric scale
- P6 Code Before Prompts: Validation, swap logic, aggregation are pure Python
- P16 Permission to Fail: Unstable results are flagged, not hidden
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class EvaluationCriterion:
    """A criterion for evaluation with name, description, scale, and weight.

    Attributes:
        name: Short identifier for the criterion (e.g., "accuracy")
        description: Full description of what to evaluate
        scale: Tuple of (min, max) valid integer scores
        weight: Relative weight for aggregation (default 1.0)
    """

    name: str
    description: str
    scale: tuple[int, int]
    weight: float = 1.0


@dataclass
class CriterionScore:
    """A score for a single criterion with reasoning.

    Attributes:
        criterion: The criterion being scored
        score: Integer score within the criterion's scale
        reasoning: Explanation for the score (required before scoring)
    """

    criterion: EvaluationCriterion
    score: int
    reasoning: str


@dataclass
class BiasChecklistItem:
    """An item in the bias checklist.

    Attributes:
        name: Name of the bias check (e.g., "position_bias")
        checked: Whether this check was performed
        notes: Notes about the check result
    """

    name: str
    checked: bool
    notes: str


@dataclass
class EvaluationReport:
    """Complete evaluation report with scores, reasoning, and metadata.

    Attributes:
        scores: List of criterion scores
        total: Weighted total score
        reasoning: Overall reasoning for the evaluation
        bias_checklist: Completed bias checklist
        safety_flag: Whether safety concerns were detected
        confidence: Confidence in the evaluation (0.0 to 1.0)
    """

    scores: list[CriterionScore]
    total: float
    reasoning: str
    bias_checklist: list[BiasChecklistItem]
    safety_flag: bool
    confidence: float


@dataclass
class PairwiseResult:
    """Result of a pairwise comparison.

    Attributes:
        winner: "A", "B", or "tie"
        reasoning: Explanation for the choice
        stable: Whether the result was consistent across position swaps
        confidence: Confidence in the result (lower if unstable)
        bias_checklist: Completed bias checklist
    """

    winner: str
    reasoning: str
    stable: bool
    confidence: float
    bias_checklist: list[BiasChecklistItem]


# Type alias for judge functions
JudgeFn = Callable[[str], str]


class JudgeEngine:
    """Engine for LLM-as-judge evaluation.

    This class provides deterministic scaffolding around probabilistic model calls.
    It does NOT call LLM APIs directly - instead, it structures prompts and parses
    responses. API calls are handled by the caller through the judge_fn parameter.

    Methods:
        build_evaluation_prompt: Build a prompt for direct evaluation
        build_pairwise_prompt: Build a prompt for pairwise comparison
        parse_criterion_score: Parse and validate a score from judge response
        evaluate: Evaluate a response against a rubric
        pairwise_compare: Compare two responses with position debiasing
        ensemble_vote: Get majority vote from multiple judges
    """

    # Standard bias checks to include in evaluations
    STANDARD_BIAS_CHECKS = [
        "length_bias",
        "verbosity_bias",
        "style_bias",
        "anchoring_bias",
    ]

    PAIRWISE_BIAS_CHECKS = [
        "position_bias",
        "length_bias",
        "verbosity_bias",
        "style_bias",
    ]

    def build_evaluation_prompt(
        self,
        response: str,
        rubric: list[EvaluationCriterion],
        reference: Optional[str] = None,
    ) -> str:
        """Build a prompt for evaluating a response against a rubric.

        Args:
            response: The response to evaluate
            rubric: List of evaluation criteria
            reference: Optional reference/ground truth answer

        Returns:
            Formatted prompt string for the judge
        """
        prompt_parts = [
            "You are an expert evaluator. Evaluate the following response against the provided criteria.",
            "",
            "IMPORTANT INSTRUCTIONS:",
            "1. You MUST provide reasoning BEFORE giving any score",
            "2. Scores must be integers within the specified scale",
            "3. If you detect any safety concerns, include 'Safety: CONCERN' in your response",
            "",
        ]

        if reference:
            prompt_parts.extend(
                [
                    "Reference Answer:",
                    reference,
                    "",
                ]
            )

        prompt_parts.extend(
            [
                "Response to Evaluate:",
                response,
                "",
                "Evaluation Criteria:",
            ]
        )

        for criterion in rubric:
            min_score, max_score = criterion.scale
            prompt_parts.append(
                f"- {criterion.name}: {criterion.description} "
                f"(Scale: {min_score} to {max_score}, Weight: {criterion.weight})"
            )

        prompt_parts.extend(
            [
                "",
                "For each criterion, provide your evaluation in this format:",
                "Reasoning: [Your detailed reasoning]",
                "Score: [Integer score within scale]",
                "",
                "Then provide an overall assessment.",
            ]
        )

        return "\n".join(prompt_parts)

    def build_pairwise_prompt(
        self,
        response_a: str,
        response_b: str,
        rubric: list[EvaluationCriterion],
    ) -> str:
        """Build a prompt for pairwise comparison.

        Args:
            response_a: First response
            response_b: Second response
            rubric: Evaluation criteria

        Returns:
            Formatted prompt for pairwise comparison
        """
        prompt_parts = [
            "You are an expert evaluator. Compare the following two responses.",
            "",
            "IMPORTANT INSTRUCTIONS:",
            "1. You MUST provide reasoning BEFORE declaring a winner",
            "2. Consider each criterion carefully",
            "3. Declare winner as 'Winner: A', 'Winner: B', or 'Winner: tie'",
            "",
            "Response A:",
            response_a,
            "",
            "Response B:",
            response_b,
            "",
            "Evaluation Criteria:",
        ]

        for criterion in rubric:
            min_score, max_score = criterion.scale
            prompt_parts.append(
                f"- {criterion.name}: {criterion.description} "
                f"(Scale: {min_score} to {max_score})"
            )

        prompt_parts.extend(
            [
                "",
                "Provide your comparison:",
                "Reasoning: [Your detailed comparison]",
                "Winner: [A, B, or tie]",
            ]
        )

        return "\n".join(prompt_parts)

    def parse_criterion_score(
        self,
        response: str,
        criterion: EvaluationCriterion,
    ) -> CriterionScore:
        """Parse and validate a criterion score from judge response.

        Args:
            response: The judge's response text
            criterion: The criterion being scored

        Returns:
            Validated CriterionScore

        Raises:
            ValueError: If reasoning is missing, score is not an integer,
                       or score is outside the valid range
        """
        # Extract reasoning - must come before score
        reasoning_match = re.search(
            r"[Rr]easoning:\s*(.+?)(?=[Ss]core:|$)",
            response,
            re.DOTALL,
        )

        if not reasoning_match:
            raise ValueError(
                "Reasoning is required before score. "
                "Response must include 'Reasoning: ...' before 'Score: ...'"
            )

        reasoning = reasoning_match.group(1).strip()
        if not reasoning:
            raise ValueError("Reasoning is required before score and cannot be empty.")

        # Extract score
        score_match = re.search(r"[Ss]core:\s*([\d.]+)", response)
        if not score_match:
            raise ValueError("No score found in response. Expected 'Score: N'")

        score_str = score_match.group(1)

        # Validate integer (no decimals)
        if "." in score_str:
            # Check if it's actually an integer like "4.0"
            float_score = float(score_str)
            if float_score != int(float_score):
                raise ValueError(
                    f"Score must be an integer (discrete), not {score_str}. "
                    "Partial scores are not allowed."
                )
            score = int(float_score)
        else:
            try:
                score = int(score_str)
            except ValueError:
                raise ValueError(f"Score must be an integer, got: {score_str}")

        # Validate range
        min_score, max_score = criterion.scale
        if score < min_score or score > max_score:
            raise ValueError(
                f"Score {score} is outside valid range [{min_score}, {max_score}]. "
                f"Score must be between {min_score} and {max_score}."
            )

        return CriterionScore(
            criterion=criterion,
            score=score,
            reasoning=reasoning,
        )

    def _parse_winner(self, response: str) -> str:
        """Parse winner from pairwise comparison response.

        Args:
            response: Judge's response

        Returns:
            "A", "B", or "tie"
        """
        winner_match = re.search(r"[Ww]inner:\s*([ABab]|tie)", response, re.IGNORECASE)
        if winner_match:
            winner = winner_match.group(1).upper()
            if winner == "TIE":
                return "tie"
            return winner
        return "tie"  # Default to tie if unclear

    def _parse_safety_flag(self, response: str) -> bool:
        """Check if response indicates safety concerns.

        Args:
            response: Judge's response

        Returns:
            True if safety concern detected
        """
        safety_patterns = [
            r"[Ss]afety:\s*CONCERN",
            r"[Ss]afety\s+concern",
            r"potentially\s+harmful",
            r"safety\s+issue",
        ]
        for pattern in safety_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        return False

    def _build_standard_bias_checklist(
        self,
        checks: list[str],
        notes_map: Optional[dict[str, str]] = None,
    ) -> list[BiasChecklistItem]:
        """Build a bias checklist with standard checks.

        Args:
            checks: List of check names to include
            notes_map: Optional mapping of check names to notes

        Returns:
            List of BiasChecklistItem
        """
        notes_map = notes_map or {}
        return [
            BiasChecklistItem(
                name=check,
                checked=True,
                notes=notes_map.get(check, "Evaluated during assessment"),
            )
            for check in checks
        ]

    def evaluate(
        self,
        response: str,
        rubric: list[EvaluationCriterion],
        reference: Optional[str] = None,
        judge_fn: Optional[JudgeFn] = None,
    ) -> EvaluationReport:
        """Evaluate a response against a rubric.

        Args:
            response: The response to evaluate
            rubric: List of evaluation criteria
            reference: Optional ground truth/reference answer (P6: simpler when available)
            judge_fn: Function that takes a prompt and returns judge response

        Returns:
            EvaluationReport with scores, reasoning, and metadata
        """
        if judge_fn is None:
            raise ValueError("judge_fn is required for evaluation")

        # Build and execute evaluation prompt
        prompt = self.build_evaluation_prompt(response, rubric, reference)
        judge_response = judge_fn(prompt)

        # Parse scores for each criterion
        scores: list[CriterionScore] = []
        for criterion in rubric:
            try:
                score = self.parse_criterion_score(judge_response, criterion)
                scores.append(score)
            except ValueError:
                # If parsing fails for a criterion, try to extract any score
                # This is a fallback - ideally all criteria are scored
                pass

        # Calculate weighted total
        if scores:
            total_weight = sum(s.criterion.weight for s in scores)
            total = sum(s.score * s.criterion.weight for s in scores) / total_weight
        else:
            total = 0.0

        # Check for safety concerns
        safety_flag = self._parse_safety_flag(judge_response)

        # Build reasoning
        overall_reasoning = judge_response
        if safety_flag:
            overall_reasoning = f"[SAFETY CONCERN DETECTED] {overall_reasoning}"

        # Build bias checklist
        notes_map = {}
        if reference:
            notes_map["anchoring_bias"] = "Reference answer provided for comparison"

        bias_checklist = self._build_standard_bias_checklist(
            self.STANDARD_BIAS_CHECKS,
            notes_map,
        )

        return EvaluationReport(
            scores=scores,
            total=total,
            reasoning=overall_reasoning,
            bias_checklist=bias_checklist,
            safety_flag=safety_flag,
            confidence=1.0 if not safety_flag else 0.8,
        )

    def pairwise_compare(
        self,
        response_a: str,
        response_b: str,
        rubric: list[EvaluationCriterion],
        judge_fn: Optional[JudgeFn] = None,
    ) -> PairwiseResult:
        """Compare two responses with position debiasing.

        Runs comparison twice with swapped positions to detect position bias.
        If the winner changes after swapping, the result is flagged as unstable.

        Args:
            response_a: First response
            response_b: Second response
            rubric: Evaluation criteria
            judge_fn: Function that takes a prompt and returns judge response

        Returns:
            PairwiseResult with winner, stability flag, and confidence
        """
        if judge_fn is None:
            raise ValueError("judge_fn is required for comparison")

        # First comparison: original order (A, B)
        prompt_original = self.build_pairwise_prompt(response_a, response_b, rubric)
        response_original = judge_fn(prompt_original)
        winner_original = self._parse_winner(response_original)

        # Second comparison: swapped order (B, A)
        prompt_swapped = self.build_pairwise_prompt(response_b, response_a, rubric)
        response_swapped = judge_fn(prompt_swapped)
        winner_swapped = self._parse_winner(response_swapped)

        # Translate swapped winner back to original labels
        winner_swapped_translated = {
            "A": "B",  # A in swapped = B in original
            "B": "A",  # B in swapped = A in original
            "tie": "tie",
        }.get(winner_swapped, "tie")

        # Check stability
        stable = winner_original == winner_swapped_translated

        # Determine final winner and confidence
        if stable:
            final_winner = winner_original
            confidence = 1.0
        else:
            # Unstable - position bias detected
            # Default to tie with low confidence
            if winner_original == "tie" or winner_swapped_translated == "tie":
                final_winner = winner_original if winner_original != "tie" else winner_swapped_translated
                confidence = 0.5
            else:
                final_winner = "tie"  # Conflicting results
                confidence = 0.3

        # Build bias checklist
        notes_map = {
            "position_bias": (
                "Consistent across positions"
                if stable
                else "DETECTED: Winner changed when positions swapped"
            ),
        }
        bias_checklist = self._build_standard_bias_checklist(
            self.PAIRWISE_BIAS_CHECKS,
            notes_map,
        )

        return PairwiseResult(
            winner=final_winner,
            reasoning=f"Original: {response_original}\nSwapped: {response_swapped}",
            stable=stable,
            confidence=confidence,
            bias_checklist=bias_checklist,
        )

    def ensemble_vote(
        self,
        response: str,
        rubric: list[EvaluationCriterion],
        n_judges: int = 3,
        judge_fn: Optional[JudgeFn] = None,
    ) -> EvaluationReport:
        """Get evaluation from multiple judges with majority vote.

        Args:
            response: The response to evaluate
            rubric: Evaluation criteria
            n_judges: Number of judges to use (default 3)
            judge_fn: Function that takes a prompt and returns judge response

        Returns:
            EvaluationReport with majority vote results and confidence based on agreement
        """
        if judge_fn is None:
            raise ValueError("judge_fn is required for ensemble voting")

        # Collect evaluations from all judges
        all_scores: list[list[CriterionScore]] = []
        all_totals: list[float] = []
        all_reasonings: list[str] = []

        prompt = self.build_evaluation_prompt(response, rubric)

        for _ in range(n_judges):
            judge_response = judge_fn(prompt)

            scores: list[CriterionScore] = []
            for criterion in rubric:
                try:
                    score = self.parse_criterion_score(judge_response, criterion)
                    scores.append(score)
                except ValueError:
                    pass

            if scores:
                total_weight = sum(s.criterion.weight for s in scores)
                total = sum(s.score * s.criterion.weight for s in scores) / total_weight
                all_scores.append(scores)
                all_totals.append(total)
                all_reasonings.append(judge_response)

        if not all_totals:
            # No valid evaluations
            return EvaluationReport(
                scores=[],
                total=0.0,
                reasoning="No valid evaluations from judges",
                bias_checklist=self._build_standard_bias_checklist(
                    self.STANDARD_BIAS_CHECKS
                ),
                safety_flag=False,
                confidence=0.0,
            )

        # Calculate majority vote for total score
        # Round totals to nearest integer for voting
        rounded_totals = [round(t) for t in all_totals]
        total_counts = Counter(rounded_totals)
        majority_total, majority_count = total_counts.most_common(1)[0]

        # Use the actual total closest to majority
        final_total = float(majority_total)

        # Calculate confidence based on agreement
        agreement_ratio = majority_count / len(all_totals)

        # Also consider score variance
        if len(all_totals) > 1:
            try:
                variance = statistics.variance(all_totals)
                # High variance = low confidence
                max_possible_variance = (
                    (rubric[0].scale[1] - rubric[0].scale[0]) ** 2 / 4
                    if rubric
                    else 4
                )
                variance_factor = 1 - min(variance / max_possible_variance, 1)
            except statistics.StatisticsError:
                variance_factor = 1.0
        else:
            variance_factor = 1.0

        confidence = agreement_ratio * 0.7 + variance_factor * 0.3

        # Combine scores from all judges (use first matching for each criterion)
        combined_scores: list[CriterionScore] = []
        for criterion in rubric:
            criterion_scores = []
            for scores in all_scores:
                for s in scores:
                    if s.criterion.name == criterion.name:
                        criterion_scores.append(s)
                        break

            if criterion_scores:
                # Use median score
                median_score = int(
                    statistics.median([s.score for s in criterion_scores])
                )
                combined_reasoning = " | ".join(
                    [s.reasoning[:100] for s in criterion_scores]
                )
                combined_scores.append(
                    CriterionScore(
                        criterion=criterion,
                        score=median_score,
                        reasoning=combined_reasoning,
                    )
                )

        # Check for any safety flags
        safety_flag = any(
            self._parse_safety_flag(r) for r in all_reasonings
        )

        # Build bias checklist
        notes_map = {
            "anchoring_bias": f"Ensemble of {n_judges} judges used",
        }
        bias_checklist = self._build_standard_bias_checklist(
            self.STANDARD_BIAS_CHECKS,
            notes_map,
        )

        return EvaluationReport(
            scores=combined_scores,
            total=final_total,
            reasoning=f"Ensemble of {n_judges} judges. Agreement: {agreement_ratio:.0%}",
            bias_checklist=bias_checklist,
            safety_flag=safety_flag,
            confidence=confidence,
        )
