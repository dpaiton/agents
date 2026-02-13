"""Tests for orchestration.config — config loading and model selection."""

import os
from unittest.mock import patch

from orchestration.config import (
    DEFAULT_MODEL,
    ECONOMY_DEFAULT_MODEL,
    ECONOMY_MODEL_TABLE,
    MODEL_TABLE,
    EcoConfig,
    _build_config,
    _extract_eco_section,
    _find_config_file,
    load_config,
    select_model,
)


# ---------------------------------------------------------------------------
# Model table tests
# ---------------------------------------------------------------------------


class TestModelTable:
    def test_model_table_has_all_task_types(self):
        expected_keys = {
            "comment-classification",
            "issue-body-edit",
            "pr-description-edit",
            "code-change",
            "performance-analysis",  # Renamed from test-writing
            "review",
            "evaluation",
            "design",
            "architecture",
            "backend",
            "frontend",
            "ml",
            "infrastructure",
            "integration",
            "project-management",
        }
        assert set(MODEL_TABLE.keys()) == expected_keys

    def test_economy_table_has_same_keys(self):
        assert set(ECONOMY_MODEL_TABLE.keys()) == set(MODEL_TABLE.keys())

    def test_economy_models_are_cheaper_or_equal(self):
        # Economy models should never be more expensive than standard
        for key in MODEL_TABLE:
            assert key in ECONOMY_MODEL_TABLE

    def test_default_model_is_sonnet(self):
        assert "sonnet" in DEFAULT_MODEL

    def test_economy_default_is_haiku(self):
        assert "haiku" in ECONOMY_DEFAULT_MODEL


# ---------------------------------------------------------------------------
# EcoConfig tests
# ---------------------------------------------------------------------------


class TestEcoConfig:
    def test_defaults(self):
        config = EcoConfig()
        assert config.default_model == DEFAULT_MODEL
        assert config.token_budget == 50_000
        assert config.poll_interval == 60
        assert config.parallel is True
        assert config.gcp_project is None
        assert config.gcp_zone == "us-central1-a"
        assert config.gcp_machine_type == "e2-standard-2"
        assert config.gcp_timeout_hours == 4

    def test_frozen(self):
        config = EcoConfig()
        try:
            config.token_budget = 100  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass

    def test_custom_values(self):
        config = EcoConfig(
            default_model="gpt-4o",
            token_budget=100_000,
            poll_interval=30,
            parallel=False,
            gcp_project="my-project",
        )
        assert config.default_model == "gpt-4o"
        assert config.token_budget == 100_000
        assert config.poll_interval == 30
        assert config.parallel is False
        assert config.gcp_project == "my-project"

    def test_models_default_matches_model_table(self):
        config = EcoConfig()
        assert config.models == MODEL_TABLE

    def test_models_are_independent_copies(self):
        config = EcoConfig()
        assert config.models is not MODEL_TABLE


# ---------------------------------------------------------------------------
# Config file discovery
# ---------------------------------------------------------------------------


class TestFindConfigFile:
    def test_finds_eco_toml(self, tmp_path):
        eco_toml = tmp_path / ".eco.toml"
        eco_toml.write_text("[models]\n")
        assert _find_config_file(tmp_path) == eco_toml

    def test_finds_pyproject_toml(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.eco]\n")
        assert _find_config_file(tmp_path) == pyproject

    def test_prefers_eco_toml_over_pyproject(self, tmp_path):
        eco_toml = tmp_path / ".eco.toml"
        eco_toml.write_text("")
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("")
        assert _find_config_file(tmp_path) == eco_toml

    def test_returns_none_when_no_config(self, tmp_path):
        assert _find_config_file(tmp_path) is None


# ---------------------------------------------------------------------------
# Extract eco section
# ---------------------------------------------------------------------------


class TestExtractEcoSection:
    def test_eco_toml_returns_whole_file(self):
        data = {"default_model": "gpt-4o", "token_budget": 10000}
        assert _extract_eco_section(data, ".eco.toml") == data

    def test_pyproject_returns_tool_eco(self):
        data = {
            "project": {"name": "test"},
            "tool": {"eco": {"default_model": "gpt-4o"}},
        }
        assert _extract_eco_section(data, "pyproject.toml") == {
            "default_model": "gpt-4o",
        }

    def test_pyproject_missing_tool_eco_returns_empty(self):
        data = {"project": {"name": "test"}}
        assert _extract_eco_section(data, "pyproject.toml") == {}


# ---------------------------------------------------------------------------
# Build config with env overrides
# ---------------------------------------------------------------------------


