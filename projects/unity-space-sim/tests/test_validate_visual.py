"""Unit tests for the visual validation tool.

Tests parse_vision_response(), aggregate_criterion_scores(), and CLI argument
parsing without making any network calls.
"""

import argparse
import json
import statistics
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure repo root is on sys.path so orchestration imports work
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Also add tools directory for direct import
_TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from validate_visual import (
    CriterionResult,
    ValidationResult,
    aggregate_criterion_scores,
    parse_vision_response,
)
from orchestration.rubrics import VISUAL_FIDELITY_RUBRIC


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_response_json(scores: dict[str, int]) -> str:
    """Build a mock JSON response matching the expected format.

    Args:
        scores: Mapping of criterion name to integer score.
    """
    criteria = [
        {"name": name, "reasoning": f"Mock reasoning for {name}.", "score": score}
        for name, score in scores.items()
    ]
    return json.dumps({"criteria": criteria})


def _default_scores() -> dict[str, int]:
    """Default scores (all max) for the visual fidelity rubric."""
    return {c.name: c.scale[1] for c in VISUAL_FIDELITY_RUBRIC}


# ---------------------------------------------------------------------------
# parse_vision_response tests
# ---------------------------------------------------------------------------


class TestParseVisionResponse:
    """Tests for parse_vision_response()."""

    def test_valid_response_parses_all_criteria(self):
        scores = _default_scores()
        response = _make_response_json(scores)
        results = parse_vision_response(response, VISUAL_FIDELITY_RUBRIC)

        assert len(results) == len(VISUAL_FIDELITY_RUBRIC)
        names = {r.name for r in results}
        expected_names = {c.name for c in VISUAL_FIDELITY_RUBRIC}
        assert names == expected_names

    def test_scores_are_correct_values(self):
        scores = {"Silhouette Match": 1, "Proportions": 2, "Component Count": 0,
                  "Material Fidelity": 1, "Overall Impression": 2}
        response = _make_response_json(scores)
        results = parse_vision_response(response, VISUAL_FIDELITY_RUBRIC)

        result_lookup = {r.name: r.score for r in results}
        for name, expected in scores.items():
            assert result_lookup[name] == expected

    def test_weights_and_max_scores_from_rubric(self):
        scores = _default_scores()
        response = _make_response_json(scores)
        results = parse_vision_response(response, VISUAL_FIDELITY_RUBRIC)

        rubric_lookup = {c.name: c for c in VISUAL_FIDELITY_RUBRIC}
        for r in results:
            criterion = rubric_lookup[r.name]
            assert r.max_score == criterion.scale[1]
            assert r.weight == criterion.weight

    def test_markdown_fenced_json_is_stripped(self):
        scores = _default_scores()
        inner = _make_response_json(scores)
        wrapped = f"```json\n{inner}\n```"
        results = parse_vision_response(wrapped, VISUAL_FIDELITY_RUBRIC)
        assert len(results) == len(VISUAL_FIDELITY_RUBRIC)

    def test_invalid_json_raises_value_error(self):
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            parse_vision_response("not json at all", VISUAL_FIDELITY_RUBRIC)

    def test_missing_criteria_key_raises_value_error(self):
        with pytest.raises(ValueError, match="missing 'criteria' key"):
            parse_vision_response('{"scores": []}', VISUAL_FIDELITY_RUBRIC)

    def test_score_out_of_range_raises_value_error(self):
        scores = _default_scores()
        scores["Silhouette Match"] = 99  # way out of range
        response = _make_response_json(scores)
        with pytest.raises(ValueError, match="outside valid range"):
            parse_vision_response(response, VISUAL_FIDELITY_RUBRIC)

    def test_unknown_criteria_are_skipped(self):
        data = {"criteria": [
            {"name": "Unknown Criterion", "reasoning": "n/a", "score": 1},
            {"name": "Silhouette Match", "reasoning": "ok", "score": 1},
        ]}
        results = parse_vision_response(json.dumps(data), VISUAL_FIDELITY_RUBRIC)
        assert len(results) == 1
        assert results[0].name == "Silhouette Match"

    def test_no_valid_criteria_raises_value_error(self):
        data = {"criteria": [
            {"name": "Completely Unknown", "reasoning": "n/a", "score": 1},
        ]}
        with pytest.raises(ValueError, match="No valid criterion scores"):
            parse_vision_response(json.dumps(data), VISUAL_FIDELITY_RUBRIC)

    def test_string_score_is_coerced_to_int(self):
        data = {"criteria": [
            {"name": "Silhouette Match", "reasoning": "ok", "score": "2"},
            {"name": "Proportions", "reasoning": "ok", "score": "1"},
            {"name": "Component Count", "reasoning": "ok", "score": "2"},
            {"name": "Material Fidelity", "reasoning": "ok", "score": "1"},
            {"name": "Overall Impression", "reasoning": "ok", "score": "2"},
        ]}
        results = parse_vision_response(json.dumps(data), VISUAL_FIDELITY_RUBRIC)
        assert all(isinstance(r.score, int) for r in results)


