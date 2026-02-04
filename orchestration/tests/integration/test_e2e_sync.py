"""End-to-end integration tests for sync operations.

These tests validate the full comment-driven workflow: fetch comments →
classify intent → execute action → record history. They use real
classifiers and executors with mocked subprocess calls.

Each test follows the Foundational Algorithm (P2) as a scientific
experiment: hypothesis → setup → execute → verify.
"""

import json

import pytest
from unittest.mock import patch, MagicMock

from orchestration.sync_engine import (
    ActionExecutor,
    ActionResult,
    ClassifiedComment,
    CommentFetcher,
    CommentIntent,
    GitHubComment,
    IntentClassifier,
    SyncHistory,
)


pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Sync: Intent classification
# ---------------------------------------------------------------------------


class TestSyncIntentClassification:
    """Hypothesis: The classifier deterministically maps comment patterns
    to the correct intent with high confidence."""

    def test_edit_issue_intent(self, make_comment):
        classifier = IntentClassifier()
        comment = make_comment("Please update the issue body to reflect the new design")
        classified = classifier.classify(comment)
        assert classified.intent == CommentIntent.EDIT_ISSUE
        assert classified.confidence >= 0.8

    def test_change_code_intent(self, make_comment):
        classifier = IntentClassifier()
        comment = make_comment(
            "Fix the code on line 42 of auth.py",
            pr=18, path="auth.py", line=42,
        )
        classified = classifier.classify(comment)
        assert classified.intent == CommentIntent.CHANGE_CODE
        assert classified.confidence >= 0.8

    def test_change_code_implement_function(self, make_comment):
        classifier = IntentClassifier()
        comment = make_comment(
            "Implement the function for input validation",
            pr=18, path="src/auth.py", line=10,
        )
        classified = classifier.classify(comment)
        assert classified.intent == CommentIntent.CHANGE_CODE
        assert classified.confidence >= 0.8

    def test_update_pr_desc_intent(self, make_comment):
        classifier = IntentClassifier()
        comment = make_comment(
            "Update the PR description to mention the breaking change",
            pr=18,
        )
        classified = classifier.classify(comment)
        assert classified.intent == CommentIntent.UPDATE_PR_DESC
        assert classified.confidence >= 0.8

    def test_reply_intent(self, make_comment):
        classifier = IntentClassifier()
        comment = make_comment("LGTM, thanks for the fix!", pr=18)
        classified = classifier.classify(comment)
        assert classified.intent == CommentIntent.REPLY

    def test_create_issue_intent(self, make_comment):
        classifier = IntentClassifier()
        comment = make_comment("Can you open a new issue to track the refactoring?")
        classified = classifier.classify(comment)
        assert classified.intent == CommentIntent.CREATE_ISSUE

    def test_unclear_comment_gets_clarify(self, make_comment):
        """P16: Ambiguous input → ask for clarification, don't guess."""
        classifier = IntentClassifier()
        comment = make_comment("Hmm, I'm not sure about this")
        classified = classifier.classify(comment)
        assert classified.intent == CommentIntent.CLARIFY
        assert classified.confidence < 0.5

    def test_classification_is_deterministic(self, make_comment):
        """P5: Same input always produces same classification."""
        classifier = IntentClassifier()
        comment = make_comment("Fix the broken test in test_router.py")
        result_a = classifier.classify(comment)
        result_b = classifier.classify(comment)
        assert result_a.intent == result_b.intent
        assert result_a.confidence == result_b.confidence


# ---------------------------------------------------------------------------
# Sync: Action execution (dry run)
# ---------------------------------------------------------------------------


