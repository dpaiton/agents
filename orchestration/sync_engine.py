"""Comment-driven sync engine for GitHub issue and PR processing.

This module implements ``eco sync`` — the primary interaction model.  It fetches
unresolved GitHub comments, classifies intent via deterministic pattern matching
(with optional LLM fallback), dispatches to action handlers, and persists sync
history.

Design Principles:
- P5 Deterministic Infrastructure: Pattern matching first, LLM only as fallback.
- P6 Code Before Prompts: ``gh`` CLI for all GitHub interactions.
- P8 UNIX Philosophy: Composable classes, text interfaces.
- P10 CLI as Interface: All actions via ``gh`` / ``git`` subprocess calls.
- P16 Permission to Fail: Actions that fail are logged, not fatal.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class CommentIntent(Enum):
    """Classified intent of a GitHub comment."""

    EDIT_ISSUE = "edit_issue"
    CHANGE_CODE = "change_code"
    UPDATE_PR_DESC = "update_pr_desc"
    REPLY = "reply"
    CLARIFY = "clarify"
    CREATE_ISSUE = "create_issue"

    def __str__(self) -> str:
        return self.value


@dataclass
class GitHubComment:
    """A GitHub comment from an issue or PR."""

    id: str
    body: str
    author: str
    created_at: str
    pr: Optional[int] = None
    issue: Optional[int] = None
    thread_id: Optional[str] = None
    path: Optional[str] = None
    line: Optional[int] = None


@dataclass
class ClassifiedComment:
    """A comment with its classified intent."""

    comment: GitHubComment
    intent: CommentIntent
    confidence: float
    pattern_matched: bool


@dataclass
class ActionResult:
    """Result of executing an action for a comment."""

    comment_id: str
    intent: CommentIntent
    success: bool
    summary: str
    error: Optional[str] = None


@dataclass
class SyncRun:
    """Record of a single sync invocation."""

    timestamp: str
    results: list[ActionResult]
    dry_run: bool


# ---------------------------------------------------------------------------
# CommentFetcher — retrieves comments via ``gh`` CLI
# ---------------------------------------------------------------------------


def _run_gh(*args: str) -> tuple[int, str, str]:
    """Run a ``gh`` CLI command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class CommentFetcher:
    """Fetches GitHub comments using the ``gh`` CLI."""

    def __init__(self, repo: Optional[str] = None) -> None:
        self.repo = repo or os.environ.get("GITHUB_REPO", "")

    def _repo_args(self) -> list[str]:
        if self.repo:
            return ["--repo", self.repo]
        return []

    def fetch_pr_review_threads(self, pr: int) -> list[GitHubComment]:
        """Fetch review thread comments on a PR via GraphQL."""
        query = """
        query($owner: String!, $repo: String!, $pr: Int!) {
          repository(owner: $owner, name: $repo) {
            pullRequest(number: $pr) {
              reviewThreads(first: 100) {
                nodes {
                  id
                  isResolved
                  comments(first: 10) {
                    nodes {
                      id
                      body
                      author { login }
                      createdAt
                      path
                      line
                    }
                  }
                }
              }
            }
          }
        }
        """
        if not self.repo or "/" not in self.repo:
            return []

        owner, repo_name = self.repo.split("/", 1)
        rc, out, err = _run_gh(
            "api", "graphql",
            "-f", f"query={query}",
            "-f", f"owner={owner}",
            "-f", f"repo={repo_name}",
            "-F", f"pr={pr}",
        )
        if rc != 0:
            return []

        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return []

        comments: list[GitHubComment] = []
        threads = (
            data.get("data", {})
            .get("repository", {})
            .get("pullRequest", {})
            .get("reviewThreads", {})
            .get("nodes", [])
        )
        for thread in threads:
            if thread.get("isResolved"):
                continue
            for node in thread.get("comments", {}).get("nodes", []):
                comments.append(
                    GitHubComment(
                        id=node["id"],
                        body=node.get("body", ""),
                        author=node.get("author", {}).get("login", "unknown"),
                        created_at=node.get("createdAt", ""),
                        pr=pr,
                        thread_id=thread["id"],
                        path=node.get("path"),
                        line=node.get("line"),
                    )
                )
        return comments

    def fetch_pr_comments(self, pr: int) -> list[GitHubComment]:
        """Fetch top-level comments on a PR."""
        rc, out, err = _run_gh(
            "pr", "view", str(pr),
            "--json", "comments",
            *self._repo_args(),
        )
        if rc != 0:
            return []

        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return []

        comments: list[GitHubComment] = []
        for c in data.get("comments", []):
            comments.append(
                GitHubComment(
                    id=c.get("id", ""),
                    body=c.get("body", ""),
                    author=c.get("author", {}).get("login", "unknown"),
                    created_at=c.get("createdAt", ""),
                    pr=pr,
                )
            )
        return comments

    def fetch_issue_comments(self, issue: int) -> list[GitHubComment]:
        """Fetch comments on an issue."""
        rc, out, err = _run_gh(
            "issue", "view", str(issue),
            "--json", "comments",
            *self._repo_args(),
        )
        if rc != 0:
            return []

        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return []

        comments: list[GitHubComment] = []
        for c in data.get("comments", []):
            comments.append(
                GitHubComment(
                    id=c.get("id", ""),
                    body=c.get("body", ""),
                    author=c.get("author", {}).get("login", "unknown"),
                    created_at=c.get("createdAt", ""),
                    issue=issue,
                )
            )
        return comments

    def fetch_all_open(self) -> list[GitHubComment]:
        """Fetch comments from all open PRs and issues."""
        comments: list[GitHubComment] = []

        # Fetch open PRs
        rc, out, _ = _run_gh(
            "pr", "list", "--json", "number", "--state", "open",
            *self._repo_args(),
        )
        if rc == 0:
            try:
                prs = json.loads(out)
                for pr in prs:
                    num = pr.get("number")
                    if num:
                        comments.extend(self.fetch_pr_comments(num))
                        comments.extend(self.fetch_pr_review_threads(num))
            except json.JSONDecodeError:
                pass

        # Fetch open issues
        rc, out, _ = _run_gh(
            "issue", "list", "--json", "number", "--state", "open",
            *self._repo_args(),
        )
        if rc == 0:
            try:
                issues = json.loads(out)
                for issue in issues:
                    num = issue.get("number")
                    if num:
                        comments.extend(self.fetch_issue_comments(num))
            except json.JSONDecodeError:
                pass

        return comments


