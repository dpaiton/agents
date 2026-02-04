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
    """Handle sync command, dispatching to subcommands.

    Bare ``eco sync`` runs both comment processing and worktree rebase.
    Explicit subcommands (``eco sync comments``, ``eco sync worktrees``)
    run only their respective part.
    """
    sync_command = getattr(args, "sync_command", None)

    if sync_command == "worktrees":
        return cmd_sync_worktrees(args)

    if sync_command == "comments":
        return cmd_sync_comments(args)

    # No subcommand — run both: comments first, then worktree rebase
    rc = cmd_sync_comments(args)

    # Provide defaults for worktree-specific flags
    if not hasattr(args, "verbose"):
        args.verbose = False
    if not hasattr(args, "no_push"):
        args.no_push = False

    print()  # visual separator
    wt_rc = cmd_sync_worktrees(args)
    return rc or wt_rc


def setup_sync_parser(subparsers: argparse._SubParsersAction) -> None:
    """Set up the sync subcommand parser with nested subcommands."""
    parser = subparsers.add_parser(
        "sync",
        help="Process comments and sync worktrees",
        description=(
            "Process unresolved GitHub comments and synchronize worktrees. "
            "Bare 'sync' runs both. Use 'sync comments' or 'sync worktrees' "
            "to run only one part."
        ),
    )

    # Top-level flags (available on bare 'eco sync')
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
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Show detailed output for worktree sync",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        default=False,
        help="Skip force-pushing rebased branches",
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


def cmd_cost(args: argparse.Namespace) -> int:
    """Handle cost command without subcommand."""
    if not args.cost_command:
        print("Error: cost requires a subcommand (history or log)", file=sys.stderr)
        print("Usage: agents cost history | agents cost log --model ...", file=sys.stderr)
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
    setup_cost_parser(subparsers)

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

    # Execute the subcommand
    if hasattr(args, "func"):
        return args.func(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