class TestSyncActionExecution:
    """Hypothesis: The executor correctly dispatches each intent type
    to the appropriate action handler in dry-run mode."""

    def _make_classified(self, intent, body="test", **kwargs):
        comment = GitHubComment(
            id=f"IC_test_{intent.value}",
            body=body,
            author="testuser",
            created_at="2026-01-01T00:00:00Z",
            **kwargs,
        )
        return ClassifiedComment(
            comment=comment,
            intent=intent,
            confidence=0.9,
            pattern_matched=True,
        )

    def test_edit_issue_dry_run(self):
        executor = ActionExecutor()
        classified = self._make_classified(
            CommentIntent.EDIT_ISSUE, body="Update the issue", issue=42,
        )
        result = executor.execute(classified, dry_run=True)
        assert result.success is True
        assert result.intent == CommentIntent.EDIT_ISSUE

    def test_change_code_dry_run(self):
        executor = ActionExecutor()
        classified = self._make_classified(
            CommentIntent.CHANGE_CODE, body="Fix the bug", pr=18,
        )
        result = executor.execute(classified, dry_run=True)
        assert result.success is True
        assert result.intent == CommentIntent.CHANGE_CODE

    def test_update_pr_desc_dry_run(self):
        executor = ActionExecutor()
        classified = self._make_classified(
            CommentIntent.UPDATE_PR_DESC, body="Update description", pr=18,
        )
        result = executor.execute(classified, dry_run=True)
        assert result.success is True
        assert result.intent == CommentIntent.UPDATE_PR_DESC

    def test_reply_dry_run(self):
        executor = ActionExecutor()
        classified = self._make_classified(
            CommentIntent.REPLY, body="Thanks!", pr=18,
        )
        result = executor.execute(classified, dry_run=True)
        assert result.success is True
        assert result.intent == CommentIntent.REPLY

    def test_clarify_dry_run(self):
        executor = ActionExecutor()
        classified = self._make_classified(
            CommentIntent.CLARIFY, body="Unclear request",
        )
        result = executor.execute(classified, dry_run=True)
        assert result.success is True
        assert result.intent == CommentIntent.CLARIFY

    def test_create_issue_dry_run(self):
        executor = ActionExecutor()
        classified = self._make_classified(
            CommentIntent.CREATE_ISSUE, body="Open an issue for this",
        )
        result = executor.execute(classified, dry_run=True)
        assert result.success is True
        assert result.intent == CommentIntent.CREATE_ISSUE


# ---------------------------------------------------------------------------
# Sync: History tracking
# ---------------------------------------------------------------------------


class TestSyncHistory:
    """Hypothesis: The sync history correctly tracks processed comments
    and prevents reprocessing (idempotency, P5)."""

    def test_record_and_check(self, tmp_path):
        history = SyncHistory(state_dir=str(tmp_path))
        result = ActionResult(
            comment_id="IC_test_001",
            intent=CommentIntent.EDIT_ISSUE,
            success=True,
            summary="Updated issue body",
        )
        assert not history.is_processed("IC_test_001")
        history.record(result)
        assert history.is_processed("IC_test_001")

    def test_idempotent_processing(self, tmp_path):
        """P5: Running sync twice on the same comment takes no new action."""
        history = SyncHistory(state_dir=str(tmp_path))
        result = ActionResult(
            comment_id="IC_test_002",
            intent=CommentIntent.CHANGE_CODE,
            success=True,
            summary="Pushed code change",
        )
        history.record(result)

        # Second processing should be skipped
        assert history.is_processed("IC_test_002")

    def test_multiple_comments_tracked(self, tmp_path):
        history = SyncHistory(state_dir=str(tmp_path))
        for i in range(5):
            result = ActionResult(
                comment_id=f"IC_test_{i:03d}",
                intent=CommentIntent.REPLY,
                success=True,
                summary=f"Replied to comment {i}",
            )
            history.record(result)

        for i in range(5):
            assert history.is_processed(f"IC_test_{i:03d}")
        assert not history.is_processed("IC_test_999")


# ---------------------------------------------------------------------------
# Sync: Full workflow (classify → execute → record)
# ---------------------------------------------------------------------------


