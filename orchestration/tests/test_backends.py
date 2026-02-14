"""Tests for the model backend abstraction.

Tests are written first (P7: Spec / Test / Evals First) and cover:
- Protocol compliance
- Backend registry
- Factory function
- Available backends detection
- Backend-to-judge-fn adapter
- Economy model selection
- Individual backend SDK call shapes (mocked)
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from orchestration.backends import (
    BACKEND_REGISTRY,
    DEFAULT_MODELS,
    ECONOMY_MODELS,
    AnthropicBackend,
    ClaudeCliBackend,
    GoogleBackend,
    ModelBackend,
    OpenAIBackend,
    _run_claude_cli,
    available_backends,
    backend_as_judge_fn,
    create_backend,
)


# ---------------------------------------------------------------------------
# TestModelBackendProtocol
# ---------------------------------------------------------------------------


class TestModelBackendProtocol:
    """Verify that the ModelBackend protocol works with arbitrary implementations."""

    def test_mock_satisfies_protocol(self):
        """An object with a complete(str)->str method satisfies ModelBackend."""

        class _MockBackend:
            def complete(self, prompt: str) -> str:
                return "response"

        backend = _MockBackend()
        assert isinstance(backend, ModelBackend)

    def test_object_without_complete_does_not_satisfy(self):
        """An object without complete() does not satisfy ModelBackend."""

        class _NotABackend:
            pass

        assert not isinstance(_NotABackend(), ModelBackend)

    def test_concrete_backends_satisfy_protocol(self):
        """All registered backend classes satisfy the protocol (structurally)."""
        for cls in BACKEND_REGISTRY.values():
            assert hasattr(cls, "complete")


# ---------------------------------------------------------------------------
# TestBackendRegistry
# ---------------------------------------------------------------------------


class TestBackendRegistry:
    """Tests for BACKEND_REGISTRY."""

    def test_registry_has_three_providers(self):
        assert len(BACKEND_REGISTRY) == 3

    def test_registry_contains_anthropic(self):
        assert "anthropic" in BACKEND_REGISTRY
        assert BACKEND_REGISTRY["anthropic"] is AnthropicBackend

    def test_registry_contains_google(self):
        assert "google" in BACKEND_REGISTRY
        assert BACKEND_REGISTRY["google"] is GoogleBackend

    def test_registry_contains_openai(self):
        assert "openai" in BACKEND_REGISTRY
        assert BACKEND_REGISTRY["openai"] is OpenAIBackend

    def test_registry_values_are_classes(self):
        for cls in BACKEND_REGISTRY.values():
            assert isinstance(cls, type)


# ---------------------------------------------------------------------------
# TestCreateBackend
# ---------------------------------------------------------------------------


class _MockAnthropicModule:
    """Minimal mock for the anthropic SDK module."""

    def __init__(self):
        self.Anthropic = MagicMock()


class _MockGenaiModule:
    """Minimal mock for the google.genai SDK module."""

    def __init__(self):
        self.Client = MagicMock()


class _MockGoogleModule:
    """Mock for 'google' top-level with genai attribute."""

    def __init__(self, genai_mod):
        self.genai = genai_mod


class _MockOpenAIModule:
    """Minimal mock for the openai SDK module."""

    def __init__(self):
        self.OpenAI = MagicMock()


class TestCreateBackend:
    """Tests for the create_backend factory function."""

    def test_create_anthropic_backend(self):
        mock_mod = _MockAnthropicModule()
        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"anthropic": mock_mod}),
        ):
            backend = create_backend("anthropic")
            assert isinstance(backend, AnthropicBackend)

    def test_create_google_backend(self):
        mock_genai = _MockGenaiModule()
        mock_google = _MockGoogleModule(mock_genai)
        with (
            patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}),
            patch.dict(
                "sys.modules",
                {"google": mock_google, "google.genai": mock_genai},
            ),
        ):
            backend = create_backend("google")
            assert isinstance(backend, GoogleBackend)

    def test_create_openai_backend(self):
        mock_mod = _MockOpenAIModule()
        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"openai": mock_mod}),
        ):
            backend = create_backend("openai")
            assert isinstance(backend, OpenAIBackend)

    def test_create_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            create_backend("unknown")


# ---------------------------------------------------------------------------
# TestAvailableBackends
# ---------------------------------------------------------------------------


class TestAvailableBackends:
    """Tests for the available_backends function."""

    @patch.dict(
        "os.environ",
        {"ANTHROPIC_API_KEY": "k1", "GOOGLE_API_KEY": "k2", "OPENAI_API_KEY": "k3"},
    )
    def test_all_available_when_all_keys_set(self):
        result = available_backends()
        assert "anthropic" in result
        assert "google" in result
        assert "openai" in result

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "k1"}, clear=True)
    def test_only_anthropic_when_only_its_key_set(self):
        result = available_backends()
        assert result == ["anthropic"]

    @patch("shutil.which", return_value=None)
    @patch.dict("os.environ", {}, clear=True)
    def test_empty_when_no_keys_and_no_cli(self, _mock_which):
        result = available_backends()
        assert result == []

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch.dict("os.environ", {}, clear=True)
    def test_anthropic_available_via_claude_cli(self, _mock_which):
        result = available_backends()
        assert "anthropic" in result

    @patch("shutil.which", return_value=None)
    @patch.dict(
        "os.environ",
        {"GOOGLE_API_KEY": "k2", "OPENAI_API_KEY": "k3"},
        clear=True,
    )
    def test_excludes_provider_without_key_or_cli(self, _mock_which):
        result = available_backends()
        assert "anthropic" not in result
        assert "google" in result
        assert "openai" in result


# ---------------------------------------------------------------------------
# TestBackendAsJudgeFn
# ---------------------------------------------------------------------------


class TestBackendAsJudgeFn:
    """Tests for backend_as_judge_fn adapter."""

    def test_adapts_backend_to_callable(self):
        mock_backend = MagicMock(spec=ModelBackend)
        mock_backend.complete.return_value = "judge response"

        judge_fn = backend_as_judge_fn(mock_backend)
        result = judge_fn("prompt text")

        assert result == "judge response"
        mock_backend.complete.assert_called_once_with("prompt text")

    def test_returned_callable_is_callable(self):
        mock_backend = MagicMock(spec=ModelBackend)
        judge_fn = backend_as_judge_fn(mock_backend)
        assert callable(judge_fn)

    def test_passes_through_prompt_exactly(self):
        mock_backend = MagicMock(spec=ModelBackend)
        mock_backend.complete.return_value = ""

        judge_fn = backend_as_judge_fn(mock_backend)
        judge_fn("exact prompt")

        mock_backend.complete.assert_called_with("exact prompt")


# ---------------------------------------------------------------------------
# TestEconomyModels
# ---------------------------------------------------------------------------


class TestEconomyModels:
    """Tests for economy model selection."""

    def test_economy_models_dict_has_all_providers(self):
        for provider in BACKEND_REGISTRY:
            assert provider in ECONOMY_MODELS

    def test_economy_models_differ_from_defaults(self):
        """Economy models should be cheaper alternatives (at least for anthropic/openai)."""
        assert ECONOMY_MODELS["anthropic"] != DEFAULT_MODELS["anthropic"]
        assert ECONOMY_MODELS["openai"] != DEFAULT_MODELS["openai"]

    def test_economy_flag_selects_economy_model(self):
        mock_mod = _MockAnthropicModule()
        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"anthropic": mock_mod}),
        ):
            backend = create_backend("anthropic", economy=True)
            assert backend.model == ECONOMY_MODELS["anthropic"]

    def test_explicit_model_overrides_economy(self):
        mock_mod = _MockAnthropicModule()
        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"anthropic": mock_mod}),
        ):
            backend = create_backend("anthropic", model="custom-model", economy=True)
            assert backend.model == "custom-model"

    def test_no_economy_uses_default_model(self):
        mock_mod = _MockAnthropicModule()
        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"anthropic": mock_mod}),
        ):
            backend = create_backend("anthropic")
            assert backend.model == DEFAULT_MODELS["anthropic"]


# ---------------------------------------------------------------------------
# TestAnthropicBackend
# ---------------------------------------------------------------------------


class TestAnthropicBackend:
    """Tests for AnthropicBackend with mocked SDK."""

    def test_complete_calls_messages_create(self):
        mock_mod = _MockAnthropicModule()
        mock_client = MagicMock()
        mock_mod.Anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="response text")]
        mock_client.messages.create.return_value = mock_message

        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"anthropic": mock_mod}),
        ):
            backend = AnthropicBackend()
            result = backend.complete("test prompt")

        mock_client.messages.create.assert_called_once_with(
            model=DEFAULT_MODELS["anthropic"],
            max_tokens=1024,
            messages=[{"role": "user", "content": "test prompt"}],
        )
        assert result == "response text"

    def test_uses_custom_model(self):
        mock_mod = _MockAnthropicModule()
        mock_client = MagicMock()
        mock_mod.Anthropic.return_value = mock_client
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="ok")]
        mock_client.messages.create.return_value = mock_message

        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"anthropic": mock_mod}),
        ):
            backend = AnthropicBackend(model="claude-custom")
            backend.complete("p")

        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-custom"

    @patch.dict("os.environ", {}, clear=True)
    def test_raises_without_api_key(self):
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            AnthropicBackend()


# ---------------------------------------------------------------------------
# TestGoogleBackend
# ---------------------------------------------------------------------------


class TestGoogleBackend:
    """Tests for GoogleBackend with mocked SDK."""

    def _make_mocks(self):
        mock_genai = _MockGenaiModule()
        mock_google = _MockGoogleModule(mock_genai)
        return mock_google, mock_genai

    def test_complete_calls_generate_content(self):
        mock_google, mock_genai = self._make_mocks()
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "generated text"
        mock_client.models.generate_content.return_value = mock_response

        with (
            patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}),
            patch.dict(
                "sys.modules",
                {"google": mock_google, "google.genai": mock_genai},
            ),
        ):
            backend = GoogleBackend()
            result = backend.complete("test prompt")

        mock_client.models.generate_content.assert_called_once_with(
            model=DEFAULT_MODELS["google"],
            contents="test prompt",
        )
        assert result == "generated text"

    def test_uses_custom_model(self):
        mock_google, mock_genai = self._make_mocks()
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_client.models.generate_content.return_value = mock_response

        with (
            patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}),
            patch.dict(
                "sys.modules",
                {"google": mock_google, "google.genai": mock_genai},
            ),
        ):
            backend = GoogleBackend(model="gemini-custom")
            backend.complete("p")

        call_kwargs = mock_client.models.generate_content.call_args
        assert call_kwargs.kwargs["model"] == "gemini-custom"

    @patch.dict("os.environ", {}, clear=True)
    def test_raises_without_api_key(self):
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            GoogleBackend()


# ---------------------------------------------------------------------------
# TestOpenAIBackend
# ---------------------------------------------------------------------------


class TestOpenAIBackend:
    """Tests for OpenAIBackend with mocked SDK."""

    def test_complete_calls_chat_completions(self):
        mock_mod = _MockOpenAIModule()
        mock_client = MagicMock()
        mock_mod.OpenAI.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = "completion text"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"openai": mock_mod}),
        ):
            backend = OpenAIBackend()
            result = backend.complete("test prompt")

        mock_client.chat.completions.create.assert_called_once_with(
            model=DEFAULT_MODELS["openai"],
            messages=[{"role": "user", "content": "test prompt"}],
        )
        assert result == "completion text"

    def test_uses_custom_model(self):
        mock_mod = _MockOpenAIModule()
        mock_client = MagicMock()
        mock_mod.OpenAI.return_value = mock_client
        mock_choice = MagicMock()
        mock_choice.message.content = "ok"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"openai": mock_mod}),
        ):
            backend = OpenAIBackend(model="gpt-custom")
            backend.complete("p")

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "gpt-custom"

    @patch.dict("os.environ", {}, clear=True)
    def test_raises_without_api_key(self):
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            OpenAIBackend()


# ---------------------------------------------------------------------------
# TestClaudeCliBackend
# ---------------------------------------------------------------------------


def _make_mock_popen(
    stdout_lines: list[str],
    returncode: int = 0,
    stderr_text: str = "",
):
    """Create a mock Popen that yields stdout_lines and returns the given code."""
    mock_proc = MagicMock()
    mock_proc.stdout = iter(stdout_lines)
    mock_proc.stderr = MagicMock()
    mock_proc.stderr.read.return_value = stderr_text
    mock_proc.returncode = returncode
    mock_proc.wait.return_value = returncode
    return mock_proc


class TestClaudeCliBackend:
    """Tests for ClaudeCliBackend with mocked subprocess."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_init_succeeds_when_claude_in_path(self, _mock_which):
        backend = ClaudeCliBackend()
        assert backend.model == DEFAULT_MODELS["anthropic"]

    @patch("shutil.which", return_value=None)
    def test_init_raises_when_claude_not_in_path(self, _mock_which):
        with pytest.raises(ValueError, match="claude CLI not found"):
            ClaudeCliBackend()

    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_uses_custom_model(self, _mock_which):
        backend = ClaudeCliBackend(model="claude-custom")
        assert backend.model == "claude-custom"

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("orchestration.backends.subprocess.Popen")
    def test_complete_calls_claude_cli(self, mock_popen, _mock_which):
        result_event = json.dumps({
            "type": "result",
            "result": "cli response",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        })
        mock_popen.return_value = _make_mock_popen([result_event + "\n"])
        backend = ClaudeCliBackend()
        result = backend.complete("test prompt")

        assert result == "cli response"
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert cmd[0] == "claude"
        assert "-p" in cmd
        assert "test prompt" in cmd

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("orchestration.backends.subprocess.Popen")
    def test_complete_raises_on_cli_failure(self, mock_popen, _mock_which):
        mock_popen.return_value = _make_mock_popen(
            [], returncode=1, stderr_text="error occurred",
        )
        backend = ClaudeCliBackend()
        with pytest.raises(RuntimeError, match="claude CLI failed"):
            backend.complete("test prompt")


