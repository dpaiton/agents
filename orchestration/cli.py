"""Command-line interface for the orchestration framework."""

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="eco",
        description="Orchestration CLI for multi-agent workflows.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("sync", help="Sync configuration and dependencies")
    subparsers.add_parser("run", help="Run an orchestration pipeline")
    subparsers.add_parser("deploy", help="Deploy agents to remote infrastructure")
    subparsers.add_parser("route", help="Classify a task and determine agent sequence")
    subparsers.add_parser("judge", help="Run LLM-as-judge evaluation")
    subparsers.add_parser("review", help="Run automated code review")
    subparsers.add_parser("rubric", help="Manage evaluation rubrics")
    subparsers.add_parser("cost", help="Estimate or report pipeline costs")
    subparsers.add_parser("status", help="Show status of running pipelines")
    subparsers.add_parser("test", help="Run the test suite")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    print(f"Command '{args.command}' is not yet implemented.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
