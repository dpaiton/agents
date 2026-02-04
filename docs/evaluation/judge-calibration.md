# Judge Calibration Process

This document defines how to calibrate LLM judges so their scores are consistent, accurate, and reproducible. Calibration is the process of aligning a judge's scoring behavior with known-correct scores using gold-standard examples (P15: Science as Meta-Loop).

Calibration is not optional. An uncalibrated judge produces scores that cannot be compared across evaluations, prompts, or time periods. Calibration is the mechanism that turns subjective evaluation into a reliable measurement.

## Purpose of Calibration

1. **Establish scoring baselines.** Gold-standard examples define what each score means in practice, not just in rubric descriptions.
2. **Detect judge drift.** When a judge prompt is modified or the judge model is updated, re-running calibration examples reveals whether scoring behavior has changed.
3. **Enable inter-rater comparison.** When multiple judges (human or LLM) evaluate the same work, calibration ensures their scores are comparable.
4. **Catch biases early.** Calibration examples are designed to test for known biases (see [bias-awareness.md](bias-awareness.md)). A judge that fails calibration likely has an unmitigated bias.

## Gold-Standard Examples

Gold-standard examples are submissions with **known-correct scores** that have been reviewed and agreed upon by multiple human raters. They serve as the "ground truth" for calibration.

Each gold-standard example includes:
- The task specification
- The submitted code and tests
- The expected score for each criterion with reasoning
- The expected total score

### Gold-Standard Example 1: Score 10/10

**Task:** Write a Python function `parse_config(path: str) -> dict` that reads a TOML configuration file and returns a dictionary. Handle file-not-found, permission errors, and malformed TOML. Include tests.

**Submission:**

```python
# config_parser.py
import tomllib
from pathlib import Path


class ConfigError(Exception):
    """Raised when configuration cannot be loaded."""


def parse_config(path: str) -> dict:
    """Parse a TOML configuration file and return its contents as a dict.

    Args:
        path: Path to the TOML configuration file.

    Returns:
        Dictionary of configuration values.

    Raises:
        ConfigError: If the file cannot be read or parsed.
    """
    config_path = Path(path)

    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {path}")

    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except PermissionError:
        raise ConfigError(f"Permission denied reading: {path}")
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Malformed TOML in {path}: {e}")
```

```python
# test_config_parser.py
import os
import stat
import tempfile
from pathlib import Path

import pytest

from config_parser import ConfigError, parse_config


class TestParseConfig:
    """Tests for parse_config function."""

    def test_valid_config(self, tmp_path):
        """Happy path: valid TOML returns correct dict."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('[server]\nhost = "localhost"\nport = 8080\n')
        result = parse_config(str(config_file))
        assert result == {"server": {"host": "localhost", "port": 8080}}

    def test_empty_config(self, tmp_path):
        """Edge case: empty file returns empty dict."""
        config_file = tmp_path / "empty.toml"
        config_file.write_text("")
        result = parse_config(str(config_file))
        assert result == {}

    def test_file_not_found(self):
        """Error case: missing file raises ConfigError."""
        with pytest.raises(ConfigError, match="not found"):
            parse_config("/nonexistent/path/config.toml")

    def test_permission_denied(self, tmp_path):
        """Error case: unreadable file raises ConfigError."""
        config_file = tmp_path / "secret.toml"
        config_file.write_text("[data]\nkey = 'value'\n")
        config_file.chmod(0o000)
        try:
            with pytest.raises(ConfigError, match="Permission denied"):
                parse_config(str(config_file))
        finally:
            config_file.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def test_malformed_toml(self, tmp_path):
        """Error case: invalid TOML raises ConfigError."""
        config_file = tmp_path / "bad.toml"
        config_file.write_text("[unclosed\n")
        with pytest.raises(ConfigError, match="Malformed TOML"):
            parse_config(str(config_file))

    def test_nested_config(self, tmp_path):
        """Integration: complex nested TOML structure."""
        config_file = tmp_path / "nested.toml"
        config_file.write_text(
            '[database]\nurl = "postgres://localhost/db"\n'
            "[database.pool]\nmin = 2\nmax = 10\n"
        )
        result = parse_config(str(config_file))
        assert result["database"]["url"] == "postgres://localhost/db"
        assert result["database"]["pool"]["min"] == 2
        assert result["database"]["pool"]["max"] == 10
```

**Expected Scoring:**

| Criterion | Score | Evidence |
|---|---|---|
| Correctness | 2 | Handles all specified cases: valid TOML, file not found, permission error, malformed TOML. Edge case (empty file) is handled correctly. Custom exception wraps all failure modes. |
| Completeness | 2 | All three error types from the spec are implemented. Return type matches spec (dict). No missing functionality. |
| Code Quality | 2 | Clear function name, descriptive docstring with Args/Returns/Raises. Custom exception class. Uses pathlib. No duplication. Follows Python conventions. |
| Security | 2 | Input path is validated (existence check before open). Errors are wrapped in custom exception that does not leak stack traces. No secrets in code. Uses binary mode for TOML reading (correct per spec). |
| Test Quality | 2 | Happy path (valid config), edge cases (empty file, nested structure), error cases (not found, permission denied, malformed TOML). Uses tmp_path fixture for isolation. Cleanup in permission test. Six tests covering all documented behaviors. |

**Total: 10/10**

---

### Gold-Standard Example 2: Score 4/10

**Task:** Same as above — write `parse_config(path: str) -> dict` that reads TOML, handles errors, includes tests.

**Submission:**

```python
# config_parser.py
import tomllib


def parse_config(path):
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data
```

```python
# test_config_parser.py
from config_parser import parse_config


def test_it_works():
    result = parse_config("sample.toml")
    assert isinstance(result, dict)


def test_has_keys():
    result = parse_config("sample.toml")
    assert len(result) > 0
```