class TestSyncFullWorkflow:
    """Hypothesis: The full sync workflow processes a comment through
    classification, execution, and history recording."""

    def test_full_workflow_edit_issue(self, make_comment, tmp_path):
        classifier = IntentClassifier()
        executor = ActionExecutor()
        history = SyncHistory(state_dir=str(tmp_path))

        comment = make_comment(
            "Please update the issue body with the new requirements",
            issue=42,
        )

        # Step 1: Classify
        classified = classifier.classify(comment)
        assert classified.intent == CommentIntent.EDIT_ISSUE

        # Step 2: Execute (dry run)
        result = executor.execute(classified, dry_run=True)
        assert result.success is True

        # Step 3: Record
        history.record(result)
        assert history.is_processed(comment.id)

    def test_full_workflow_code_change(self, make_comment, tmp_path):
        classifier = IntentClassifier()
        executor = ActionExecutor()
        history = SyncHistory(state_dir=str(tmp_path))

        comment = make_comment(
            "Fix the function in auth.py for validation",
            pr=18,
            path="src/auth.py",
            line=10,
        )

        classified = classifier.classify(comment)
        assert classified.intent == CommentIntent.CHANGE_CODE

        result = executor.execute(classified, dry_run=True)
        assert result.success is True

        history.record(result)
        assert history.is_processed(comment.id)

    def test_full_workflow_unclear_asks_clarification(self, make_comment, tmp_path):
        """P16: Unclear comment → classify as CLARIFY → ask for more info."""
        classifier = IntentClassifier()
        executor = ActionExecutor()
        history = SyncHistory(state_dir=str(tmp_path))

        comment = make_comment("What do you think about this approach?")

        classified = classifier.classify(comment)
        assert classified.intent == CommentIntent.CLARIFY

        result = executor.execute(classified, dry_run=True)
        assert result.success is True

        history.record(result)
        assert history.is_processed(comment.id)


# ---------------------------------------------------------------------------
# Sync: Comment fetcher (mocked subprocess)
# ---------------------------------------------------------------------------


class TestSyncCommentFetcher:
    """Hypothesis: The comment fetcher correctly parses gh CLI output."""

    @patch("orchestration.sync_engine.subprocess.run")
    def test_fetch_pr_comments_parses_json(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "comments": [
                    {
                        "id": "IC_kwDOtest1",
                        "body": "Please fix this",
                        "author": {"login": "user1"},
                        "createdAt": "2026-01-01T00:00:00Z",
                    }
                ]
            }),
        )

        fetcher = CommentFetcher()
        comments = fetcher.fetch_pr_comments(18)

        assert len(comments) == 1
        assert comments[0].id == "IC_kwDOtest1"
        assert comments[0].body == "Please fix this"
        assert comments[0].author == "user1"
        assert comments[0].pr == 18

    @patch("orchestration.sync_engine.subprocess.run")
    def test_fetch_issue_comments_parses_json(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "comments": [
                    {
                        "id": "IC_kwDOtest2",
                        "body": "Update the description",
                        "author": {"login": "user2"},
                        "createdAt": "2026-01-02T00:00:00Z",
                    }
                ]
            }),
        )

        fetcher = CommentFetcher()
        comments = fetcher.fetch_issue_comments(42)

        assert len(comments) == 1
        assert comments[0].issue == 42

    @patch("orchestration.sync_engine.subprocess.run")
    def test_fetch_returns_empty_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        fetcher = CommentFetcher()
        comments = fetcher.fetch_pr_comments(99)
        assert comments == []


# ---------------------------------------------------------------------------
# Sync: Dry-run prevents side effects
# ---------------------------------------------------------------------------


class TestSyncDryRun:
    """Hypothesis: dry_run=True shows the plan but takes no action."""

    def test_dry_run_does_not_call_subprocess(self, make_comment):
        executor = ActionExecutor()
        comment = make_comment("Fix the bug", pr=18)
        classified = ClassifiedComment(
            comment=comment,
            intent=CommentIntent.CHANGE_CODE,
            confidence=0.9,
            pattern_matched=True,
        )

        with patch("orchestration.sync_engine.subprocess.run") as mock_run:
            result = executor.execute(classified, dry_run=True)
            mock_run.assert_not_called()

        assert result.success is True

    def test_dry_run_result_is_successful(self, make_comment):
        executor = ActionExecutor()
        for intent in CommentIntent:
            comment = make_comment(f"Test {intent.value}", issue=42, pr=18)
            classified = ClassifiedComment(
                comment=comment,
                intent=intent,
                confidence=0.9,
                pattern_matched=True,
            )
            result = executor.execute(classified, dry_run=True)
            assert result.success is True, f"Dry run failed for {intent}"
