"""Tests for the comment-driven sync engine.

Tests are written first (P7: Spec / Test / Evals First) and cover:
- CommentIntent enum
- GitHubComment dataclass
- IntentClassifier pattern matching
- CommentFetcher subprocess mocking
- ActionExecutor dispatch and dry-run
- SyncHistory persistence
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

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


# ---------------------------------------------------------------------------
# TestCommentIntent
# ---------------------------------------------------------------------------


class TestCommentIntent:
    """Tests for CommentIntent enum."""

    def test_has_edit_issue(self):
        assert CommentIntent.EDIT_ISSUE.value == "edit_issue"

    def test_has_change_code(self):
        assert CommentIntent.CHANGE_CODE.value == "change_code"

    def test_has_update_pr_desc(self):
        assert CommentIntent.UPDATE_PR_DESC.value == "update_pr_desc"

    def test_has_reply(self):
        assert CommentIntent.REPLY.value == "reply"

    def test_has_clarify(self):
        assert CommentIntent.CLARIFY.value == "clarify"

    def test_has_create_issue(self):
        assert CommentIntent.CREATE_ISSUE.value == "create_issue"

    def test_str_returns_value(self):
        assert str(CommentIntent.EDIT_ISSUE) == "edit_issue"

    def test_all_intents_count(self):
        assert len(CommentIntent) == 7


# ---------------------------------------------------------------------------
# TestGitHubComment
# ---------------------------------------------------------------------------


class TestGitHubComment:
    """Tests for GitHubComment dataclass."""

    def test_required_fields(self):
        c = GitHubComment(
            id="123",
            body="Fix the bug",
            author="user1",
            created_at="2025-01-01T00:00:00Z",
        )
        assert c.id == "123"
        assert c.body == "Fix the bug"
        assert c.author == "user1"
        assert c.created_at == "2025-01-01T00:00:00Z"

    def test_optional_fields_default_to_none(self):
        c = GitHubComment(id="1", body="", author="a", created_at="")
        assert c.pr is None
        assert c.issue is None
        assert c.thread_id is None
        assert c.path is None
        assert c.line is None

    def test_optional_fields_accept_values(self):
        c = GitHubComment(
            id="1",
            body="",
            author="a",
            created_at="",
            pr=18,
            issue=42,
            thread_id="t1",
            path="src/main.py",
            line=10,
        )
        assert c.pr == 18
        assert c.issue == 42
        assert c.thread_id == "t1"
        assert c.path == "src/main.py"
        assert c.line == 10


# ---------------------------------------------------------------------------
# TestIntentClassifier
# ---------------------------------------------------------------------------


class TestIntentClassifier:
    """Tests for IntentClassifier pattern matching."""

    def _make_comment(self, body: str) -> GitHubComment:
        return GitHubComment(id="c1", body=body, author="user", created_at="")

    def test_edit_issue_pattern(self):
        classifier = IntentClassifier()
        result = classifier.classify(self._make_comment("Please update the issue description"))
        assert result.intent == CommentIntent.EDIT_ISSUE
        assert result.pattern_matched is True
        assert result.confidence >= 0.5

    def test_change_code_pattern_fix(self):
        classifier = IntentClassifier()
        result = classifier.classify(self._make_comment("Fix the function to handle nulls"))
        assert result.intent == CommentIntent.CHANGE_CODE

    def test_change_code_pattern_implement(self):
        classifier = IntentClassifier()
        result = classifier.classify(self._make_comment("Implement the test for validation"))
        assert result.intent == CommentIntent.CHANGE_CODE

    def test_change_code_pattern_push(self):
        classifier = IntentClassifier()
        result = classifier.classify(self._make_comment("Push a fix for this"))
        assert result.intent == CommentIntent.CHANGE_CODE

    def test_update_pr_desc_pattern(self):
        classifier = IntentClassifier()
        result = classifier.classify(self._make_comment("Update the PR description"))
        assert result.intent == CommentIntent.UPDATE_PR_DESC

    def test_reply_pattern_lgtm(self):
        classifier = IntentClassifier()
        result = classifier.classify(self._make_comment("LGTM"))
        assert result.intent == CommentIntent.REPLY

    def test_reply_pattern_thanks(self):
        classifier = IntentClassifier()
        result = classifier.classify(self._make_comment("Thanks for the fix!"))
        assert result.intent == CommentIntent.REPLY

    def test_reply_pattern_mention(self):
        classifier = IntentClassifier()
        result = classifier.classify(self._make_comment("@bot please respond"))
        assert result.intent == CommentIntent.REPLY

    def test_invoke_agent_pattern_with_colon(self):
        classifier = IntentClassifier()
        result = classifier.classify(self._make_comment("@unity-asset-designer: Create concept art"))
        assert result.intent == CommentIntent.INVOKE_AGENT

    def test_invoke_agent_pattern_orchestrator(self):
        classifier = IntentClassifier()
        result = classifier.classify(self._make_comment("@orchestrator: Please handle this task"))
        assert result.intent == CommentIntent.INVOKE_AGENT

    def test_create_issue_pattern(self):
        classifier = IntentClassifier()
        result = classifier.classify(self._make_comment("Create an issue to track this"))
        assert result.intent == CommentIntent.CREATE_ISSUE

    def test_create_issue_pattern_track(self):
        classifier = IntentClassifier()
        result = classifier.classify(self._make_comment("Track this as an issue"))
        assert result.intent == CommentIntent.CREATE_ISSUE

    def test_clarify_pattern_question(self):
        classifier = IntentClassifier()
        result = classifier.classify(self._make_comment("What does this function do?"))
        assert result.intent == CommentIntent.CLARIFY

    def test_clarify_pattern_dont_understand(self):
        classifier = IntentClassifier()
        result = classifier.classify(self._make_comment("I don't understand the logic here"))
        assert result.intent == CommentIntent.CLARIFY

    def test_ambiguous_falls_to_clarify(self):
        classifier = IntentClassifier()
        result = classifier.classify(self._make_comment("Interesting approach"))
        assert result.intent == CommentIntent.CLARIFY
        assert result.confidence < 0.5

    def test_ambiguous_not_pattern_matched(self):
        classifier = IntentClassifier()
        result = classifier.classify(self._make_comment("Looks good to me overall"))
        assert result.pattern_matched is False

    def test_classify_with_llm_high_confidence_skips_llm(self):
        """When pattern match confidence is high, LLM is not called."""
        classifier = IntentClassifier()
        mock_llm = MagicMock()

        result = classifier.classify_with_llm(
            self._make_comment("Fix the code please"),
            judge_fn=mock_llm,
        )

        assert result.intent == CommentIntent.CHANGE_CODE
        mock_llm.assert_not_called()

    def test_classify_with_llm_low_confidence_calls_llm(self):
        """When pattern match confidence is low, LLM is used."""
        classifier = IntentClassifier()
        mock_llm = MagicMock(return_value="change_code")

        result = classifier.classify_with_llm(
            self._make_comment("Interesting approach"),
            judge_fn=mock_llm,
        )

        mock_llm.assert_called_once()
        assert result.intent == CommentIntent.CHANGE_CODE
        assert result.confidence == 0.7

    def test_classify_with_llm_failure_returns_original(self):
        """If LLM fails, returns the original pattern-match result."""
        classifier = IntentClassifier()
        mock_llm = MagicMock(side_effect=RuntimeError("API error"))

        result = classifier.classify_with_llm(
            self._make_comment("Interesting approach"),
            judge_fn=mock_llm,
        )

        assert result.intent == CommentIntent.CLARIFY
        assert result.confidence == 0.3


# ---------------------------------------------------------------------------
# TestCommentFetcher
# ---------------------------------------------------------------------------


class TestCommentFetcher:
    """Tests for CommentFetcher with mocked subprocess calls."""

    def test_fetch_pr_comments_parses_json(self):
        gh_output = json.dumps({
            "comments": [
                {
                    "id": "c1",
                    "body": "Fix this",
                    "author": {"login": "user1"},
                    "createdAt": "2025-01-01T00:00:00Z",
                },
            ]
        })

        with patch("orchestration.sync_engine.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=gh_output, stderr="",
            )
            fetcher = CommentFetcher(repo="owner/repo")
            comments = fetcher.fetch_pr_comments(18)

        assert len(comments) == 1
        assert comments[0].id == "c1"
        assert comments[0].body == "Fix this"
        assert comments[0].pr == 18

    def test_fetch_issue_comments_parses_json(self):
        gh_output = json.dumps({
            "comments": [
                {
                    "id": "c2",
                    "body": "Track this",
                    "author": {"login": "user2"},
                    "createdAt": "2025-01-02T00:00:00Z",
                },
            ]
        })

        with patch("orchestration.sync_engine.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=gh_output, stderr="",
            )
            fetcher = CommentFetcher(repo="owner/repo")
            comments = fetcher.fetch_issue_comments(42)

        assert len(comments) == 1
        assert comments[0].id == "c2"
        assert comments[0].issue == 42

    def test_fetch_pr_comments_returns_empty_on_failure(self):
        with patch("orchestration.sync_engine.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="", stderr="error",
            )
            fetcher = CommentFetcher(repo="owner/repo")
            comments = fetcher.fetch_pr_comments(18)

        assert comments == []

    def test_fetch_pr_review_threads_parses_graphql(self):
        graphql_response = json.dumps({
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "id": "t1",
                                    "isResolved": False,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "id": "rc1",
                                                "body": "Review comment",
                                                "author": {"login": "reviewer"},
                                                "createdAt": "2025-01-01T00:00:00Z",
                                                "path": "src/main.py",
                                                "line": 42,
                                            }
                                        ]
                                    },
                                },
                                {
                                    "id": "t2",
                                    "isResolved": True,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "id": "rc2",
                                                "body": "Resolved",
                                                "author": {"login": "reviewer"},
                                                "createdAt": "2025-01-01T00:00:00Z",
                                                "path": None,
                                                "line": None,
                                            }
                                        ]
                                    },
                                },
                            ]
                        }
                    }
                }
            }
        })

        with patch("orchestration.sync_engine.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=graphql_response, stderr="",
            )
            fetcher = CommentFetcher(repo="owner/repo")
            comments = fetcher.fetch_pr_review_threads(18)

        # Only unresolved thread should produce comments
        assert len(comments) == 1
        assert comments[0].id == "rc1"
        assert comments[0].thread_id == "t1"
        assert comments[0].path == "src/main.py"
        assert comments[0].line == 42

    def test_fetch_pr_review_threads_no_repo(self):
        fetcher = CommentFetcher(repo="")
        comments = fetcher.fetch_pr_review_threads(18)
        assert comments == []


# ---------------------------------------------------------------------------
# TestActionExecutor
# ---------------------------------------------------------------------------


class TestActionExecutor:
    """Tests for ActionExecutor dispatch and dry-run mode."""

    def _make_classified(
        self,
        intent: CommentIntent,
        pr: int | None = None,
        issue: int | None = None,
    ) -> ClassifiedComment:
        comment = GitHubComment(
            id="c1",
            body="Test body",
            author="user",
            created_at="",
            pr=pr,
            issue=issue,
        )
        return ClassifiedComment(
            comment=comment,
            intent=intent,
            confidence=0.9,
            pattern_matched=True,
        )

    def test_edit_issue_dry_run(self):
        executor = ActionExecutor()
        classified = self._make_classified(CommentIntent.EDIT_ISSUE, issue=42)
        result = executor.execute(classified, dry_run=True)
        assert result.success is True
        assert "[dry-run]" in result.summary
        assert "42" in result.summary

    def test_change_code_dry_run(self):
        executor = ActionExecutor()
        classified = self._make_classified(CommentIntent.CHANGE_CODE, pr=18)
        result = executor.execute(classified, dry_run=True)
        assert result.success is True
        assert "[dry-run]" in result.summary

    def test_update_pr_desc_dry_run(self):
        executor = ActionExecutor()
        classified = self._make_classified(CommentIntent.UPDATE_PR_DESC, pr=18)
        result = executor.execute(classified, dry_run=True)
        assert result.success is True
        assert "[dry-run]" in result.summary
        assert "18" in result.summary

    def test_reply_dry_run(self):
        executor = ActionExecutor()
        classified = self._make_classified(CommentIntent.REPLY, pr=18)
        result = executor.execute(classified, dry_run=True)
        assert result.success is True
        assert "[dry-run]" in result.summary

    def test_invoke_agent_dry_run(self):
        executor = ActionExecutor()
        comment = GitHubComment(
            id="c1",
            body="@unity-asset-designer: Create concept art for spaceship",
            author="user",
            created_at="2024-01-01T00:00:00Z",
            issue=42,
        )
        classified = ClassifiedComment(
            comment=comment,
            intent=CommentIntent.INVOKE_AGENT,
            confidence=0.9,
            pattern_matched=True,
        )
        result = executor.execute(classified, dry_run=True)
        assert result.success is True
        assert "[dry-run]" in result.summary
        assert "unity-asset-designer" in result.summary

    def test_clarify_dry_run(self):
        executor = ActionExecutor()
        classified = self._make_classified(CommentIntent.CLARIFY, issue=42)
        result = executor.execute(classified, dry_run=True)
        assert result.success is True
        assert "[dry-run]" in result.summary

    def test_create_issue_dry_run(self):
        executor = ActionExecutor()
        classified = self._make_classified(CommentIntent.CREATE_ISSUE)
        result = executor.execute(classified, dry_run=True)
        assert result.success is True
        assert "[dry-run]" in result.summary

    def test_edit_issue_no_issue_number(self):
        executor = ActionExecutor()
        classified = self._make_classified(CommentIntent.EDIT_ISSUE)
        result = executor.execute(classified, dry_run=False)
        assert result.success is False
        assert result.error is not None

    def test_update_pr_desc_no_pr_number(self):
        executor = ActionExecutor()
        classified = self._make_classified(CommentIntent.UPDATE_PR_DESC)
        result = executor.execute(classified, dry_run=False)
        assert result.success is False
        assert result.error is not None

    def test_change_code_queues_action(self):
        executor = ActionExecutor()
        classified = self._make_classified(CommentIntent.CHANGE_CODE, pr=18)
        result = executor.execute(classified, dry_run=False)
        assert result.success is True
        assert "queued" in result.summary.lower() or "change" in result.summary.lower()

    def test_result_has_correct_intent(self):
        executor = ActionExecutor()
        for intent in CommentIntent:
            classified = self._make_classified(intent, pr=1, issue=1)
            result = executor.execute(classified, dry_run=True)
            assert result.intent == intent


# ---------------------------------------------------------------------------
# TestSyncHistory
# ---------------------------------------------------------------------------


class TestSyncHistory:
    """Tests for SyncHistory JSONL persistence."""

    def test_record_creates_file(self, tmp_path):
        history = SyncHistory(state_dir=tmp_path / ".eco-state")
        result = ActionResult(
            comment_id="c1",
            intent=CommentIntent.EDIT_ISSUE,
            success=True,
            summary="Edited issue",
        )
        history.record(result)
        assert (tmp_path / ".eco-state" / "sync-history.jsonl").exists()

    def test_is_processed_after_record(self, tmp_path):
        history = SyncHistory(state_dir=tmp_path / ".eco-state")
        result = ActionResult(
            comment_id="c1",
            intent=CommentIntent.EDIT_ISSUE,
            success=True,
            summary="Done",
        )
        assert history.is_processed("c1") is False
        history.record(result)
        assert history.is_processed("c1") is True

    def test_is_processed_nonexistent_file(self, tmp_path):
        history = SyncHistory(state_dir=tmp_path / ".eco-state")
        assert history.is_processed("c1") is False

    def test_multiple_records(self, tmp_path):
        history = SyncHistory(state_dir=tmp_path / ".eco-state")
        for i in range(3):
            result = ActionResult(
                comment_id=f"c{i}",
                intent=CommentIntent.REPLY,
                success=True,
                summary=f"Reply {i}",
            )
            history.record(result)

        assert history.is_processed("c0") is True
        assert history.is_processed("c1") is True
        assert history.is_processed("c2") is True
        assert history.is_processed("c99") is False

    def test_get_runs_returns_results(self, tmp_path):
        history = SyncHistory(state_dir=tmp_path / ".eco-state")
        result = ActionResult(
            comment_id="c1",
            intent=CommentIntent.EDIT_ISSUE,
            success=True,
            summary="Done",
        )
        history.record(result)
        runs = history.get_runs()
        assert len(runs) == 1
        assert len(runs[0].results) == 1
        assert runs[0].results[0].comment_id == "c1"

    def test_get_runs_empty_file(self, tmp_path):
        history = SyncHistory(state_dir=tmp_path / ".eco-state")
        runs = history.get_runs()
        assert runs == []

    def test_record_roundtrip_preserves_fields(self, tmp_path):
        history = SyncHistory(state_dir=tmp_path / ".eco-state")
        result = ActionResult(
            comment_id="c42",
            intent=CommentIntent.CREATE_ISSUE,
            success=False,
            summary="Failed",
            error="API error",
        )
        history.record(result)

        # Read the raw JSONL
        path = tmp_path / ".eco-state" / "sync-history.jsonl"
        line = path.read_text().strip()
        record = json.loads(line)
        assert record["comment_id"] == "c42"
        assert record["intent"] == "create_issue"
        assert record["success"] is False
        assert record["error"] == "API error"
        assert "timestamp" in record

    def test_get_runs_with_since_filter(self, tmp_path):
        history = SyncHistory(state_dir=tmp_path / ".eco-state")
        result = ActionResult(
            comment_id="c1",
            intent=CommentIntent.REPLY,
            success=True,
            summary="Done",
        )
        history.record(result)

        # Since far future should return nothing
        runs = history.get_runs(since="2099-01-01T00:00:00Z")
        assert len(runs) == 0
