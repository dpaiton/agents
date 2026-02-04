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
    agents sync                            # fetch/prune, clean merged worktrees, rebase remaining
    agents sync --dry-run                  # preview sync actions without making changes
    agents cost history                    # show historical token usage by day
    agents cost history --pr 18            # filter by PR number
    agents cost log --model claude-sonnet-4-20250514 --input-tokens 1500 --output-tokens 800 --command route

    eco route "Add a login page"           # economy mode: uses smaller, cheaper models
    eco judge --response r.txt --ref ref.txt --rubric code_review  # economy mode

Economy mode can also be enabled explicitly with the --economy flag:
    agents --economy route "Add a login page"

When invoked as ``eco``, economy mode is enabled automatically.
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from orchestration.cost import (
    CostCalculator,
    DailySummary,
    UsageRecord,
    UsageStore,
)


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

    rubric_name = args.rubric
    providers = getattr(args, "provider", None) or []
    model_override = getattr(args, "model", None)
    economy = getattr(args, "economy", False)

    if providers:
        # Use real backends via judge engine
        from orchestration.backends import (
            backend_as_judge_fn,
            create_backend,
        )
        from orchestration.judge import EvaluationCriterion, JudgeEngine

        engine = JudgeEngine()

        # Build rubric criteria from RUBRICS dict
        rubric_def = RUBRICS.get(rubric_name)
        if not rubric_def:
            print(f"Error: Rubric not found: {rubric_name}", file=sys.stderr)
            print(f"Available rubrics: {', '.join(RUBRICS.keys())}", file=sys.stderr)
            return 1

        rubric = [
            EvaluationCriterion(
                name=c["name"],
                description=c["description"],
                scale=(1, 5),
                weight=c["weight"],
            )
            for c in rubric_def["criteria"]
        ]

        judge_fns = []
        for provider in providers:
            try:
                backend = create_backend(
                    provider, model=model_override, economy=economy,
                )
                judge_fns.append(backend_as_judge_fn(backend))
            except ValueError as e:
                print(f"Error creating {provider} backend: {e}", file=sys.stderr)
                return 1

        if len(judge_fns) == 1:
            report = engine.evaluate(
                response=response,
                rubric=rubric,
                reference=reference,
                judge_fn=judge_fns[0],
            )
        else:
            report = engine.multi_model_ensemble(
                response=response,
                rubric=rubric,
                judge_fns=judge_fns,
                reference=reference,
            )

        result = {
            "rubric": rubric_name,
            "score": report.total,
            "confidence": report.confidence,
            "reasoning": report.reasoning,
            "safety_flag": report.safety_flag,
            "criteria": {
                s.criterion.name: {"score": s.score, "feedback": s.reasoning}
                for s in report.scores
            },
            "summary": f"Evaluation using {rubric_name} rubric completed.",
        }
    else:
        # Placeholder evaluation logic when no providers given
        result = {
            "rubric": rubric_name,
            "score": 0.75,  # Placeholder
            "criteria": {
                "correctness": {
                    "score": 0.8,
                    "feedback": "Response addresses the main points.",
                },
                "completeness": {
                    "score": 0.7,
                    "feedback": "Some details could be expanded.",
                },
                "clarity": {
                    "score": 0.75,
                    "feedback": "Well structured and readable.",
                },
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
        "--provider",
        action="append",
        default=[],
        help="LLM provider to use (repeatable: --provider anthropic --provider google)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override model name for all providers",
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
# Subcommand: sync
# -----------------------------------------------------------------------------

def _run_git(*cmd_args: str, cwd: str | None = None) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git", *cmd_args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _parse_worktrees(porcelain_output: str) -> list[dict[str, str]]:
    """Parse ``git worktree list --porcelain`` output into a list of dicts."""
    worktrees: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in porcelain_output.splitlines():
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("branch "):
            current["branch"] = line.split(" ", 1)[1]
        elif line == "bare":
            current["bare"] = "true"
        elif line == "detached":
            current["detached"] = "true"
        elif line == "":
            if current:
                worktrees.append(current)
                current = {}
    if current:
        worktrees.append(current)
    return worktrees


def _detect_default_branch() -> str:
    """Detect the default branch name (e.g. main or master)."""
    rc, out, _ = _run_git("symbolic-ref", "refs/remotes/origin/HEAD", "--short")
    if rc == 0 and "/" in out:
        return out.split("/", 1)[1]
    return "main"


def cmd_sync_comments(args: argparse.Namespace) -> int:
    """Process unresolved GitHub comments on issues and PRs."""
    from orchestration.sync_engine import (
        ActionExecutor,
        CommentFetcher,
        IntentClassifier,
        SyncHistory,
    )

    dry_run = getattr(args, "dry_run", False)
    pr_num = getattr(args, "pr", None)
    issue_num = getattr(args, "issue", None)

    fetcher = CommentFetcher()
    classifier = IntentClassifier()
    executor = ActionExecutor()
    history = SyncHistory()

    # Fetch comments
    if pr_num:
        comments = fetcher.fetch_pr_comments(pr_num)
        comments.extend(fetcher.fetch_pr_review_threads(pr_num))
    elif issue_num:
        comments = fetcher.fetch_issue_comments(issue_num)
    else:
        comments = fetcher.fetch_all_open()

    if not comments:
        print("No unresolved comments found.")
        return 0

    # Filter already-processed comments
    new_comments = [c for c in comments if not history.is_processed(c.id)]
    if not new_comments:
        print("All comments already processed.")
        return 0

    print(f"Found {len(new_comments)} unprocessed comment(s)")

    # Classify and execute
    results = []
    for comment in new_comments:
        classified = classifier.classify(comment)
        result = executor.execute(classified, dry_run=dry_run)
        results.append(result)

        status = "OK" if result.success else "FAIL"
        print(f"  [{status}] {result.intent}: {result.summary}")

        if not dry_run:
            history.record(result)

    # Summary
    success_count = sum(1 for r in results if r.success)
    print(f"\nSync complete: {success_count}/{len(results)} actions succeeded.")
    return 0


def cmd_sync_worktrees(args: argparse.Namespace) -> int:
    """Sync worktrees: fetch/prune, clean up merged branches, rebase remaining."""
    dry_run = args.dry_run
    verbose = args.verbose or dry_run

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    def action(msg: str) -> None:
        print(msg)

    # Step 1: Fetch and prune remote tracking branches
    action("Fetching and pruning remote tracking branches...")
    if not dry_run:
        rc, out, err = _run_git("fetch", "--prune", "origin")
        if rc != 0:
            print(f"Error: git fetch --prune failed: {err}", file=sys.stderr)
            return 1
        if out:
            log(out)
        if err:
            log(err)

    # Step 2: Detect default branch and update local copy
    default_branch = _detect_default_branch()
    log(f"Default branch: {default_branch}")

    # Step 3: List all worktrees
    rc, worktree_output, _ = _run_git("worktree", "list", "--porcelain")
    if rc != 0:
        print("Error: Could not list worktrees", file=sys.stderr)
        return 1

    worktrees = _parse_worktrees(worktree_output)
    if not worktrees:
        action("No worktrees found.")
        return 0

    # Find the worktree on the default branch and update it
    for wt in worktrees:
        branch_ref = wt.get("branch", "")
        if branch_ref == f"refs/heads/{default_branch}":
            action(f"Updating local {default_branch}...")
            if not dry_run:
                rc, out, err = _run_git(
                    "pull", "--ff-only", "origin", default_branch, cwd=wt["path"]
                )
                if rc != 0:
                    print(
                        f"Warning: Could not fast-forward {default_branch}: {err}",
                        file=sys.stderr,
                    )
                else:
                    log(out or "Already up to date.")
            break
    else:
        log(f"No worktree on {default_branch}, skipping local update")

    # Step 4: Separate branch worktrees into stale (remote gone) and active
    branch_worktrees = [
        wt for wt in worktrees
        if "branch" in wt and not wt["branch"].endswith(f"/{default_branch}")
    ]

    if not branch_worktrees:
        action("No branch worktrees to sync.")
        action("Sync complete: everything up to date.")
        return 0

    log(f"Found {len(branch_worktrees)} branch worktree(s)")

    stale: list[tuple[dict[str, str], str]] = []
    active: list[tuple[dict[str, str], str]] = []

    for wt in branch_worktrees:
        branch_name = wt["branch"].replace("refs/heads/", "")
        remote_ref = f"refs/remotes/origin/{branch_name}"
        rc, _, _ = _run_git("rev-parse", "--verify", remote_ref)
        if rc != 0:
            stale.append((wt, branch_name))
        else:
            active.append((wt, branch_name))

    # Step 5: Remove stale worktrees and delete their local branches
    for wt, branch_name in stale:
        action(f"Removing worktree (branch merged/deleted): {wt['path']} [{branch_name}]")
        if not dry_run:
            rc, _, err = _run_git("worktree", "remove", "--force", wt["path"])
            if rc != 0:
                print(f"  Warning: worktree remove failed: {err}", file=sys.stderr)

            rc, _, err = _run_git("branch", "-D", branch_name)
            if rc != 0:
                print(f"  Warning: branch delete failed: {err}", file=sys.stderr)
            else:
                log(f"  Deleted branch {branch_name}")

    # Step 6: Rebase active worktree branches onto origin/<default>
    rebase_target = f"origin/{default_branch}"
    rebased: list[tuple[dict[str, str], str]] = []

    for wt, branch_name in active:
        action(f"Rebasing {branch_name} onto {rebase_target}...")
        if not dry_run:
            rc, out, err = _run_git("rebase", rebase_target, cwd=wt["path"])
            if rc != 0:
                print(f"  Error: rebase failed for {branch_name}: {err}", file=sys.stderr)
                print(f"  Aborting rebase for {branch_name}", file=sys.stderr)
                _run_git("rebase", "--abort", cwd=wt["path"])
                continue
            log(f"  {out or 'Already up to date.'}")
        rebased.append((wt, branch_name))

    # Step 7: Force-push rebased branches
    if not args.no_push:
        for wt, branch_name in rebased:
            action(f"Pushing {branch_name}...")
            if not dry_run:
                rc, out, err = _run_git(
                    "push", "--force-with-lease", "origin", branch_name, cwd=wt["path"]
                )
                if rc != 0:
                    print(f"  Warning: push failed for {branch_name}: {err}", file=sys.stderr)
                else:
                    log(err or out or "Done.")
    elif rebased:
        log("Skipping push (--no-push)")

    # Summary
    parts = []
    if stale:
        parts.append(f"{len(stale)} merged worktree(s) removed")
    if rebased:
        parts.append(f"{len(rebased)} branch(es) rebased")
    if not parts:
        parts.append("everything up to date")

    action(f"Sync complete: {', '.join(parts)}.")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    """Handle sync command, dispatching to subcommands or running both."""
    sync_command = getattr(args, "sync_command", None)
    if sync_command == "worktrees":
        return cmd_sync_worktrees(args)
    if sync_command == "comments":
        return cmd_sync_comments(args)
    # No subcommand — run both comments then worktrees
    rc = cmd_sync_comments(args)
    if not hasattr(args, "verbose"):
        args.verbose = False
    if not hasattr(args, "no_push"):
        args.no_push = False
    print()
    wt_rc = cmd_sync_worktrees(args)
    return rc or wt_rc


def setup_sync_parser(subparsers: argparse._SubParsersAction) -> None:
    """Set up the sync subcommand parser with nested subcommands."""
    parser = subparsers.add_parser(
        "sync",
        help="Process comments or sync worktrees",
        description=(
            "Process unresolved GitHub comments (default) or synchronize worktrees. "
            "Use 'sync' or 'sync comments' to process comments, "
            "'sync worktrees' to manage git worktrees."
        ),
    )

    # Top-level flags for comment processing (available on bare 'eco sync')
    parser.add_argument(
        "--pr",
        type=int,
        default=None,
        help="Process comments on this PR only",
    )
    parser.add_argument(
        "--issue",
        type=int,
        default=None,
        help="Process comments on this issue only",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show plan without executing",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        default=False,
        help="Process comments sequentially instead of in parallel",
    )

    sync_subparsers = parser.add_subparsers(
        dest="sync_command",
        metavar="SUBCOMMAND",
    )

    # sync comments
    comments_parser = sync_subparsers.add_parser(
        "comments",
        help="Process unresolved GitHub comments (default)",
    )
    comments_parser.add_argument(
        "--pr",
        type=int,
        default=None,
        help="Process comments on this PR only",
    )
    comments_parser.add_argument(
        "--issue",
        type=int,
        default=None,
        help="Process comments on this issue only",
    )
    comments_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show plan without executing",
    )
    comments_parser.add_argument(
        "--sequential",
        action="store_true",
        default=False,
        help="Process comments sequentially instead of in parallel",
    )

    # sync worktrees
    worktrees_parser = sync_subparsers.add_parser(
        "worktrees",
        help="Fetch/prune, clean up merged worktrees, rebase remaining",
        description=(
            "Synchronize the local repository and all worktrees with the remote. "
            "Fetches and prunes remote tracking branches, removes worktrees whose "
            "remote branches have been deleted (merged PRs), rebases remaining "
            "worktree branches onto the default branch, and force-pushes the "
            "rebased branches."
        ),
    )
    worktrees_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be done without making changes (implies --verbose)",
    )
    worktrees_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Show detailed output",
    )
    worktrees_parser.add_argument(
        "--no-push",
        action="store_true",
        default=False,
        help="Skip force-pushing rebased branches",
    )