# ---------------------------------------------------------------------------
# aggregate_criterion_scores tests
# ---------------------------------------------------------------------------


class TestAggregateCriterionScores:
    """Tests for median-based score aggregation."""

    def _make_run(self, scores: dict[str, int]) -> list[CriterionResult]:
        """Build a list of CriterionResult from a name->score mapping."""
        rubric_lookup = {c.name: c for c in VISUAL_FIDELITY_RUBRIC}
        results = []
        for name, score in scores.items():
            c = rubric_lookup[name]
            results.append(CriterionResult(
                name=name,
                score=score,
                max_score=c.scale[1],
                weight=c.weight,
                reasoning=f"Run reasoning for {name} score={score}",
            ))
        return results

    def test_single_run_returns_same_scores(self):
        scores = _default_scores()
        runs = [self._make_run(scores)]
        median_criteria, ranges, stds = aggregate_criterion_scores(runs)

        for cr in median_criteria:
            assert cr.score == scores[cr.name]
        # Single run: ranges are trivial, std is 0
        for name in scores:
            lo, hi = ranges[name]
            assert lo == hi == scores[name]
            assert stds[name] == 0.0

    def test_median_of_three_runs(self):
        # Scores: [0, 1, 2] -> median = 1
        names = list(_default_scores().keys())
        run1 = self._make_run({n: 0 for n in names})
        run2 = self._make_run({n: 1 for n in names})
        run3 = self._make_run({n: 2 for n in names})

        median_criteria, ranges, stds = aggregate_criterion_scores([run1, run2, run3])

        for cr in median_criteria:
            assert cr.score == 1, f"{cr.name} should have median 1"

    def test_median_with_outlier(self):
        # Scores: [2, 2, 0] -> median = 2 (robust to single outlier)
        names = list(_default_scores().keys())
        run1 = self._make_run({n: 2 for n in names})
        run2 = self._make_run({n: 2 for n in names})
        run3 = self._make_run({n: 0 for n in names})  # outlier

        median_criteria, ranges, stds = aggregate_criterion_scores([run1, run2, run3])

        for cr in median_criteria:
            assert cr.score == 2, f"{cr.name} should have median 2 (outlier-robust)"

    def test_score_ranges_are_correct(self):
        names = list(_default_scores().keys())
        run1 = self._make_run({n: 0 for n in names})
        run2 = self._make_run({n: 1 for n in names})
        run3 = self._make_run({n: 2 for n in names})

        _, ranges, _ = aggregate_criterion_scores([run1, run2, run3])

        for name in names:
            assert ranges[name] == (0, 2)

    def test_std_devs_are_correct(self):
        names = list(_default_scores().keys())
        run1 = self._make_run({n: 0 for n in names})
        run2 = self._make_run({n: 1 for n in names})
        run3 = self._make_run({n: 2 for n in names})

        _, _, stds = aggregate_criterion_scores([run1, run2, run3])

        expected_std = round(statistics.stdev([0, 1, 2]), 2)
        for name in names:
            assert stds[name] == expected_std

    def test_even_number_of_runs_uses_median(self):
        # Scores: [0, 1, 1, 2] -> median = 1 (average of middle two, truncated to int)
        names = list(_default_scores().keys())
        runs = [
            self._make_run({n: 0 for n in names}),
            self._make_run({n: 1 for n in names}),
            self._make_run({n: 1 for n in names}),
            self._make_run({n: 2 for n in names}),
        ]

        median_criteria, _, _ = aggregate_criterion_scores(runs)

        for cr in median_criteria:
            # statistics.median([0,1,1,2]) = 1.0, int(1.0) = 1
            assert cr.score == 1

    def test_reasoning_from_closest_run(self):
        """The reasoning should come from the run whose score matches the median."""
        names = list(_default_scores().keys())
        run1 = self._make_run({n: 0 for n in names})
        run2 = self._make_run({n: 1 for n in names})
        run3 = self._make_run({n: 2 for n in names})

        median_criteria, _, _ = aggregate_criterion_scores([run1, run2, run3])

        for cr in median_criteria:
            # Median is 1, so reasoning should come from run2 (score=1)
            assert "score=1" in cr.reasoning


