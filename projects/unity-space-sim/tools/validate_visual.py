#!/usr/bin/env python3
"""Visual validation tool: compare Blender renders against concept art.

Sends paired images (render + concept art) to Claude vision for scoring
against the visual fidelity rubric. Outputs structured results with
per-criterion scores and a pass/fail determination.

Usage (CLI):
    # Single pair
    python validate_visual.py \\
        --render path/to/render.png \\
        --concept path/to/concept.png \\
        --threshold 0.75

    # Batch mode: compare standard view pairs
    python validate_visual.py \\
        --render-dir path/to/renders/ \\
        --concept-dir path/to/concepts/ \\
        --threshold 0.75

    # JSON output
    python validate_visual.py --render r.png --concept c.png --format json

Usage (programmatic):
    from validate_visual import validate_render, ValidationResult
    result = validate_render("render.png", "concept.png")
    print(result.passed, result.normalized_score)

Requires ANTHROPIC_API_KEY in the environment.
"""

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Allow importing orchestration rubrics from the repo root
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CriterionResult:
    """Score for a single visual fidelity criterion."""

    name: str
    score: int
    max_score: int
    weight: float
    reasoning: str


@dataclass
class ValidationResult:
    """Complete validation result for a render vs concept art comparison."""

    render_path: str
    concept_path: str
    criteria: list[CriterionResult]
    total_score: float
    max_possible_score: float
    normalized_score: float  # 0.0 to 1.0
    threshold: float
    passed: bool
    model: str
    raw_response: str = ""


# ---------------------------------------------------------------------------
# Image encoding
# ---------------------------------------------------------------------------


def encode_image_base64(image_path: str) -> str:
    """Read an image file and return its base64 encoding."""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def detect_media_type(image_path: str) -> str:
    """Detect media type from file extension."""
    ext = Path(image_path).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "image/png")


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def build_validation_prompt(rubric_criteria: list) -> str:
    """Build the prompt for visual comparison scoring.

    Args:
        rubric_criteria: List of EvaluationCriterion from the rubric.

    Returns:
        Prompt string instructing the vision model how to score.
    """
    criteria_desc = []
    for c in rubric_criteria:
        criteria_desc.append(
            f'- **{c.name}** (scale {c.scale[0]}-{c.scale[1]}, weight {c.weight}): '
            f'{c.description}'
        )
    criteria_text = "\n".join(criteria_desc)

    return f"""You are an expert 3D asset reviewer. You have been shown two images:
- **Image 1** is a 3D render produced by a Blender Python script.
- **Image 2** is the approved concept art that the render should match.

Compare Image 1 (the render) against Image 2 (the concept art) and score each criterion below.

## Criteria

{criteria_text}

## Instructions

1. For each criterion, write 1-2 sentences of reasoning FIRST, then give an integer score.
2. Be strict: a score of 2 means the render closely matches the concept art for that criterion.
3. A score of 0 means the render completely fails to match.
4. Focus on structural accuracy (shape, count, proportions) over rendering quality (lighting, textures).

## Required Output Format

You MUST respond with ONLY a JSON object in this exact format (no markdown fences, no extra text):

{{
  "criteria": [
    {{"name": "Silhouette Match", "reasoning": "...", "score": 0}},
    {{"name": "Proportions", "reasoning": "...", "score": 0}},
    {{"name": "Component Count", "reasoning": "...", "score": 0}},
    {{"name": "Material Fidelity", "reasoning": "...", "score": 0}},
    {{"name": "Overall Impression", "reasoning": "...", "score": 0}}
  ]
}}"""


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def parse_vision_response(
    response_text: str,
    rubric_criteria: list,
) -> list[CriterionResult]:
    """Parse the vision model's JSON response into CriterionResult objects.

    Args:
        response_text: Raw response from the vision model.
        rubric_criteria: List of EvaluationCriterion for validation.

    Returns:
        List of CriterionResult objects.

    Raises:
        ValueError: If response is malformed or scores are out of range.
    """
    # Strip markdown code fences if present
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON response: {e}\nRaw: {response_text[:500]}")

    if "criteria" not in data:
        raise ValueError(f"Response missing 'criteria' key. Got keys: {list(data.keys())}")

    # Build lookup for rubric criteria
    rubric_lookup = {c.name: c for c in rubric_criteria}

    results = []
    for item in data["criteria"]:
        name = item.get("name", "")
        score = item.get("score")
        reasoning = item.get("reasoning", "")

        if name not in rubric_lookup:
            continue  # skip unknown criteria

        criterion = rubric_lookup[name]
        min_score, max_score = criterion.scale

        if not isinstance(score, int):
            try:
                score = int(score)
            except (TypeError, ValueError):
                raise ValueError(f"Score for '{name}' must be an integer, got: {score}")

        if score < min_score or score > max_score:
            raise ValueError(
                f"Score {score} for '{name}' is outside valid range "
                f"[{min_score}, {max_score}]"
            )

        results.append(CriterionResult(
            name=name,
            score=score,
            max_score=max_score,
            weight=criterion.weight,
            reasoning=reasoning,
        ))

    if not results:
        raise ValueError("No valid criterion scores parsed from response.")

    return results


# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------


def _call_vision_sdk(
    render_path: str,
    concept_path: str,
    prompt_text: str,
    model: str,
    api_key: str,
) -> str:
    """Call Anthropic vision API via SDK (requires ANTHROPIC_API_KEY)."""
    import anthropic

    render_b64 = encode_image_base64(render_path)
    concept_b64 = encode_image_base64(concept_path)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Image 1 (3D render from Blender):",
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": detect_media_type(render_path),
                        "data": render_b64,
                    },
                },
                {
                    "type": "text",
                    "text": "Image 2 (approved concept art reference):",
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": detect_media_type(concept_path),
                        "data": concept_b64,
                    },
                },
                {
                    "type": "text",
                    "text": prompt_text,
                },
            ],
        }],
    )
    return message.content[0].text


def _call_vision_cli(
    render_path: str,
    concept_path: str,
    prompt_text: str,
    model: str,
) -> str:
    """Call Claude vision via the claude CLI (handles OAuth natively).

    The CLI's Read tool can display images to the model. This path is used
    when ANTHROPIC_API_KEY is not available but the user has an OAuth session.
    """
    render_abs = os.path.abspath(render_path)
    concept_abs = os.path.abspath(concept_path)

    full_prompt = (
        f"Read these two image files using the Read tool, then compare them.\n\n"
        f"Image 1 (3D render from Blender): {render_abs}\n"
        f"Image 2 (approved concept art reference): {concept_abs}\n\n"
        f"After reading both images, apply the following evaluation:\n\n"
        f"{prompt_text}"
    )

    cmd = [
        "claude", "-p",
        "--output-format", "json",
        "--model", model,
        "--allowedTools", "Read",
    ]

    # Allow running inside a Claude Code session by clearing the nesting guard
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    result = subprocess.run(
        cmd,
        input=full_prompt,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"claude CLI exited with code {result.returncode}: "
            f"{result.stderr[:500]}"
        )

    data = json.loads(result.stdout)
    if data.get("is_error"):
        raise RuntimeError(f"claude CLI error: {data.get('result', 'unknown')}")

    return data["result"]


def validate_render(
    render_path: str,
    concept_path: str,
    threshold: float = 0.75,
    model: str = "claude-sonnet-4-20250514",
    rubric: Optional[list] = None,
) -> ValidationResult:
    """Compare a render against concept art using Claude vision.

    Authentication: tries ANTHROPIC_API_KEY (SDK) first, then falls back
    to the claude CLI which handles OAuth natively.

    Args:
        render_path: Path to the Blender-rendered PNG.
        concept_path: Path to the concept art PNG.
        threshold: Normalized score (0-1) required to pass.
        model: Anthropic model to use for vision.
        rubric: Optional override rubric criteria list.

    Returns:
        ValidationResult with scores and pass/fail.

    Raises:
        FileNotFoundError: If image files don't exist.
        ValueError: If no authentication method is available.
    """
    from orchestration.rubrics import VISUAL_FIDELITY_RUBRIC

    rubric = rubric or VISUAL_FIDELITY_RUBRIC

    # Validate inputs
    for path in (render_path, concept_path):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Image not found: {path}")

    # Build prompt
    prompt_text = build_validation_prompt(rubric)

    # Try SDK first (ANTHROPIC_API_KEY), fall back to claude CLI (OAuth)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        raw_response = _call_vision_sdk(
            render_path, concept_path, prompt_text, model, api_key,
        )
    elif shutil.which("claude"):
        raw_response = _call_vision_cli(
            render_path, concept_path, prompt_text, model,
        )
    else:
        raise ValueError(
            "No authentication available. Set ANTHROPIC_API_KEY for SDK access, "
            "or install the claude CLI (handles OAuth natively)."
        )

    # Parse response
    criteria_results = parse_vision_response(raw_response, rubric)

    # Calculate scores
    total_score = sum(c.score * c.weight for c in criteria_results)
    max_possible = sum(c.max_score * c.weight for c in criteria_results)
    normalized = total_score / max_possible if max_possible > 0 else 0.0

    return ValidationResult(
        render_path=render_path,
        concept_path=concept_path,
        criteria=criteria_results,
        total_score=total_score,
        max_possible_score=max_possible,
        normalized_score=normalized,
        threshold=threshold,
        passed=normalized >= threshold,
        model=model,
        raw_response=raw_response,
    )