# ---------------------------------------------------------------------------
# IntentClassifier — deterministic pattern matching, LLM fallback
# ---------------------------------------------------------------------------


class IntentClassifier:
    """Classifies comment intent using pattern matching with optional LLM fallback."""

    INTENT_PATTERNS: dict[CommentIntent, list[re.Pattern[str]]] = {
        CommentIntent.EDIT_ISSUE: [
            re.compile(r"\b(update|edit|change|modify)\s+(the\s+)?(issue|description|body)\b", re.I),
            re.compile(r"\b(issue\s+body|issue\s+description)\b", re.I),
        ],
        CommentIntent.CHANGE_CODE: [
            re.compile(r"\b(fix|implement|add|remove|refactor|change|update)\s+(the\s+)?(code|function|method|class|file|module|test)\b", re.I),
            re.compile(r"\b(code\s+change|pull\s+request\s+change)\b", re.I),
            re.compile(r"\b(push|commit)\s+(a\s+)?(fix|change|update)\b", re.I),
        ],
        CommentIntent.UPDATE_PR_DESC: [
            re.compile(r"\b(update|edit|change|modify)\s+(the\s+)?(pr|pull\s+request)\s+(description|body|summary)\b", re.I),
            re.compile(r"\bpr\s+description\b", re.I),
        ],
        CommentIntent.REPLY: [
            re.compile(r"\b(reply|respond|answer)\b", re.I),
            re.compile(r"^\s*@\w+", re.I),
            re.compile(r"\bthanks\b|\bthank\s+you\b|\blgtm\b", re.I),
        ],
        CommentIntent.CREATE_ISSUE: [
            re.compile(r"\b(create|open|file|new)\s+(an?\s+)?(issue|ticket|bug)\b", re.I),
            re.compile(r"\btrack\s+(this|that)\s+(as\s+)?(an?\s+)?(issue|ticket)\b", re.I),
        ],
        CommentIntent.CLARIFY: [
            re.compile(r"\b(what|how|why|when|where|which|can\s+you|could\s+you|please\s+explain)\b.*\?", re.I),
            re.compile(r"\bi\s+don'?t\s+understand\b", re.I),
            re.compile(r"\bclarif(y|ication)\b", re.I),
        ],
    }

    def classify(self, comment: GitHubComment) -> ClassifiedComment:
        """Classify a comment using deterministic pattern matching.

        Returns the first matching intent with high confidence, or CLARIFY
        as default with low confidence.
        """
        body = comment.body

        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(body):
                    return ClassifiedComment(
                        comment=comment,
                        intent=intent,
                        confidence=0.9,
                        pattern_matched=True,
                    )

        # No pattern matched — default to CLARIFY
        return ClassifiedComment(
            comment=comment,
            intent=CommentIntent.CLARIFY,
            confidence=0.3,
            pattern_matched=False,
        )

    def classify_with_llm(
        self,
        comment: GitHubComment,
        judge_fn: Callable[[str], str],
    ) -> ClassifiedComment:
        """Classify a comment using an LLM as fallback.

        First tries pattern matching. If confidence is low (< 0.5), uses the
        LLM to classify.
        """
        result = self.classify(comment)
        if result.confidence >= 0.5:
            return result

        # LLM fallback
        intent_names = ", ".join(i.value for i in CommentIntent)
        prompt = (
            f"Classify the intent of this GitHub comment into one of: {intent_names}\n\n"
            f"Comment: {comment.body}\n\n"
            f"Reply with just the intent name."
        )

        try:
            response = judge_fn(prompt).strip().lower()
            for intent in CommentIntent:
                if intent.value in response:
                    return ClassifiedComment(
                        comment=comment,
                        intent=intent,
                        confidence=0.7,
                        pattern_matched=False,
                    )
        except Exception:
            pass

        return result


