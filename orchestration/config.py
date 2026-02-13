"""Configuration system for the orchestration framework.

Loads config from ``.eco.toml`` or ``pyproject.toml`` ``[tool.eco]`` section.
Provides deterministic model selection based on task type (P5, P6).

Design Principles:
- P5 Deterministic Infrastructure: Model selection is a code lookup table
- P6 Code Before Prompts: Config parsing and model selection are pure Python
- P8 UNIX Philosophy: Config files are standard TOML, composable with other tools
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Model selection table — deterministic based on task type (P5, P6)
# ---------------------------------------------------------------------------

MODEL_TABLE: dict[str, str] = {
    "comment-classification": "claude-haiku-3-5-20241022",
    "issue-body-edit": "claude-haiku-3-5-20241022",
    "pr-description-edit": "claude-haiku-3-5-20241022",
    "code-change": "claude-sonnet-4-20250514",
    "performance-analysis": "claude-sonnet-4-20250514",  # Renamed from test-writing
    "review": "claude-sonnet-4-20250514",
    "evaluation": "claude-opus-4-20250514",
    "design": "claude-sonnet-4-20250514",
    "architecture": "claude-sonnet-4-20250514",
    "backend": "claude-sonnet-4-20250514",
    "frontend": "claude-sonnet-4-20250514",
    "ml": "claude-sonnet-4-20250514",  # Could use Opus for complex ML architecture
    "infrastructure": "claude-sonnet-4-20250514",
    "integration": "claude-sonnet-4-20250514",
    "project-management": "claude-haiku-3-5-20241022",  # Efficiency focus
}

DEFAULT_MODEL = "claude-sonnet-4-20250514"

# Economy mode overrides — cheaper models per task type
ECONOMY_MODEL_TABLE: dict[str, str] = {
    "comment-classification": "claude-haiku-3-5-20241022",
    "issue-body-edit": "claude-haiku-3-5-20241022",
    "pr-description-edit": "claude-haiku-3-5-20241022",
    "code-change": "claude-haiku-3-5-20241022",
    "performance-analysis": "claude-haiku-3-5-20241022",  # Renamed from test-writing
    "review": "claude-haiku-3-5-20241022",
    "evaluation": "claude-sonnet-4-20250514",
    "design": "claude-haiku-3-5-20241022",
    "architecture": "claude-haiku-3-5-20241022",
    "backend": "claude-haiku-3-5-20241022",
    "frontend": "claude-haiku-3-5-20241022",
    "ml": "claude-haiku-3-5-20241022",
    "infrastructure": "claude-haiku-3-5-20241022",
    "integration": "claude-haiku-3-5-20241022",
    "project-management": "claude-haiku-3-5-20241022",
}

ECONOMY_DEFAULT_MODEL = "claude-haiku-3-5-20241022"


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EcoConfig:
    """Configuration for eco execution.

    Attributes:
        default_model: Fallback model when task type is not in the table.
        token_budget: Maximum tokens per run (0 = unlimited).
        poll_interval: Seconds between polls in watch mode.
        parallel: Whether to process independent tasks in parallel.
        models: Task-type to model mapping (overrides MODEL_TABLE).
        gcp_project: GCP project ID for remote execution.
        gcp_zone: GCP zone for remote instances.
        gcp_machine_type: GCP machine type.
        gcp_timeout_hours: Auto-shutdown timeout in hours.
    """

    default_model: str = DEFAULT_MODEL
    token_budget: int = 50_000
    poll_interval: int = 60
    parallel: bool = True
    models: dict[str, str] = field(default_factory=lambda: dict(MODEL_TABLE))
    gcp_project: str | None = None
    gcp_zone: str = "us-central1-a"
    gcp_machine_type: str = "e2-standard-2"
    gcp_timeout_hours: int = 4


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def _find_config_file(search_dir: Path) -> Path | None:
    """Search for .eco.toml or pyproject.toml starting from *search_dir*."""
    for name in (".eco.toml", "pyproject.toml"):
        candidate = search_dir / name
        if candidate.is_file():
            return candidate
    return None


def _parse_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file and return the raw dict."""
    if tomllib is None:
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def _extract_eco_section(data: dict[str, Any], filename: str) -> dict[str, Any]:
    """Extract the eco config section from parsed TOML data.

    For ``.eco.toml``, the entire file is the eco section.
    For ``pyproject.toml``, look under ``[tool.eco]``.
    """
    if filename == ".eco.toml":
        return data
    # pyproject.toml → [tool][eco]
    return data.get("tool", {}).get("eco", {})