# Default view pairs: render filename -> concept art filename
DEFAULT_VIEW_PAIRS = {
    "viper_fighter_3quarter.png": "hero.png",
    "viper_fighter_side.png": "side.png",
}


def validate_render_batch(
    render_dir: str,
    concept_dir: str,
    view_pairs: Optional[dict[str, str]] = None,
    threshold: float = 0.75,
    model: str = "claude-sonnet-4-20250514",
) -> list[ValidationResult]:
    """Validate multiple render/concept pairs.

    Args:
        render_dir: Directory containing rendered PNGs.
        concept_dir: Directory containing concept art PNGs.
        view_pairs: Mapping of render filename to concept filename.
        threshold: Pass threshold for each pair.
        model: Vision model to use.

    Returns:
        List of ValidationResult, one per pair.
    """
    view_pairs = view_pairs or DEFAULT_VIEW_PAIRS
    results = []

    for render_name, concept_name in view_pairs.items():
        render_path = os.path.join(render_dir, render_name)
        concept_path = os.path.join(concept_dir, concept_name)

        if not os.path.isfile(render_path):
            print(f"Skipping {render_name}: render not found", file=sys.stderr)
            continue
        if not os.path.isfile(concept_path):
            print(f"Skipping {concept_name}: concept art not found", file=sys.stderr)
            continue

        result = validate_render(
            render_path=render_path,
            concept_path=concept_path,
            threshold=threshold,
            model=model,
        )
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# CLI output formatting
# ---------------------------------------------------------------------------


def format_result_text(result: ValidationResult) -> str:
    """Format a ValidationResult as human-readable text."""
    status = "PASS" if result.passed else "FAIL"
    lines = [
        f"[{status}] {Path(result.render_path).name} vs {Path(result.concept_path).name}",
        f"  Score: {result.normalized_score:.0%} (threshold: {result.threshold:.0%})",
        f"  Weighted total: {result.total_score:.1f} / {result.max_possible_score:.1f}",
        f"  Model: {result.model}",
        "",
    ]
    for c in result.criteria:
        lines.append(
            f"  {c.name}: {c.score}/{c.max_score} (weight {c.weight})"
        )
        lines.append(f"    {c.reasoning}")
    return "\n".join(lines)


def format_result_json(result: ValidationResult) -> str:
    """Format a ValidationResult as JSON."""
    d = asdict(result)
    del d["raw_response"]  # omit verbose raw response
    return json.dumps(d, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Compare Blender renders against concept art using vision AI"
    )

    # Single pair mode
    parser.add_argument("--render", help="Path to a single render PNG")
    parser.add_argument("--concept", help="Path to a single concept art PNG")

    # Batch mode
    parser.add_argument("--render-dir", help="Directory containing render PNGs")
    parser.add_argument("--concept-dir", help="Directory containing concept art PNGs")

    # Options
    parser.add_argument(
        "--threshold", type=float, default=0.75,
        help="Normalized score (0-1) required to pass (default: 0.75)",
    )
    parser.add_argument(
        "--model", default="claude-sonnet-4-20250514",
        help="Anthropic model for vision (default: claude-sonnet-4-20250514)",
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    # Load .env if available
    try:
        from dotenv import load_dotenv
        for candidate in [Path.cwd(), _REPO_ROOT]:
            env_path = candidate / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                break
    except ImportError:
        pass

    # Determine mode
    if args.render and args.concept:
        results = [validate_render(
            render_path=args.render,
            concept_path=args.concept,
            threshold=args.threshold,
            model=args.model,
        )]
    elif args.render_dir and args.concept_dir:
        results = validate_render_batch(
            render_dir=args.render_dir,
            concept_dir=args.concept_dir,
            threshold=args.threshold,
            model=args.model,
        )
    else:
        parser.error(
            "Provide either --render + --concept (single pair) "
            "or --render-dir + --concept-dir (batch mode)"
        )

    # Output results
    all_passed = True
    for result in results:
        if args.format == "json":
            print(format_result_json(result))
        else:
            print(format_result_text(result))
            print()
        if not result.passed:
            all_passed = False

    # Exit code: 0 if all passed, 1 if any failed
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
