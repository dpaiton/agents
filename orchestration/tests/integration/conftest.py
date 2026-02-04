"""Shared fixtures for integration tests.

All integration tests are marked with @pytest.mark.integration and can
be run with: uv run pytest -m integration -v
"""

import pytest

from orchestration.sync_engine import GitHubComment


@pytest.fixture
def make_comment():
    """Factory fixture for creating GitHubComment instances."""

    def _make(
        body: str,
        *,
        comment_id: str = "IC_test_001",
        author: str = "testuser",
        pr: int | None = None,
        issue: int | None = None,
        path: str | None = None,
        line: int | None = None,
    ) -> GitHubComment:
        return GitHubComment(
            id=comment_id,
            body=body,
            author=author,
            created_at="2026-01-01T00:00:00Z",
            pr=pr,
            issue=issue,
            path=path,
            line=line,
        )

    return _make


@pytest.fixture
def sync_state_dir(tmp_path):
    """Provide a temporary directory for sync history."""
    return tmp_path / "eco-state"