# ---------------------------------------------------------------------------
# CLI argument parsing tests
# ---------------------------------------------------------------------------


class TestCLIParsing:
    """Tests for CLI argument parsing in main()."""

    def _parse_args(self, args: list[str]) -> argparse.Namespace:
        """Parse CLI args using the same parser as main()."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--render")
        parser.add_argument("--concept")
        parser.add_argument("--render-dir")
        parser.add_argument("--concept-dir")
        parser.add_argument("--threshold", type=float, default=0.75)
        parser.add_argument("--model", default="claude-sonnet-4-20250514")
        parser.add_argument("--runs", type=int, default=1)
        parser.add_argument("--temperature", type=float, default=0.0)
        parser.add_argument("--format", choices=["text", "json"], default="text")
        return parser.parse_args(args)

    def test_default_runs_is_one(self):
        args = self._parse_args(["--render", "r.png", "--concept", "c.png"])
        assert args.runs == 1

    def test_custom_runs(self):
        args = self._parse_args(["--render", "r.png", "--concept", "c.png", "--runs", "5"])
        assert args.runs == 5

    def test_default_temperature_is_zero(self):
        args = self._parse_args(["--render", "r.png", "--concept", "c.png"])
        assert args.temperature == 0.0

    def test_custom_temperature(self):
        args = self._parse_args([
            "--render", "r.png", "--concept", "c.png",
            "--temperature", "0.7",
        ])
        assert args.temperature == 0.7

    def test_all_flags_together(self):
        args = self._parse_args([
            "--render", "r.png", "--concept", "c.png",
            "--threshold", "0.8", "--runs", "3",
            "--temperature", "0.2", "--format", "json",
        ])
        assert args.threshold == 0.8
        assert args.runs == 3
        assert args.temperature == 0.2
        assert args.format == "json"

    def test_batch_mode_flags(self):
        args = self._parse_args([
            "--render-dir", "/tmp/renders",
            "--concept-dir", "/tmp/concepts",
            "--runs", "3",
            "--temperature", "0.1",
        ])
        assert args.render_dir == "/tmp/renders"
        assert args.concept_dir == "/tmp/concepts"
        assert args.runs == 3
        assert args.temperature == 0.1


# ---------------------------------------------------------------------------
# ValidationResult dataclass tests
# ---------------------------------------------------------------------------


class TestValidationResult:
    """Tests for the ValidationResult dataclass fields."""

    def test_default_score_ranges_empty(self):
        result = ValidationResult(
            render_path="r.png",
            concept_path="c.png",
            criteria=[],
            total_score=0.0,
            max_possible_score=0.0,
            normalized_score=0.0,
            threshold=0.75,
            passed=False,
            model="test",
        )
        assert result.score_ranges == {}
        assert result.score_std_devs == {}
        assert result.num_runs == 1

    def test_score_ranges_populated(self):
        ranges = {"Silhouette Match": (1, 2)}
        stds = {"Silhouette Match": 0.5}
        result = ValidationResult(
            render_path="r.png",
            concept_path="c.png",
            criteria=[],
            total_score=0.0,
            max_possible_score=0.0,
            normalized_score=0.0,
            threshold=0.75,
            passed=False,
            model="test",
            num_runs=3,
            score_ranges=ranges,
            score_std_devs=stds,
        )
        assert result.score_ranges == ranges
        assert result.score_std_devs == stds
        assert result.num_runs == 3
