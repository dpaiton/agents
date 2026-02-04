"""Token usage tracking and cost estimation.

This module provides deterministic infrastructure for recording, storing,
and analyzing token usage across CLI commands. All cost calculations use
a static pricing table — no API calls, no probabilistic behavior.

Design Principles:
- P5 Deterministic Infrastructure: Pricing lookup, aggregation are pure Python
- P6 Code Before Prompts: Token counting and cost math, not AI
- P8 UNIX Philosophy: JSONL storage is append-only, greppable, composable
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


@dataclass
class UsageRecord:
    """A single token usage event.

    Attributes:
        timestamp: ISO 8601 UTC timestamp (e.g. "2026-02-04T14:30:00Z")
        model: Model identifier (e.g. "claude-sonnet-4-20250514")
        input_tokens: Number of input/prompt tokens consumed
        output_tokens: Number of output/completion tokens consumed
        command: CLI command that generated this usage (e.g. "route", "judge")
        pr: Associated PR number, if any
        issue: Associated issue number, if any
        session_id: Optional session identifier for grouping related calls
    """

    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    command: str
    pr: Optional[int] = None
    issue: Optional[int] = None
    session_id: Optional[str] = None


@dataclass
class DailySummary:
    """Aggregated usage for a single day.

    Attributes:
        date: The date string (YYYY-MM-DD)
        total_input_tokens: Sum of input tokens for the day
        total_output_tokens: Sum of output tokens for the day
        estimated_cost_usd: Estimated cost in USD
        record_count: Number of usage events
        models: Unique models used (sorted)
        commands: Unique commands invoked (sorted)
    """

    date: str
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost_usd: float
    record_count: int
    models: list[str]
    commands: list[str]


# ---------------------------------------------------------------------------
# Pricing table — per 1M tokens in USD
# ---------------------------------------------------------------------------

MODEL_PRICING: dict[str, dict[str, float]] = {
    # Anthropic
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    "claude-opus-4-5-20251101": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-haiku-3-5-20241022": {"input": 0.80, "output": 4.00},
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    # Google
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
}

DEFAULT_PRICING: dict[str, float] = {"input": 3.00, "output": 15.00}


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

class UsageStore:
    """Append-only JSONL store for usage records.

    Default location: ``~/.agents/usage.jsonl``.  Override with the
    ``AGENTS_USAGE_FILE`` environment variable.
    """

    def __init__(self, path: str | None = None) -> None:
        if path is None:
            path = os.environ.get(
                "AGENTS_USAGE_FILE",
                os.path.expanduser("~/.agents/usage.jsonl"),
            )
        self.path = Path(path)

    def append(self, record: UsageRecord) -> None:
        """Append a single usage record."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    def read_all(self) -> list[UsageRecord]:
        """Read every record from the store."""
        if not self.path.exists():
            return []
        records: list[UsageRecord] = []
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(UsageRecord(**json.loads(line)))
        return records

    def read_filtered(
        self,
        *,
        pr: int | None = None,
        issue: int | None = None,
        since: str | None = None,
        until: str | None = None,
        command: str | None = None,
    ) -> list[UsageRecord]:
        """Read records matching all supplied filters (AND logic)."""
        records = self.read_all()
        if pr is not None:
            records = [r for r in records if r.pr == pr]
        if issue is not None:
            records = [r for r in records if r.issue == issue]
        if since is not None:
            # Date-only values (YYYY-MM-DD) include the full day
            cmp = since + "T00:00:00Z" if len(since) == 10 else since
            records = [r for r in records if r.timestamp >= cmp]
        if until is not None:
            cmp = until + "T23:59:59Z" if len(until) == 10 else until
            records = [r for r in records if r.timestamp <= cmp]
        if command is not None:
            records = [r for r in records if r.command == command]
        return records


# ---------------------------------------------------------------------------
# Cost calculation
# ---------------------------------------------------------------------------

class CostCalculator:
    """Pure-Python cost estimation from token counts and a pricing table."""

    @staticmethod
    def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD for a single usage event."""
        pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    @staticmethod
    def estimate_record_cost(record: UsageRecord) -> float:
        """Estimate cost in USD for a ``UsageRecord``."""
        return CostCalculator.estimate_cost(
            record.model, record.input_tokens, record.output_tokens,
        )

    @staticmethod
    def summarize_by_day(records: list[UsageRecord]) -> list[DailySummary]:
        """Aggregate records into daily summaries, sorted chronologically."""
        by_day: dict[str, list[UsageRecord]] = defaultdict(list)
        for r in records:
            day = r.timestamp[:10]  # YYYY-MM-DD
            by_day[day].append(r)

        summaries: list[DailySummary] = []
        for day in sorted(by_day):
            day_records = by_day[day]
            total_input = sum(r.input_tokens for r in day_records)
            total_output = sum(r.output_tokens for r in day_records)
            total_cost = sum(
                CostCalculator.estimate_record_cost(r) for r in day_records
            )
            summaries.append(
                DailySummary(
                    date=day,
                    total_input_tokens=total_input,
                    total_output_tokens=total_output,
                    estimated_cost_usd=round(total_cost, 6),
                    record_count=len(day_records),
                    models=sorted({r.model for r in day_records}),
                    commands=sorted({r.command for r in day_records}),
                )
            )
        return summaries