# ---------------------------------------------------------------------------
# TestRunClaudeCli
# ---------------------------------------------------------------------------


class TestRunClaudeCli:
    """Tests for the _run_claude_cli helper."""

    def _result_line(self, text="ok", input_tokens=10, output_tokens=5):
        return json.dumps({
            "type": "result",
            "result": text,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        }) + "\n"

    @patch("orchestration.backends.subprocess.Popen")
    def test_passes_model_flag(self, mock_popen):
        mock_popen.return_value = _make_mock_popen([self._result_line()])
        _run_claude_cli("prompt", model="sonnet")
        cmd = mock_popen.call_args[0][0]
        assert "--model" in cmd
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "sonnet"

    @patch("orchestration.backends.subprocess.Popen")
    def test_passes_system_prompt_flag(self, mock_popen):
        mock_popen.return_value = _make_mock_popen([self._result_line()])
        _run_claude_cli("prompt", system_prompt="You are helpful.")
        cmd = mock_popen.call_args[0][0]
        assert "--system-prompt" in cmd
        idx = cmd.index("--system-prompt")
        assert cmd[idx + 1] == "You are helpful."

    @patch("orchestration.backends.subprocess.Popen")
    def test_unsets_claudecode_env(self, mock_popen):
        mock_popen.return_value = _make_mock_popen([self._result_line()])
        _run_claude_cli("prompt")
        env = mock_popen.call_args[1]["env"]
        assert env["CLAUDECODE"] == ""

    @patch("orchestration.backends.subprocess.Popen")
    def test_uses_stream_json_format(self, mock_popen):
        mock_popen.return_value = _make_mock_popen([self._result_line()])
        _run_claude_cli("prompt")
        cmd = mock_popen.call_args[0][0]
        assert "--output-format" in cmd
        idx = cmd.index("--output-format")
        assert cmd[idx + 1] == "stream-json"

    @patch("orchestration.backends.subprocess.Popen")
    def test_returns_dict_with_result_and_tokens(self, mock_popen):
        mock_popen.return_value = _make_mock_popen([
            self._result_line("hello", 100, 50),
        ])
        result = _run_claude_cli("prompt")
        assert isinstance(result, dict)
        assert result["result"] == "hello"
        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 50

    @patch("orchestration.backends.subprocess.Popen")
    def test_handles_non_json_lines(self, mock_popen):
        mock_popen.return_value = _make_mock_popen([
            "not json\n",
            self._result_line("ok"),
        ])
        result = _run_claude_cli("prompt")
        assert result["result"] == "ok"

    @patch("orchestration.backends.subprocess.Popen")
    def test_passes_allowed_tools_flag(self, mock_popen):
        mock_popen.return_value = _make_mock_popen([self._result_line()])
        _run_claude_cli("prompt", allowed_tools=["Bash", "Write"])
        cmd = mock_popen.call_args[0][0]
        assert "--allowedTools" in cmd
        idx = cmd.index("--allowedTools")
        assert cmd[idx + 1] == "Bash,Write"

    @patch("orchestration.backends.subprocess.Popen")
    def test_no_allowed_tools_flag_when_none(self, mock_popen):
        mock_popen.return_value = _make_mock_popen([self._result_line()])
        _run_claude_cli("prompt")
        cmd = mock_popen.call_args[0][0]
        assert "--allowedTools" not in cmd

    @patch("orchestration.backends.subprocess.Popen")
    def test_on_event_callback(self, mock_popen):
        events = []
        mock_popen.return_value = _make_mock_popen([
            json.dumps({"type": "progress", "data": "working"}) + "\n",
            self._result_line(),
        ])
        _run_claude_cli("prompt", on_event=lambda e: events.append(e))
        assert len(events) == 2
        assert events[0]["type"] == "progress"
        assert events[1]["type"] == "result"


# ---------------------------------------------------------------------------
# TestCreateBackendFallback
# ---------------------------------------------------------------------------


class TestCreateBackendFallback:
    """Tests for create_backend falling back to ClaudeCliBackend."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch.dict("os.environ", {}, clear=True)
    def test_anthropic_falls_back_to_cli(self, _mock_which):
        backend = create_backend("anthropic")
        assert isinstance(backend, ClaudeCliBackend)

    @patch("shutil.which", return_value=None)
    @patch.dict("os.environ", {}, clear=True)
    def test_anthropic_raises_when_no_key_and_no_cli(self, _mock_which):
        with pytest.raises(ValueError, match="claude CLI not found"):
            create_backend("anthropic")

    @patch.dict("os.environ", {}, clear=True)
    def test_google_does_not_fall_back(self):
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            create_backend("google")