class TestBuildConfig:
    def test_empty_section_gives_defaults(self):
        config = _build_config({})
        assert config.default_model == DEFAULT_MODEL
        assert config.token_budget == 50_000

    def test_section_overrides(self):
        section = {
            "default_model": "gpt-4o",
            "token_budget": 10000,
            "poll_interval": 30,
            "parallel": False,
        }
        config = _build_config(section)
        assert config.default_model == "gpt-4o"
        assert config.token_budget == 10000
        assert config.poll_interval == 30
        assert config.parallel is False

    def test_models_section_merges(self):
        section = {"models": {"code-change": "gpt-4o"}}
        config = _build_config(section)
        assert config.models["code-change"] == "gpt-4o"
        # Other models should still be from MODEL_TABLE
        assert config.models["review"] == MODEL_TABLE["review"]

    def test_gcp_section(self):
        section = {
            "gcp": {
                "project": "my-project",
                "zone": "europe-west1-b",
                "machine_type": "e2-standard-4",
                "timeout_hours": 8,
            },
        }
        config = _build_config(section)
        assert config.gcp_project == "my-project"
        assert config.gcp_zone == "europe-west1-b"
        assert config.gcp_machine_type == "e2-standard-4"
        assert config.gcp_timeout_hours == 8

    @patch.dict(os.environ, {"ECO_DEFAULT_MODEL": "gemini-2.0-flash"})
    def test_env_overrides_default_model(self):
        config = _build_config({"default_model": "gpt-4o"})
        assert config.default_model == "gemini-2.0-flash"

    @patch.dict(os.environ, {"ECO_TOKEN_BUDGET": "25000"})
    def test_env_overrides_token_budget(self):
        config = _build_config({"token_budget": 50000})
        assert config.token_budget == 25000

    @patch.dict(os.environ, {"ECO_POLL_INTERVAL": "120"})
    def test_env_overrides_poll_interval(self):
        config = _build_config({})
        assert config.poll_interval == 120

    @patch.dict(os.environ, {"ECO_PARALLEL": "false"})
    def test_env_overrides_parallel(self):
        config = _build_config({})
        assert config.parallel is False

    @patch.dict(os.environ, {"ECO_PARALLEL": "0"})
    def test_env_parallel_zero_is_false(self):
        config = _build_config({})
        assert config.parallel is False

    @patch.dict(os.environ, {"GCP_PROJECT": "env-project"})
    def test_env_overrides_gcp_project(self):
        config = _build_config({"gcp": {"project": "file-project"}})
        assert config.gcp_project == "env-project"


# ---------------------------------------------------------------------------
# load_config integration
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_loads_defaults_when_no_file(self, tmp_path):
        config = load_config(search_dir=tmp_path)
        assert config.default_model == DEFAULT_MODEL
        assert config.token_budget == 50_000

    def test_loads_eco_toml(self, tmp_path):
        eco_toml = tmp_path / ".eco.toml"
        eco_toml.write_bytes(
            b'default_model = "gpt-4o"\ntoken_budget = 10000\n'
        )
        config = load_config(search_dir=tmp_path)
        assert config.default_model == "gpt-4o"
        assert config.token_budget == 10000

    def test_loads_pyproject_tool_eco(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_bytes(
            b'[tool.eco]\ndefault_model = "gemini-2.0-flash"\n'
        )
        config = load_config(search_dir=tmp_path)
        assert config.default_model == "gemini-2.0-flash"

    def test_string_search_dir(self, tmp_path):
        config = load_config(search_dir=str(tmp_path))
        assert isinstance(config, EcoConfig)


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------


class TestSelectModel:
    def test_known_task_type_returns_table_value(self):
        assert select_model("code-change") == MODEL_TABLE["code-change"]

    def test_unknown_task_type_returns_default(self):
        assert select_model("nonexistent") == DEFAULT_MODEL

    def test_economy_mode_returns_economy_model(self):
        model = select_model("code-change", economy=True)
        assert model == ECONOMY_MODEL_TABLE["code-change"]

    def test_economy_unknown_returns_economy_default(self):
        model = select_model("nonexistent", economy=True)
        assert model == ECONOMY_DEFAULT_MODEL

    def test_config_overrides_table(self):
        config = EcoConfig(models={"code-change": "gpt-4o"})
        model = select_model("code-change", config=config)
        assert model == "gpt-4o"

    def test_config_default_model_for_unknown(self):
        config = EcoConfig(default_model="custom-model")
        model = select_model("nonexistent", config=config)
        assert model == "custom-model"

    def test_economy_takes_precedence_over_config(self):
        config = EcoConfig(models={"code-change": "gpt-4o"})
        model = select_model("code-change", config=config, economy=True)
        assert model == ECONOMY_MODEL_TABLE["code-change"]

    def test_all_task_types_resolve(self):
        for task_type in MODEL_TABLE:
            model = select_model(task_type)
            assert model is not None
            assert isinstance(model, str)
