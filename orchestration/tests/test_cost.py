"""Tests for token usage tracking and cost estimation."""

from __future__ import annotations

import json

import pytest

from orchestration.cost import (
    MODEL_PRICING,
    DEFAULT_PRICING,
    CostCalculator,
    DailySummary,
    UsageRecord,
    UsageStore,
)


# ---------------------------------------------------------------------------
# UsageRecord
# ---------------------------------------------------------------------------

class TestUsageRecord:
    """Tests for UsageRecord dataclass."""

    def test_required_fields(self):
        r = UsageRecord(
            timestamp="2026-02-04T14:00:00Z",
            model="claude-sonnet-4-20250514",
            input_tokens=100,
            output_tokens=50,
            command="route",
        )
        assert r.timestamp == "2026-02-04T14:00:00Z"
        assert r.model == "claude-sonnet-4-20250514"
        assert r.input_tokens == 100
        assert r.output_tokens == 50
        assert r.command == "route"

    def test_optional_fields_default_to_none(self):
        r = UsageRecord(
            timestamp="2026-02-04T14:00:00Z",
            model="m",
            input_tokens=0,
            output_tokens=0,
            command="c",
        )
        assert r.pr is None
        assert r.issue is None
        assert r.session_id is None

    def test_optional_fields_accept_values(self):
        r = UsageRecord(
            timestamp="2026-02-04T14:00:00Z",
            model="m",
            input_tokens=0,
            output_tokens=0,
            command="c",
            pr=18,
            issue=42,
            session_id="abc",
        )
        assert r.pr == 18
        assert r.issue == 42
        assert r.session_id == "abc"


# ---------------------------------------------------------------------------
# MODEL_PRICING
# ---------------------------------------------------------------------------

class TestModelPricing:
    """Tests for the pricing table."""

    def test_sonnet_is_defined(self):
        assert "claude-sonnet-4-20250514" in MODEL_PRICING

    def test_opus_is_defined(self):
        assert "claude-opus-4-20250514" in MODEL_PRICING

    def test_haiku_is_defined(self):
        assert "claude-haiku-3-5-20241022" in MODEL_PRICING

    def test_all_entries_have_input_and_output(self):
        for model, pricing in MODEL_PRICING.items():
            assert "input" in pricing, f"{model} missing 'input'"
            assert "output" in pricing, f"{model} missing 'output'"

    def test_all_prices_are_positive(self):
        for model, pricing in MODEL_PRICING.items():
            assert pricing["input"] > 0, f"{model} input price not positive"
            assert pricing["output"] > 0, f"{model} output price not positive"

    def test_default_pricing_has_input_and_output(self):
        assert "input" in DEFAULT_PRICING
        assert "output" in DEFAULT_PRICING
        assert DEFAULT_PRICING["input"] > 0
        assert DEFAULT_PRICING["output"] > 0


# ---------------------------------------------------------------------------
# CostCalculator
# ---------------------------------------------------------------------------

class TestCostCalculator:
    """Tests for CostCalculator."""

    def test_known_model_uses_pricing_table(self):
        cost = CostCalculator.estimate_cost(
            "claude-sonnet-4-20250514", 1_000_000, 0,
        )
        assert cost == pytest.approx(3.00)

    def test_known_model_output_pricing(self):
        cost = CostCalculator.estimate_cost(
            "claude-sonnet-4-20250514", 0, 1_000_000,
        )
        assert cost == pytest.approx(15.00)

    def test_unknown_model_uses_default(self):
        cost = CostCalculator.estimate_cost("unknown-model", 1_000_000, 0)
        assert cost == pytest.approx(DEFAULT_PRICING["input"])

    def test_zero_tokens_zero_cost(self):
        cost = CostCalculator.estimate_cost("claude-sonnet-4-20250514", 0, 0)
        assert cost == 0.0

    def test_estimate_record_cost_delegates(self):
        r = UsageRecord(
            timestamp="2026-02-04T14:00:00Z",
            model="claude-sonnet-4-20250514",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            command="judge",
        )
        expected = CostCalculator.estimate_cost(r.model, r.input_tokens, r.output_tokens)
        assert CostCalculator.estimate_record_cost(r) == expected

    def test_summarize_by_day_groups_records(self):
        records = [
            UsageRecord("2026-02-04T10:00:00Z", "m", 100, 50, "route"),
            UsageRecord("2026-02-04T11:00:00Z", "m", 200, 100, "judge"),
            UsageRecord("2026-02-05T10:00:00Z", "m", 300, 150, "route"),
        ]
        summaries = CostCalculator.summarize_by_day(records)
        assert len(summaries) == 2
        assert summaries[0].date == "2026-02-04"
        assert summaries[0].total_input_tokens == 300
        assert summaries[0].total_output_tokens == 150
        assert summaries[0].record_count == 2
        assert summaries[1].date == "2026-02-05"
        assert summaries[1].record_count == 1

    def test_summarize_by_day_sorted_chronologically(self):
        records = [
            UsageRecord("2026-02-05T10:00:00Z", "m", 100, 50, "c"),
            UsageRecord("2026-02-03T10:00:00Z", "m", 100, 50, "c"),
            UsageRecord("2026-02-04T10:00:00Z", "m", 100, 50, "c"),
        ]
        summaries = CostCalculator.summarize_by_day(records)
        dates = [s.date for s in summaries]
        assert dates == ["2026-02-03", "2026-02-04", "2026-02-05"]

    def test_summarize_by_day_empty_input(self):
        assert CostCalculator.summarize_by_day([]) == []

    def test_summarize_by_day_multiple_models(self):
        records = [
            UsageRecord("2026-02-04T10:00:00Z", "model-a", 100, 50, "c"),
            UsageRecord("2026-02-04T11:00:00Z", "model-b", 100, 50, "c"),
        ]
        summaries = CostCalculator.summarize_by_day(records)
        assert summaries[0].models == ["model-a", "model-b"]

    def test_summarize_by_day_multiple_commands(self):
        records = [
            UsageRecord("2026-02-04T10:00:00Z", "m", 100, 50, "route"),
            UsageRecord("2026-02-04T11:00:00Z", "m", 100, 50, "judge"),
        ]
        summaries = CostCalculator.summarize_by_day(records)
        assert summaries[0].commands == ["judge", "route"]

    def test_summarize_by_day_cost_sums_correctly(self):
        records = [
            UsageRecord("2026-02-04T10:00:00Z", "claude-sonnet-4-20250514", 1_000_000, 0, "c"),
            UsageRecord("2026-02-04T11:00:00Z", "claude-sonnet-4-20250514", 1_000_000, 0, "c"),
        ]
        summaries = CostCalculator.summarize_by_day(records)
        assert summaries[0].estimated_cost_usd == pytest.approx(6.00)