# -----------------------------------------------------------------------------
# Subcommand: run
# -----------------------------------------------------------------------------

def cmd_run(args: argparse.Namespace) -> int:
    """Execute a task through the orchestration pipeline."""
    from orchestration.config import load_config
    from orchestration.execution import ExecutionEngine

    task = read_input(args)
    if not task:
        print("Error: No task description provided", file=sys.stderr)
        print(
            'Usage: eco run "task description" or eco run --issue 42',
            file=sys.stderr,
        )
        return 1

    economy = getattr(args, "economy", False)
    config = load_config()
    engine = ExecutionEngine(config=config, economy=economy)

    issue = getattr(args, "issue", None)
    pr = getattr(args, "pr", None)
    dry_run = getattr(args, "dry_run", False)

    run = engine.plan(task, issue=issue, pr=pr)

    if dry_run:
        print("Execution plan (dry run):")
        print(f"  Task:      {run.task}")
        print(f"  Type:      {run.task_type}")
        print(f"  Model:     {run.model}")
        print(f"  Agents:    {' → '.join(run.agent_sequence)}")
        print(f"  Budget:    {config.token_budget:,} tokens")
        run = engine.execute(run, dry_run=True)
        return 0

    print(f"Running: {run.task}")
    print(f"  Type:   {run.task_type}")
    print(f"  Model:  {run.model}")
    print(f"  Agents: {' → '.join(run.agent_sequence)}")
    print()

    run = engine.execute(run)

    if run.status == "complete":
        total = run.token_usage["input"] + run.token_usage["output"]
        print(f"Complete: {total:,} tokens used")
    elif run.status == "aborted":
        print(f"Aborted: {run.error}", file=sys.stderr)
        return 1
    elif run.status == "failed":
        print(f"Failed: {run.error}", file=sys.stderr)
        return 1

    return 0