def _build_config(section: dict[str, Any]) -> EcoConfig:
    """Build an EcoConfig from a parsed TOML section, with env overrides."""
    models = dict(MODEL_TABLE)
    if "models" in section and isinstance(section["models"], dict):
        models.update(section["models"])

    default_model = os.environ.get(
        "ECO_DEFAULT_MODEL",
        section.get("default_model", DEFAULT_MODEL),
    )

    token_budget_str = os.environ.get("ECO_TOKEN_BUDGET")
    token_budget = (
        int(token_budget_str)
        if token_budget_str is not None
        else section.get("token_budget", 50_000)
    )

    poll_interval_str = os.environ.get("ECO_POLL_INTERVAL")
    poll_interval = (
        int(poll_interval_str)
        if poll_interval_str is not None
        else section.get("poll_interval", 60)
    )

    parallel_str = os.environ.get("ECO_PARALLEL")
    if parallel_str is not None:
        parallel = parallel_str.lower() not in ("0", "false", "no")
    else:
        parallel = section.get("parallel", True)

    gcp = section.get("gcp", {})

    return EcoConfig(
        default_model=default_model,
        token_budget=token_budget,
        poll_interval=poll_interval,
        parallel=parallel,
        models=models,
        gcp_project=os.environ.get("GCP_PROJECT", gcp.get("project")),
        gcp_zone=os.environ.get("GCP_ZONE", gcp.get("zone", "us-central1-a")),
        gcp_machine_type=os.environ.get(
            "GCP_MACHINE_TYPE", gcp.get("machine_type", "e2-standard-2"),
        ),
        gcp_timeout_hours=int(
            os.environ.get(
                "GCP_TIMEOUT_HOURS",
                gcp.get("timeout_hours", 4),
            )
        ),
    )


def load_config(search_dir: str | Path | None = None) -> EcoConfig:
    """Load configuration from .eco.toml or pyproject.toml [tool.eco].

    Search order:
    1. ``search_dir`` (default: cwd)
    2. Environment variable overrides (ECO_DEFAULT_MODEL, ECO_TOKEN_BUDGET, etc.)
    3. Defaults from EcoConfig

    Returns:
        An EcoConfig instance.
    """
    if search_dir is None:
        search_dir = Path.cwd()
    else:
        search_dir = Path(search_dir)

    config_file = _find_config_file(search_dir)
    if config_file is None:
        return _build_config({})

    data = _parse_toml(config_file)
    section = _extract_eco_section(data, config_file.name)
    return _build_config(section)


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------

def select_model(
    task_type: str,
    config: EcoConfig | None = None,
    economy: bool = False,
) -> str:
    """Select the model for a given task type.

    Uses the deterministic model table (P5). Economy mode selects
    cheaper models for cost efficiency.

    Args:
        task_type: The task type key (e.g. "code-change", "review").
        config: Optional config with custom model overrides.
        economy: If True, use economy model table.

    Returns:
        The model identifier string.
    """
    if economy:
        table = ECONOMY_MODEL_TABLE
        default = ECONOMY_DEFAULT_MODEL
    elif config is not None:
        table = config.models
        default = config.default_model
    else:
        table = MODEL_TABLE
        default = DEFAULT_MODEL

    return table.get(task_type, default)