# ---------------------------------------------------------------------------
# UsageStore
# ---------------------------------------------------------------------------

class TestUsageStore:
    """Tests for UsageStore persistence."""

    def _make_record(self, **overrides) -> UsageRecord:
        defaults = dict(
            timestamp="2026-02-04T14:00:00Z",
            model="claude-sonnet-4-20250514",
            input_tokens=100,
            output_tokens=50,
            command="route",
        )
        defaults.update(overrides)
        return UsageRecord(**defaults)

    def test_append_creates_file(self, tmp_path):
        store = UsageStore(str(tmp_path / "usage.jsonl"))
        store.append(self._make_record())
        assert store.path.exists()

    def test_append_creates_parent_dirs(self, tmp_path):
        store = UsageStore(str(tmp_path / "sub" / "dir" / "usage.jsonl"))
        store.append(self._make_record())
        assert store.path.exists()

    def test_roundtrip(self, tmp_path):
        store = UsageStore(str(tmp_path / "usage.jsonl"))
        original = self._make_record(pr=18, session_id="s1")
        store.append(original)
        records = store.read_all()
        assert len(records) == 1
        assert records[0].timestamp == original.timestamp
        assert records[0].model == original.model
        assert records[0].input_tokens == original.input_tokens
        assert records[0].output_tokens == original.output_tokens
        assert records[0].command == original.command
        assert records[0].pr == original.pr
        assert records[0].session_id == original.session_id

    def test_read_all_nonexistent_file(self, tmp_path):
        store = UsageStore(str(tmp_path / "missing.jsonl"))
        assert store.read_all() == []

    def test_read_all_empty_file(self, tmp_path):
        path = tmp_path / "usage.jsonl"
        path.write_text("")
        store = UsageStore(str(path))
        assert store.read_all() == []

    def test_multiple_appends(self, tmp_path):
        store = UsageStore(str(tmp_path / "usage.jsonl"))
        store.append(self._make_record(command="route"))
        store.append(self._make_record(command="judge"))
        store.append(self._make_record(command="review"))
        records = store.read_all()
        assert len(records) == 3
        assert [r.command for r in records] == ["route", "judge", "review"]

    def test_each_append_is_one_line(self, tmp_path):
        path = tmp_path / "usage.jsonl"
        store = UsageStore(str(path))
        store.append(self._make_record())
        store.append(self._make_record())
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        assert len(lines) == 2
        for line in lines:
            json.loads(line)  # each line is valid JSON

    def test_filter_by_pr(self, tmp_path):
        store = UsageStore(str(tmp_path / "usage.jsonl"))
        store.append(self._make_record(pr=18))
        store.append(self._make_record(pr=19))
        store.append(self._make_record(pr=18))
        records = store.read_filtered(pr=18)
        assert len(records) == 2
        assert all(r.pr == 18 for r in records)

    def test_filter_by_issue(self, tmp_path):
        store = UsageStore(str(tmp_path / "usage.jsonl"))
        store.append(self._make_record(issue=42))
        store.append(self._make_record(issue=99))
        records = store.read_filtered(issue=42)
        assert len(records) == 1

    def test_filter_by_since(self, tmp_path):
        store = UsageStore(str(tmp_path / "usage.jsonl"))
        store.append(self._make_record(timestamp="2026-02-01T00:00:00Z"))
        store.append(self._make_record(timestamp="2026-02-03T00:00:00Z"))
        store.append(self._make_record(timestamp="2026-02-05T00:00:00Z"))
        records = store.read_filtered(since="2026-02-03")
        assert len(records) == 2

    def test_filter_by_until(self, tmp_path):
        store = UsageStore(str(tmp_path / "usage.jsonl"))
        store.append(self._make_record(timestamp="2026-02-01T00:00:00Z"))
        store.append(self._make_record(timestamp="2026-02-03T00:00:00Z"))
        store.append(self._make_record(timestamp="2026-02-05T00:00:00Z"))
        records = store.read_filtered(until="2026-02-03")
        assert len(records) == 2

    def test_filter_by_command(self, tmp_path):
        store = UsageStore(str(tmp_path / "usage.jsonl"))
        store.append(self._make_record(command="route"))
        store.append(self._make_record(command="judge"))
        store.append(self._make_record(command="route"))
        records = store.read_filtered(command="route")
        assert len(records) == 2

    def test_combined_filters(self, tmp_path):
        store = UsageStore(str(tmp_path / "usage.jsonl"))
        store.append(self._make_record(pr=18, command="route"))
        store.append(self._make_record(pr=18, command="judge"))
        store.append(self._make_record(pr=19, command="route"))
        records = store.read_filtered(pr=18, command="route")
        assert len(records) == 1
        assert records[0].pr == 18
        assert records[0].command == "route"