# ---------------------------------------------------------------------------
# ActionExecutor — dispatches to ``gh`` / ``git`` action handlers
# ---------------------------------------------------------------------------


class ActionExecutor:
    """Executes actions for classified comments using ``gh`` CLI and ``git``."""

    def __init__(self, repo: Optional[str] = None) -> None:
        self.repo = repo or os.environ.get("GITHUB_REPO", "")

    def _repo_args(self) -> list[str]:
        if self.repo:
            return ["--repo", self.repo]
        return []

    def execute(
        self,
        classified: ClassifiedComment,
        dry_run: bool = False,
    ) -> ActionResult:
        """Dispatch to the appropriate action handler."""
        handlers = {
            CommentIntent.EDIT_ISSUE: self._edit_issue,
            CommentIntent.CHANGE_CODE: self._change_code,
            CommentIntent.UPDATE_PR_DESC: self._update_pr_desc,
            CommentIntent.REPLY: self._reply,
            CommentIntent.CLARIFY: self._ask_clarification,
            CommentIntent.CREATE_ISSUE: self._create_issue,
        }
        handler = handlers.get(classified.intent, self._ask_clarification)
        return handler(classified.comment, dry_run)

    def _edit_issue(self, comment: GitHubComment, dry_run: bool) -> ActionResult:
        issue_num = comment.issue or comment.pr
        if not issue_num:
            return ActionResult(
                comment_id=comment.id,
                intent=CommentIntent.EDIT_ISSUE,
                success=False,
                summary="No issue number available",
                error="Cannot edit issue without issue number",
            )

        if dry_run:
            return ActionResult(
                comment_id=comment.id,
                intent=CommentIntent.EDIT_ISSUE,
                success=True,
                summary=f"[dry-run] Would edit issue #{issue_num} body",
            )

        rc, out, err = _run_gh(
            "issue", "edit", str(issue_num),
            "--body", comment.body,
            *self._repo_args(),
        )
        return ActionResult(
            comment_id=comment.id,
            intent=CommentIntent.EDIT_ISSUE,
            success=rc == 0,
            summary=f"Edited issue #{issue_num}" if rc == 0 else f"Failed to edit issue #{issue_num}",
            error=err if rc != 0 else None,
        )

    def _change_code(self, comment: GitHubComment, dry_run: bool) -> ActionResult:
        if dry_run:
            return ActionResult(
                comment_id=comment.id,
                intent=CommentIntent.CHANGE_CODE,
                success=True,
                summary=f"[dry-run] Would process code change request: {comment.body[:80]}",
            )

        # Code changes require agent orchestration — log for processing
        return ActionResult(
            comment_id=comment.id,
            intent=CommentIntent.CHANGE_CODE,
            success=True,
            summary=f"Code change queued: {comment.body[:80]}",
        )

    def _update_pr_desc(self, comment: GitHubComment, dry_run: bool) -> ActionResult:
        if not comment.pr:
            return ActionResult(
                comment_id=comment.id,
                intent=CommentIntent.UPDATE_PR_DESC,
                success=False,
                summary="No PR number available",
                error="Cannot update PR description without PR number",
            )

        if dry_run:
            return ActionResult(
                comment_id=comment.id,
                intent=CommentIntent.UPDATE_PR_DESC,
                success=True,
                summary=f"[dry-run] Would update PR #{comment.pr} description",
            )

        rc, out, err = _run_gh(
            "pr", "edit", str(comment.pr),
            "--body", comment.body,
            *self._repo_args(),
        )
        return ActionResult(
            comment_id=comment.id,
            intent=CommentIntent.UPDATE_PR_DESC,
            success=rc == 0,
            summary=f"Updated PR #{comment.pr} description" if rc == 0 else f"Failed to update PR #{comment.pr}",
            error=err if rc != 0 else None,
        )

    def _reply(self, comment: GitHubComment, dry_run: bool) -> ActionResult:
        target = f"PR #{comment.pr}" if comment.pr else f"issue #{comment.issue}"

        if dry_run:
            return ActionResult(
                comment_id=comment.id,
                intent=CommentIntent.REPLY,
                success=True,
                summary=f"[dry-run] Would reply to {target}",
            )

        # Generate LLM reply
        try:
            from orchestration.backends import create_backend

            backend = create_backend("anthropic")

            # Build prompt for reply
            prompt = f"""You are reviewing a GitHub comment on {target}.

Comment:
{comment.body}

Please provide a helpful, concise response addressing the feedback. Keep it professional and actionable."""

            response = backend.complete(prompt)

            # Post reply via gh CLI
            if comment.pr:
                rc, _, err = _run_gh("pr", "comment", str(comment.pr), "--body", response)
            else:
                rc, _, err = _run_gh("issue", "comment", str(comment.issue), "--body", response)

            if rc != 0:
                raise Exception(f"Failed to post comment: {err}")

            return ActionResult(
                comment_id=comment.id,
                intent=CommentIntent.REPLY,
                success=True,
                summary=f"Posted reply to {target}",
            )
        except Exception as e:
            return ActionResult(
                comment_id=comment.id,
                intent=CommentIntent.REPLY,
                success=False,
                summary=f"Failed to reply to {target}",
                error=str(e),
            )

    def _ask_clarification(self, comment: GitHubComment, dry_run: bool) -> ActionResult:
        target = f"PR #{comment.pr}" if comment.pr else f"issue #{comment.issue}"

        if dry_run:
            return ActionResult(
                comment_id=comment.id,
                intent=CommentIntent.CLARIFY,
                success=True,
                summary=f"[dry-run] Would ask for clarification on {target}",
            )

        return ActionResult(
            comment_id=comment.id,
            intent=CommentIntent.CLARIFY,
            success=True,
            summary=f"Clarification needed on {target}",
        )

    def _create_issue(self, comment: GitHubComment, dry_run: bool) -> ActionResult:
        if dry_run:
            return ActionResult(
                comment_id=comment.id,
                intent=CommentIntent.CREATE_ISSUE,
                success=True,
                summary=f"[dry-run] Would create new issue from comment: {comment.body[:80]}",
            )

        title = comment.body.split("\n")[0][:80]
        rc, out, err = _run_gh(
            "issue", "create",
            "--title", title,
            "--body", comment.body,
            *self._repo_args(),
        )
        return ActionResult(
            comment_id=comment.id,
            intent=CommentIntent.CREATE_ISSUE,
            success=rc == 0,
            summary=f"Created issue: {out}" if rc == 0 else "Failed to create issue",
            error=err if rc != 0 else None,
        )


