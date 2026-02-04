#!/usr/bin/env python3
"""
CLI entry point for the orchestration framework.

This module provides command-line access to all orchestration components.
Each subcommand is a thin wrapper around the corresponding library module.

Usage:
    agents route "Add a login page"
    agents judge --response response.txt --reference reference.txt --rubric code_review
    agents review --diff <(git diff main)
    agents rubric list
    agents rubric show code_review

    eco route "Add a login page"           # economy mode: uses smaller, cheaper models
    eco judge --response r.txt --ref ref.txt --rubric code_review  # economy mode

Economy mode can also be enabled explicitly with the --economy flag:
    agents --economy route "Add a login page"

When invoked as ``eco``, economy mode is enabled automatically.
"""

import argparse
import json
import os
import sys
from typing import Any


def format_output(data: Any, output_format: str) -> str:
    """Format output based on the requested format."""
    if output_format == "json":
        return json.dumps(data, indent=2)

    # Default text format
    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            lines.append(f"{key}={value}")
        return "\n".join(lines)
    elif isinstance(data, list):
        return "\n".join(str(item) for item in data)
    return str(data)


def read_input(args: argparse.Namespace, input_attr: str = "input") -> str:
    """Read input from argument or stdin."""
    input_value = getattr(args, input_attr, None)
    if input_value:
        return input_value

    if not sys.stdin.isatty():
        return sys.stdin.read().strip()

    return ""


# -----------------------------------------------------------------------------
# Subcommand: route
# -----------------------------------------------------------------------------

def cmd_route(args: argparse.Namespace) -> int:
    """Classify and route a task description."""
    task = read_input(args)

    if not task:
        print("Error: No task description provided", file=sys.stderr)
        print(
            "Usage: agents route \"task description\" or echo \"task\" | agents route",
            file=sys.stderr,
        )
        return 1

    # Placeholder routing logic - will be replaced by router module
    # For now, provide a reasonable default based on keywords
    task_lower = task.lower()

    if any(word in task_lower for word in ["fix", "bug", "error", "broken"]):
        task_type = "bugfix"
        sequence = ["engineer", "reviewer"]
        priority = "high"
    elif any(word in task_lower for word in ["add", "create", "new", "implement"]):
        task_type = "feature"
        sequence = ["test-writer", "engineer", "reviewer"]
        priority = "medium"
    elif any(word in task_lower for word in ["refactor", "clean", "improve"]):
        task_type = "refactor"
        sequence = ["engineer", "reviewer"]
        priority = "low"
    elif any(word in task_lower for word in ["doc", "readme", "comment"]):
        task_type = "documentation"
        sequence = ["writer", "reviewer"]
        priority = "low"
    else:
        task_type = "feature"
        sequence = ["engineer", "reviewer"]
        priority = "medium"

    result = {
        "task_type": task_type,
        "sequence": sequence,
        "priority": priority,
        "task": task,
    }

    print(format_output(result, args.format))
    return 0