**Expected Scoring:**

| Criterion | Score | Evidence |
|---|---|---|
| Correctness | 1 | The function reads valid TOML correctly but crashes with an unhandled FileNotFoundError on missing files, an unhandled PermissionError on unreadable files, and an unhandled TOMLDecodeError on malformed input. The spec requires handling these cases. |
| Completeness | 1 | Core functionality (read TOML, return dict) is present. Error handling for all three specified error types is missing. No custom exception. No docstring. |
| Code Quality | 1 | Function name is appropriate. No type hint on parameter (spec says `path: str`). No docstring. No custom exception. Code is short but not because it is well-designed — it is short because it is incomplete. |
| Security | 0 | No input validation. Unhandled exceptions will propagate raw tracebacks with file paths to the caller. No existence check. Opens arbitrary paths without validation. |
| Test Quality | 1 | Two tests exist but both depend on a hardcoded file `sample.toml` that may not exist in CI. No edge cases, no error cases, no integration tests. Tests verify only that the return type is dict and has keys — they do not verify correctness of parsed values. |

**Total: 4/10**

---

## Inter-Rater Agreement Target

When multiple raters (human or LLM) score the same submission, their scores must converge.

**Target: >80% agreement within 1 point on total score.**

This means: for any given submission, if two calibrated raters independently apply the rubric, their total scores (out of 10) should differ by at most 1 point at least 80% of the time.

### Measuring Agreement

1. Select a set of 10+ submissions that span the score range (at least two each in 0-2, 3-4, 5-6, 7-8, 9-10).
2. Have each rater score all submissions independently using the rubric.
3. Compute pairwise agreement: for each submission, check if the two raters' total scores differ by 0 or 1.
4. Calculate the percentage of submissions where agreement holds.

```
agreements = sum(1 for s in submissions if abs(rater_a[s] - rater_b[s]) <= 1)
agreement_rate = agreements / len(submissions) * 100
```

If agreement is below 80%:
- Review the submissions where raters diverged most.
- Identify which criteria caused the divergence.
- Clarify the rubric definitions for those criteria.
- Re-calibrate and re-test.

## Calibration Workflow

Calibration follows the scientific method (P15: Science as Meta-Loop). Each calibration round is a hypothesis-test cycle.

### Step 1: Hypothesis

Start with a hypothesis about your judge's behavior. For initial calibration, the hypothesis is: "The judge prompt, combined with the rubric, will produce scores within 1 point of gold-standard scores."

For subsequent rounds, the hypothesis addresses a specific issue: "After adding the instruction to penalize padding, the judge will no longer exhibit verbosity bias."

### Step 2: Score

Run the judge against all gold-standard examples. Record the judge's reasoning and scores for each criterion.

```bash
# Example calibration run
calibrate --judge-prompt prompts/judge_v2.txt --gold-standards data/gold/*.json
```

### Step 3: Compare to Gold

For each gold-standard example, compare the judge's scores to the expected scores:

| Example | Expected Total | Judge Total | Per-Criterion Delta |
|---|---|---|---|
| Example 1 (10/10) | 10 | 9 | Security: -1 |
| Example 2 (4/10) | 4 | 6 | Completeness: +1, Test Quality: +1 |

Identify patterns:
- Does the judge consistently over-score or under-score a specific criterion?
- Does the judge agree on high-scoring examples but diverge on low-scoring ones (or vice versa)?
- Do the deltas suggest a specific bias (see [bias-awareness.md](bias-awareness.md))?

### Step 4: Adjust

Based on the comparison, modify the judge prompt to address identified issues. Common adjustments:

| Pattern | Adjustment |
|---|---|
| Over-scores Completeness | Add instruction: "Missing error handling counts as incomplete" |
| Under-scores Security | Add instruction: "Unhandled exceptions that leak paths are a security issue" |
| Scores verbose responses higher | Add instruction: "Shorter correct responses score equal to or higher than longer correct responses" |
| Scores formatted responses higher | Add instruction: "Formatting is not a scoring criterion" |

Each adjustment should be **minimal and targeted**. Change one thing at a time so you can attribute any change in scoring behavior to the specific adjustment.

### Step 5: Repeat

Run the adjusted judge against all gold-standard examples again. Compare to gold. If the judge now agrees within 1 point on all examples, calibration is complete for this round. If not, return to Step 1 with a new hypothesis about the remaining divergence.

### Calibration Cadence

- **On judge prompt creation:** Full calibration before any production use.
- **On judge prompt modification:** Re-run all gold-standard examples.
- **On judge model update:** Full calibration (model behavior may have changed).
- **Weekly during active use:** Spot-check 2-3 gold-standard examples to detect drift.

## Expanding Gold-Standard Examples

The initial two gold-standard examples above are a starting point. As the project matures, expand the set:

1. **Add examples at every score level.** Aim for at least one gold-standard example per 2-point band (0-2, 3-4, 5-6, 7-8, 9-10).
2. **Add bias-testing examples.** Include examples specifically designed to trigger each bias (see [bias-awareness.md](bias-awareness.md)):
   - A short, correct response (tests verbosity bias)
   - A verbose, incorrect response (tests verbosity bias)
   - A well-formatted wrong answer (tests format bias)
   - A plain-text correct answer (tests format bias)
   - A confident wrong answer (tests authority bias)
   - A hedging correct answer (tests authority bias)
3. **Add domain-specific examples.** As the agent system handles new task types, add gold-standard examples for each type.

## References

- [Code Review Rubric](rubrics.md) — The criteria being calibrated
- [Bias Awareness Guide](bias-awareness.md) — Biases that calibration detects and corrects