# ---------------------------------------------------------------------------
# SyncHistory — JSONL persistence
# ---------------------------------------------------------------------------


class SyncHistory:
    """Persists sync history as JSONL at ``.eco-state/sync-history.jsonl``."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        self._state_dir = Path(state_dir) if state_dir else Path(".eco-state")
        self._path = self._state_dir / "sync-history.jsonl"

    def _ensure_dir(self) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)

    def is_processed(self, comment_id: str) -> bool:
        """Check if a comment has already been processed."""
        if not self._path.exists():
            return False
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if record.get("comment_id") == comment_id:
                        return True
                except json.JSONDecodeError:
                    continue
        return False

    def record(self, result: ActionResult) -> None:
        """Append an action result to the history file."""
        self._ensure_dir()
        entry = {
            "comment_id": result.comment_id,
            "intent": result.intent.value,
            "success": result.success,
            "summary": result.summary,
            "error": result.error,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        with open(self._path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_runs(self, since: str | None = None) -> list[SyncRun]:
        """Read all sync runs, optionally filtered by timestamp."""
        if not self._path.exists():
            return []

        results: list[ActionResult] = []
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if since and record.get("timestamp", "") < since:
                        continue
                    results.append(
                        ActionResult(
                            comment_id=record["comment_id"],
                            intent=CommentIntent(record["intent"]),
                            success=record["success"],
                            summary=record["summary"],
                            error=record.get("error"),
                        )
                    )
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        if not results:
            return []

        # Group into a single run for simplicity
        return [
            SyncRun(
                timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                results=results,
                dry_run=False,
            )
        ]