def setup_run_parser(subparsers: argparse._SubParsersAction) -> None:
    """Set up the run subcommand parser."""
    parser = subparsers.add_parser(
        "run",
        help="Execute a task through the orchestration pipeline",
        description=(
            "Route and execute a task through the agent pipeline. "
            "The task is classified, a model is selected, and agents "
            "are invoked in sequence."
        ),
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Task description (can also be provided via stdin)",
    )
    parser.add_argument(
        "--issue",
        type=int,
        default=None,
        help="Act on a specific GitHub issue",
    )
    parser.add_argument(
        "--pr",
        type=int,
        default=None,
        help="Act on a specific GitHub PR",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        default=False,
        help="Review a PR (use with --pr)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show execution plan without running",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.set_defaults(func=cmd_run)


# -----------------------------------------------------------------------------
# Subcommand: deploy
# -----------------------------------------------------------------------------

def cmd_deploy(args: argparse.Namespace) -> int:
    """Deploy a long-running agent on an issue or PR."""
    from orchestration.config import load_config
    from orchestration.execution import DeployEngine

    issue = getattr(args, "issue", None)
    pr = getattr(args, "pr", None)
    watch = getattr(args, "watch", False)
    dry_run = getattr(args, "dry_run", False)
    economy = getattr(args, "economy", False)

    if not issue and not pr:
        print("Error: Must specify --issue or --pr", file=sys.stderr)
        print("Usage: eco deploy --issue 42 [--watch]", file=sys.stderr)
        return 1

    config = load_config()
    deploy = DeployEngine(config=config, economy=economy)

    if watch:
        try:
            deploy.watch(issue=issue, pr=pr, dry_run=dry_run)
        except KeyboardInterrupt:
            print("\nStopped.")
        return 0

    target = f"issue #{issue}" if issue else f"PR #{pr}"
    print(f"Deploying agent on {target}...")
    result = deploy.deploy_once(issue=issue, pr=pr, dry_run=dry_run)

    new = result["new_comments"]
    if new == 0:
        print("No new comments to process.")
    else:
        success = sum(1 for a in result["actions"] if a.get("success"))
        print(f"Processed {success}/{new} comment(s)")

    return 0


def setup_deploy_parser(subparsers: argparse._SubParsersAction) -> None:
    """Set up the deploy subcommand parser."""
    parser = subparsers.add_parser(
        "deploy",
        help="Deploy a long-running agent on an issue or PR",
        description=(
            "Read latest comments on an issue or PR and act on them. "
            "Use --watch to continuously poll for new comments."
        ),
    )
    parser.add_argument(
        "--issue",
        type=int,
        default=None,
        help="Deploy on this GitHub issue",
    )
    parser.add_argument(
        "--pr",
        type=int,
        default=None,
        help="Deploy on this GitHub PR",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        default=False,
        help="Continuously poll for new comments",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show plan without executing",
    )
    parser.set_defaults(func=cmd_deploy)


# -----------------------------------------------------------------------------
# Subcommand: status
# -----------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> int:
    """Show running agents, token usage, and model breakdown."""
    from orchestration.config import load_config
    from orchestration.execution import ExecutionEngine

    config = load_config()
    engine = ExecutionEngine(config=config)

    if getattr(args, "all", False):
        runs = engine.get_all_runs()
    else:
        runs = engine.get_active_runs()

    if not runs:
        label = "runs" if getattr(args, "all", False) else "active agents"
        print(f"No {label}.")
        return 0

    fmt = args.format
    if fmt == "json":
        from dataclasses import asdict
        data = [asdict(r) for r in runs]
        print(json.dumps(data, indent=2))
        return 0

    # Text table
    print(f"{'Run ID':<14} {'Task Type':<14} {'Model':<30} {'Tokens':>10}  Status")
    print(f"{'-' * 12}  {'-' * 12}  {'-' * 28}  {'-' * 10}  {'-' * 8}")

    for run in runs:
        total = run.token_usage["input"] + run.token_usage["output"]
        print(
            f"{run.run_id:<14}"
            f"{run.task_type:<14}"
            f"{run.model:<30}"
            f"{total:>10,}  "
            f"{run.status}"
        )

    return 0


def setup_status_parser(subparsers: argparse._SubParsersAction) -> None:
    """Set up the status subcommand parser."""
    parser = subparsers.add_parser(
        "status",
        help="Show running agents and token usage",
        description="Display active agents, their models, token usage, and status.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        default=False,
        help="Show all runs, not just active ones",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.set_defaults(func=cmd_status)


# -----------------------------------------------------------------------------
# Subcommand: test
# -----------------------------------------------------------------------------

def cmd_test(args: argparse.Namespace) -> int:
    """Run tests via pytest."""
    cmd = ["uv", "run", "pytest"]

    if getattr(args, "integration", False):
        cmd.extend(["-m", "integration"])

    cmd.append("-v")

    # Pass through any extra args
    extra = getattr(args, "pytest_args", [])
    cmd.extend(extra)

    result = subprocess.run(cmd)
    return result.returncode


def setup_test_parser(subparsers: argparse._SubParsersAction) -> None:
    """Set up the test subcommand parser."""
    parser = subparsers.add_parser(
        "test",
        help="Run tests (shortcut for uv run pytest)",
        description="Run the test suite. Use --integration for integration tests only.",
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests only (pytest -m integration)",
    )
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Additional arguments passed to pytest",
    )
    parser.set_defaults(func=cmd_test)


# -----------------------------------------------------------------------------
# Subcommand: cost
# -----------------------------------------------------------------------------

def _print_history_table(summaries: list[DailySummary]) -> None:
    """Print a formatted text table of daily usage summaries."""
    print("Token Usage History")
    print("===================")
    print()

    header = (
        f"{'Date':<12} {'Input Tokens':>13}  {'Output Tokens':>14}  "
        f"{'Est. Cost':>10}  {'Records':>7}  Models"
    )
    print(header)
    print(
        f"{'-' * 10}  {'-' * 13}  {'-' * 14}  "
        f"{'-' * 10}  {'-' * 7}  {'-' * 6}"
    )

    for s in summaries:
        models_str = ", ".join(s.models)
        print(
            f"{s.date:<12}"
            f"{s.total_input_tokens:>13,}  "
            f"{s.total_output_tokens:>14,}  "
            f"${s.estimated_cost_usd:>9.4f}  "
            f"{s.record_count:>7}   "
            f"{models_str}"
        )

    total_input = sum(s.total_input_tokens for s in summaries)
    total_output = sum(s.total_output_tokens for s in summaries)
    total_cost = sum(s.estimated_cost_usd for s in summaries)
    total_records = sum(s.record_count for s in summaries)

    print()
    print(
        f"{'-' * 10}  {'-' * 13}  {'-' * 14}  "
        f"{'-' * 10}  {'-' * 7}"
    )
    print(
        f"{'Total':<12}"
        f"{total_input:>13,}  "
        f"{total_output:>14,}  "
        f"${total_cost:>9.4f}  "
        f"{total_records:>7}"
    )


def cmd_cost_history(args: argparse.Namespace) -> int:
    """Show historical token usage aggregated by day."""
    store = UsageStore()
    records = store.read_filtered(
        pr=getattr(args, "pr", None),
        issue=getattr(args, "issue", None),
        since=getattr(args, "since", None),
        until=getattr(args, "until", None),
        command=getattr(args, "command_filter", None),
    )

    if not records:
        print("No usage records found.")
        return 0

    summaries = CostCalculator.summarize_by_day(records)

    if args.format == "json":
        data = [asdict(s) for s in summaries]
        grand = {
            "total_input_tokens": sum(s.total_input_tokens for s in summaries),
            "total_output_tokens": sum(s.total_output_tokens for s in summaries),
            "total_cost_usd": round(sum(s.estimated_cost_usd for s in summaries), 4),
            "total_records": sum(s.record_count for s in summaries),
        }
        print(json.dumps({"days": data, "total": grand}, indent=2))
    else:
        _print_history_table(summaries)

    return 0


def cmd_cost_log(args: argparse.Namespace) -> int:
    """Record a token usage event."""
    record = UsageRecord(
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        model=args.model,
        input_tokens=args.input_tokens,
        output_tokens=args.output_tokens,
        command=args.cmd_name,
        pr=getattr(args, "pr", None),
        issue=getattr(args, "issue", None),
        session_id=getattr(args, "session_id", None),
    )

    store = UsageStore()
    store.append(record)

    cost = CostCalculator.estimate_record_cost(record)

    result = {
        "status": "recorded",
        "estimated_cost_usd": cost,
        "model": record.model,
        "input_tokens": record.input_tokens,
        "output_tokens": record.output_tokens,
    }

    print(format_output(result, args.format))
    return 0


def cmd_cost_estimate(args: argparse.Namespace) -> int:
    """Estimate token cost for a task before executing."""
    from orchestration.config import load_config
    from orchestration.execution import ExecutionEngine

    task = read_input(args)
    if not task:
        print("Error: No task description provided", file=sys.stderr)
        return 1

    economy = getattr(args, "economy", False)
    config = load_config()
    engine = ExecutionEngine(config=config, economy=economy)

    issue = getattr(args, "issue", None)
    pr = getattr(args, "pr", None)
    estimate = engine.estimate_cost(task, issue=issue, pr=pr)

    if args.format == "json":
        print(json.dumps(estimate, indent=2))
    else:
        print(f"Cost estimate for: {estimate['task']}")
        print(f"  Task type:     {estimate['task_type']}")
        print(f"  Model:         {estimate['model']}")
        print(f"  Agents:        {' → '.join(estimate['agent_sequence'])}")
        print(f"  Est. input:    {estimate['estimated_input_tokens']:,} tokens")
        print(f"  Est. output:   {estimate['estimated_output_tokens']:,} tokens")
        print(f"  Est. cost:     ${estimate['estimated_cost_usd']:.4f}")
        print(f"  Token budget:  {estimate['token_budget']:,}")

    return 0


def cmd_cost(args: argparse.Namespace) -> int:
    """Handle cost command without subcommand."""
    if not args.cost_command:
        print(
            "Error: cost requires a subcommand (estimate, history, or log)",
            file=sys.stderr,
        )
        print(
            "Usage: eco cost estimate <task> | eco cost history | eco cost log --model ...",
            file=sys.stderr,
        )
        return 1
    return args.func(args)


def setup_cost_parser(subparsers: argparse._SubParsersAction) -> None:
    """Set up the cost subcommand parser."""
    parser = subparsers.add_parser(
        "cost",
        help="Track and display token usage costs",
        description="View historical token usage and estimated costs, or record usage events.",
    )

    cost_subparsers = parser.add_subparsers(
        dest="cost_command",
        metavar="COMMAND",
    )

    # cost estimate
    estimate_parser = cost_subparsers.add_parser(
        "estimate",
        help="Estimate token cost for a task before execution",
    )
    estimate_parser.add_argument(
        "input",
        nargs="?",
        help="Task description (can also be provided via stdin)",
    )
    estimate_parser.add_argument("--pr", type=int, help="Estimate for syncing a PR")
    estimate_parser.add_argument("--issue", type=int, help="Estimate for an issue")
    estimate_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    estimate_parser.set_defaults(func=cmd_cost_estimate)

    # cost history
    history_parser = cost_subparsers.add_parser(
        "history",
        help="Show historical token usage by day",
    )
    history_parser.add_argument("--pr", type=int, help="Filter by PR number")
    history_parser.add_argument("--issue", type=int, help="Filter by issue number")
    history_parser.add_argument("--since", help="Start date (YYYY-MM-DD)")
    history_parser.add_argument("--until", help="End date (YYYY-MM-DD)")
    history_parser.add_argument(
        "--command", dest="command_filter", help="Filter by command name",
    )
    history_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    history_parser.set_defaults(func=cmd_cost_history)

    # cost log
    log_parser = cost_subparsers.add_parser(
        "log",
        help="Record a token usage event",
    )
    log_parser.add_argument("--model", required=True, help="Model identifier")
    log_parser.add_argument(
        "--input-tokens", type=int, required=True, help="Input token count",
    )
    log_parser.add_argument(
        "--output-tokens", type=int, required=True, help="Output token count",
    )
    log_parser.add_argument(
        "--command", required=True, dest="cmd_name",
        help="Command that generated this usage",
    )
    log_parser.add_argument("--pr", type=int, help="Associated PR number")
    log_parser.add_argument("--issue", type=int, help="Associated issue number")
    log_parser.add_argument("--session-id", help="Session identifier")
    log_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    log_parser.set_defaults(func=cmd_cost_log)


# -----------------------------------------------------------------------------
# Subcommand: remote
# -----------------------------------------------------------------------------

def cmd_remote_run(args: argparse.Namespace) -> int:
    """Launch a GCP instance for an agent task."""
    from orchestration.remote import get_current_branch, get_repo_url, launch_instance

    task = read_input(args)
    if not task and not args.issue and not args.pr:
        print("Error: Provide a task description, --issue, or --pr", file=sys.stderr)
        return 1

    if not task:
        task = f"Process issue #{args.issue}" if args.issue else f"Process PR #{args.pr}"

    repo = get_repo_url()
    if not repo:
        print("Error: Could not detect git remote URL", file=sys.stderr)
        return 1

    branch = getattr(args, "branch", None) or get_current_branch()
    project = getattr(args, "project", None)
    zone = getattr(args, "zone", "us-central1-a")
    machine_type = getattr(args, "machine_type", "e2-standard-2")
    timeout = getattr(args, "timeout", 4)
    deploy = getattr(args, "deploy", False)
    dry_run = getattr(args, "dry_run", False)
    template = getattr(args, "template", "agents-task-template")

    result = launch_instance(
        task,
        repo=repo,
        branch=branch,
        issue=args.issue,
        pr=args.pr,
        project=project,
        zone=zone,
        machine_type=machine_type,
        timeout_hours=timeout,
        deploy_mode=deploy,
        template=template,
        dry_run=dry_run,
    )

    if result.get("status") == "FAILED":
        print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
        return 1

    if dry_run:
        print("Dry run — would execute:")
        print(f"  {result.get('command', '')}")
    else:
        print(f"Instance launched: {result['name']}")
        print(f"  Zone: {result['zone']}")
        print(f"  Machine: {result['machine_type']}")
        print(f"  Task: {result['task']}")

    print("\nMonitor with: eco remote status")
    print(f"Stream logs:  eco remote logs {result['name']}")
    print(f"Stop:         eco remote stop {result['name']}")

    return 0


def cmd_remote_status(args: argparse.Namespace) -> int:
    """List running remote agent instances."""
    from orchestration.remote import list_instances

    project = getattr(args, "project", None)
    instances = list_instances(project=project)

    if not instances:
        print("No remote agent instances found.")
        return 0

    if args.format == "json":
        from dataclasses import asdict as _asdict
        data = [_asdict(i) for i in instances]
        print(json.dumps(data, indent=2))
        return 0

    print(f"{'Instance':<30} {'Zone':<18} {'Status':<12} {'Machine':<16} {'Task'}")
    print(f"{'-'*28}  {'-'*16}  {'-'*10}  {'-'*14}  {'-'*20}")
    for inst in instances:
        task_label = inst.task[:40] if inst.task else ""
        if inst.issue:
            task_label = f"issue #{inst.issue}"
        elif inst.pr:
            task_label = f"PR #{inst.pr}"
        print(
            f"{inst.name:<30} {inst.zone:<18} {inst.status:<12} "
            f"{inst.machine_type:<16} {task_label}"
        )

    return 0


def cmd_remote_logs(args: argparse.Namespace) -> int:
    """Stream logs from a remote agent instance."""
    from orchestration.remote import stream_logs

    instance = args.instance
    zone = getattr(args, "zone", "us-central1-a")
    project = getattr(args, "project", None)
    follow = not getattr(args, "no_follow", False)

    print(f"Streaming logs from {instance}...")
    print("(Press Ctrl+C to stop)\n")

    try:
        proc = stream_logs(
            instance,
            zone=zone,
            project=project,
            follow=follow,
        )
        if proc.stdout:
            for line in proc.stdout:
                print(line, end="")
        proc.wait()
    except KeyboardInterrupt:
        print("\nStopped log streaming.")

    return 0


def cmd_remote_stop(args: argparse.Namespace) -> int:
    """Stop a remote agent instance."""
    from orchestration.remote import stop_instance

    instance = args.instance
    zone = getattr(args, "zone", "us-central1-a")
    project = getattr(args, "project", None)

    print(f"Stopping instance {instance}...")
    result = stop_instance(instance, zone=zone, project=project)

    if result.get("status") == "FAILED":
        print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
        return 1

    print(f"Instance {instance} deleted.")
    return 0


def cmd_remote(args: argparse.Namespace) -> int:
    """Handle remote command, dispatching to subcommands."""
    remote_command = getattr(args, "remote_command", None)
    if not remote_command:
        print("Error: remote requires a subcommand (run, status, logs, stop)", file=sys.stderr)
        print("Usage: eco remote run <task> | eco remote status | eco remote logs <instance> | eco remote stop <instance>", file=sys.stderr)
        return 1
    return args.func(args)


def setup_remote_parser(subparsers: argparse._SubParsersAction) -> None:
    """Set up the remote subcommand parser."""
    parser = subparsers.add_parser(
        "remote",
        help="Manage remote GCP agent instances",
        description=(
            "Launch, monitor, and manage agent tasks running on GCP Compute instances. "
            "Requires gcloud CLI configured with appropriate project and credentials."
        ),
    )

    remote_subparsers = parser.add_subparsers(
        dest="remote_command",
        metavar="SUBCOMMAND",
    )

    # remote run
    run_parser = remote_subparsers.add_parser(
        "run",
        help="Launch a GCP instance for an agent task",
    )
    run_parser.add_argument(
        "input",
        nargs="?",
        help="Task description (can also be provided via stdin)",
    )
    run_parser.add_argument("--issue", type=int, help="GitHub issue number")
    run_parser.add_argument("--pr", type=int, help="GitHub PR number")
    run_parser.add_argument("--branch", help="Git branch to checkout (default: current)")
    run_parser.add_argument(
        "--machine-type",
        default="e2-standard-2",
        help="GCP machine type (default: e2-standard-2)",
    )
    run_parser.add_argument(
        "--zone",
        default="us-central1-a",
        help="GCP zone (default: us-central1-a)",
    )
    run_parser.add_argument("--project", help="GCP project ID")
    run_parser.add_argument(
        "--timeout",
        type=int,
        default=4,
        help="Max runtime in hours (default: 4)",
    )
    run_parser.add_argument(
        "--deploy",
        action="store_true",
        default=False,
        help="Use deploy mode (poll for comments) instead of single run",
    )
    run_parser.add_argument(
        "--template",
        default="agents-task-template",
        help="Instance template name or self-link from Terraform output (default: agents-task-template)",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be launched without actually creating the instance",
    )
    run_parser.set_defaults(func=cmd_remote_run)

    # remote status
    status_parser = remote_subparsers.add_parser(
        "status",
        help="List running remote agent instances",
    )
    status_parser.add_argument("--project", help="GCP project ID")
    status_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    status_parser.set_defaults(func=cmd_remote_status)

    # remote logs
    logs_parser = remote_subparsers.add_parser(
        "logs",
        help="Stream logs from a remote agent instance",
    )
    logs_parser.add_argument("instance", help="Instance name")
    logs_parser.add_argument(
        "--zone",
        default="us-central1-a",
        help="GCP zone (default: us-central1-a)",
    )
    logs_parser.add_argument("--project", help="GCP project ID")
    logs_parser.add_argument(
        "--no-follow",
        action="store_true",
        default=False,
        help="Print logs and exit instead of streaming",
    )
    logs_parser.set_defaults(func=cmd_remote_logs)

    # remote stop
    stop_parser = remote_subparsers.add_parser(
        "stop",
        help="Stop a remote agent instance",
    )
    stop_parser.add_argument("instance", help="Instance name")
    stop_parser.add_argument(
        "--zone",
        default="us-central1-a",
        help="GCP zone (default: us-central1-a)",
    )
    stop_parser.add_argument("--project", help="GCP project ID")
    stop_parser.set_defaults(func=cmd_remote_stop)


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
    setup_sync_parser(subparsers)
    setup_run_parser(subparsers)
    setup_deploy_parser(subparsers)
    setup_status_parser(subparsers)
    setup_test_parser(subparsers)
    setup_cost_parser(subparsers)
    setup_remote_parser(subparsers)

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

    # Special handling for commands with nested subcommands
    if args.command == "rubric":
        return cmd_rubric(args)

    if args.command == "cost":
        return cmd_cost(args)

    if args.command == "sync":
        return cmd_sync(args)

    if args.command == "remote":
        return cmd_remote(args)

    # Execute the subcommand
    if hasattr(args, "func"):
        return args.func(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