def setup_route_parser(subparsers: argparse._SubParsersAction) -> None:
    """Set up the route subcommand parser."""
    parser = subparsers.add_parser(
        "route",
        help="Classify and route a task description",
        description="Analyze a task description and determine the appropriate agent sequence.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Task description (can also be provided via stdin)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.set_defaults(func=cmd_route)


# -----------------------------------------------------------------------------
# Subcommand: judge
# -----------------------------------------------------------------------------

def cmd_judge(args: argparse.Namespace) -> int:
    """Evaluate a response against a reference using a rubric."""
    # Read response
    if args.response == "-":
        response = sys.stdin.read().strip()
    else:
        try:
            with open(args.response) as f:
                response = f.read()
        except FileNotFoundError:
            print(f"Error: Response file not found: {args.response}", file=sys.stderr)
            return 1

    # Read reference
    try:
        with open(args.reference) as f:
            reference = f.read()
    except FileNotFoundError:
        print(f"Error: Reference file not found: {args.reference}", file=sys.stderr)
        return 1

    # Placeholder evaluation logic - will be replaced by judge module
    rubric_name = args.rubric

    # Simple placeholder scoring
    result = {
        "rubric": rubric_name,
        "score": 0.75,  # Placeholder
        "criteria": {
            "correctness": {"score": 0.8, "feedback": "Response addresses the main points."},
            "completeness": {"score": 0.7, "feedback": "Some details could be expanded."},
            "clarity": {"score": 0.75, "feedback": "Well structured and readable."},
        },
        "summary": f"Evaluation using {rubric_name} rubric completed.",
    }

    print(format_output(result, args.format))
    return 0


def setup_judge_parser(subparsers: argparse._SubParsersAction) -> None:
    """Set up the judge subcommand parser."""
    parser = subparsers.add_parser(
        "judge",
        help="Evaluate a response against a reference",
        description="Run evaluation on a response compared to a reference using a specified rubric.",
    )
    parser.add_argument(
        "--response",
        required=True,
        help="Path to response file (use - for stdin)",
    )
    parser.add_argument(
        "--reference",
        required=True,
        help="Path to reference file",
    )
    parser.add_argument(
        "--rubric",
        required=True,
        help="Name of the rubric to use for evaluation",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.set_defaults(func=cmd_judge)


# -----------------------------------------------------------------------------
# Subcommand: review
# -----------------------------------------------------------------------------

def cmd_review(args: argparse.Namespace) -> int:
    """Generate a review prompt for a diff."""
    # Read diff
    if args.diff == "-":
        diff = sys.stdin.read()
    else:
        try:
            with open(args.diff) as f:
                diff = f.read()
        except FileNotFoundError:
            print(f"Error: Diff file not found: {args.diff}", file=sys.stderr)
            return 1

    if not diff.strip():
        print("Error: No diff content provided", file=sys.stderr)
        return 1

    # Placeholder review prompt generation - will be replaced by review module
    review_prompt = f"""Please review the following code changes:

```diff
{diff}
```

Consider the following aspects:
1. Code correctness and potential bugs
2. Code style and readability
3. Performance implications
4. Security considerations
5. Test coverage

Provide specific, actionable feedback."""

    result = {
        "prompt": review_prompt,
        "diff_lines": len(diff.splitlines()),
    }

    if args.format == "json":
        print(format_output(result, args.format))
    else:
        print(review_prompt)

    return 0


def setup_review_parser(subparsers: argparse._SubParsersAction) -> None:
    """Set up the review subcommand parser."""
    parser = subparsers.add_parser(
        "review",
        help="Generate a review prompt for a diff",
        description="Create a structured review prompt from a git diff.",
    )
    parser.add_argument(
        "--diff",
        default="-",
        help="Path to diff file (default: stdin)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.set_defaults(func=cmd_review)


# -----------------------------------------------------------------------------
# Subcommand: rubric
# -----------------------------------------------------------------------------

# Placeholder rubrics - will be replaced by rubric module
RUBRICS = {
    "code_review": {
        "name": "code_review",
        "description": "Evaluate code changes for quality and correctness",
        "criteria": [
            {"name": "correctness", "weight": 0.3, "description": "Code functions as intended"},
            {"name": "readability", "weight": 0.2, "description": "Code is clear and well-structured"},
            {"name": "performance", "weight": 0.2, "description": "Code is efficient"},
            {"name": "security", "weight": 0.2, "description": "Code follows security best practices"},
            {"name": "testing", "weight": 0.1, "description": "Adequate test coverage"},
        ],
    },
    "documentation": {
        "name": "documentation",
        "description": "Evaluate documentation quality",
        "criteria": [
            {"name": "accuracy", "weight": 0.3, "description": "Information is correct"},
            {"name": "completeness", "weight": 0.3, "description": "All necessary topics covered"},
            {"name": "clarity", "weight": 0.2, "description": "Easy to understand"},
            {"name": "examples", "weight": 0.2, "description": "Helpful examples provided"},
        ],
    },
    "task_completion": {
        "name": "task_completion",
        "description": "Evaluate task completion quality",
        "criteria": [
            {"name": "requirements_met", "weight": 0.4, "description": "All requirements addressed"},
            {"name": "quality", "weight": 0.3, "description": "Work is high quality"},
            {"name": "efficiency", "weight": 0.15, "description": "Solution is efficient"},
            {"name": "maintainability", "weight": 0.15, "description": "Solution is maintainable"},
        ],
    },
}


def cmd_rubric_list(args: argparse.Namespace) -> int:
    """List available rubrics."""
    rubrics = [
        {"name": name, "description": rubric["description"]}
        for name, rubric in RUBRICS.items()
    ]

    if args.format == "json":
        print(format_output(rubrics, args.format))
    else:
        for rubric in rubrics:
            print(f"{rubric['name']}: {rubric['description']}")

    return 0


def cmd_rubric_show(args: argparse.Namespace) -> int:
    """Show details of a specific rubric."""
    rubric_name = args.name

    if rubric_name not in RUBRICS:
        print(f"Error: Rubric not found: {rubric_name}", file=sys.stderr)
        print(f"Available rubrics: {', '.join(RUBRICS.keys())}", file=sys.stderr)
        return 1

    rubric = RUBRICS[rubric_name]

    if args.format == "json":
        print(format_output(rubric, args.format))
    else:
        print(f"Rubric: {rubric['name']}")
        print(f"Description: {rubric['description']}")
        print("\nCriteria:")
        for criterion in rubric["criteria"]:
            print(f"  - {criterion['name']} (weight: {criterion['weight']})")
            print(f"    {criterion['description']}")

    return 0


def setup_rubric_parser(subparsers: argparse._SubParsersAction) -> None:
    """Set up the rubric subcommand parser."""
    parser = subparsers.add_parser(
        "rubric",
        help="List and show evaluation rubrics",
        description="Manage evaluation rubrics for the judge system.",
    )

    rubric_subparsers = parser.add_subparsers(
        dest="rubric_command",
        metavar="COMMAND",
    )

    # rubric list
    list_parser = rubric_subparsers.add_parser(
        "list",
        help="List available rubrics",
    )
    list_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    list_parser.set_defaults(func=cmd_rubric_list)

    # rubric show
    show_parser = rubric_subparsers.add_parser(
        "show",
        help="Show details of a rubric",
    )
    show_parser.add_argument(
        "name",
        help="Name of the rubric to show",
    )
    show_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    show_parser.set_defaults(func=cmd_rubric_show)


def cmd_rubric(args: argparse.Namespace) -> int:
    """Handle rubric command without subcommand."""
    if not args.rubric_command:
        print("Error: rubric requires a subcommand (list or show)", file=sys.stderr)
        print("Usage: agents rubric list | agents rubric show <name>", file=sys.stderr)
        return 1
    return args.func(args)


# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------

def _invoked_as_eco() -> bool:
    """Check whether the CLI was invoked via the ``eco`` entry point."""
    argv0 = os.path.basename(sys.argv[0]) if sys.argv else ""
    return argv0 == "eco"


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    prog = "eco" if _invoked_as_eco() else "agents"
    parser = argparse.ArgumentParser(
        prog=prog,
        description=(
            "Orchestration framework CLI - command-line access to all orchestration "
            "components. Can be invoked as 'agents' (default models) or 'eco' (economy "
            "mode, uses smaller and cheaper models). Economy mode can also be enabled "
            "with --economy."
        ),
        epilog=f"For more information on a command, use: {prog} <command> --help",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    parser.add_argument(
        "--economy",
        action="store_true",
        default=False,
        help="Enable economy mode: use smaller, cheaper models (automatic when invoked as 'eco')",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        metavar="COMMAND",
        help="Available commands",
    )

    # Register all subcommands
    setup_route_parser(subparsers)
    setup_judge_parser(subparsers)
    setup_review_parser(subparsers)
    setup_rubric_parser(subparsers)

    return parser


def main() -> int:
    """Main entry point for the CLI.

    Economy mode is activated when either:
    - The CLI is invoked via the ``eco`` entry point, or
    - The ``--economy`` flag is passed explicitly.

    When economy mode is active, ``args.economy`` is ``True`` and downstream
    modules should select smaller, cheaper models accordingly.
    """
    parser = create_parser()
    args = parser.parse_args()

    # Enable economy mode when invoked as 'eco', even without --economy flag
    if _invoked_as_eco():
        args.economy = True

    if not args.command:
        parser.print_help()
        return 0

    # Special handling for rubric command
    if args.command == "rubric":
        return cmd_rubric(args)

    # Execute the subcommand
    if hasattr(args, "func"):
        return args.func(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
