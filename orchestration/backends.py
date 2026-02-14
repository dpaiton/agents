"""Model backend abstraction for multi-model ensemble evaluation.

Provides a common interface (ModelBackend protocol) for calling different LLM
providers. Each backend wraps a single provider SDK and exposes a simple
``complete(prompt) -> str`` method.

Design Principles:
- P4 Scaffolding > Model: The value is in the uniform interface, not the model.
- P5 Deterministic Infrastructure: Registry and factory are pure Python.
- P8 UNIX Philosophy: Each backend does one thing (complete a prompt).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from typing import Callable, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class ModelBackend(Protocol):
    """Protocol for model backends.

    Any class implementing ``complete(prompt: str) -> str`` satisfies this
    protocol.  Backends are intentionally simple -- they take a prompt string
    and return the model's text response.
    """

    def complete(self, prompt: str) -> str: ...


# ---------------------------------------------------------------------------
# Economy model defaults (cheaper / faster alternatives)
# ---------------------------------------------------------------------------

ECONOMY_MODELS: dict[str, str] = {
    "anthropic": "claude-haiku-4-20250414",
    "google": "gemini-2.0-flash",
    "openai": "gpt-4o-mini",
}

# ---------------------------------------------------------------------------
# Default (standard) models per provider
# ---------------------------------------------------------------------------

DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-20250514",
    "google": "gemini-2.0-flash",
    "openai": "gpt-4o",
}

# ---------------------------------------------------------------------------
# API key environment variable names per provider
# ---------------------------------------------------------------------------

API_KEY_ENV: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
}


# ---------------------------------------------------------------------------
# Concrete backend implementations
# ---------------------------------------------------------------------------

class AnthropicBackend:
    """Backend using the Anthropic SDK (Claude models)."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or DEFAULT_MODELS["anthropic"]
        api_key = os.environ.get(API_KEY_ENV["anthropic"])
        if not api_key:
            raise ValueError(
                f"Missing {API_KEY_ENV['anthropic']} environment variable"
            )
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(self, prompt: str) -> str:
        message = self._client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text


class ClaudeCliBackend:
    """Backend using the ``claude`` CLI in print mode.

    Falls back to the Claude Code CLI (``claude -p``) when no Anthropic API key
    is available.  The CLI handles OAuth authentication natively.
    """

    def __init__(self, model: str | None = None) -> None:
        self.model = model or DEFAULT_MODELS["anthropic"]
        if not shutil.which("claude"):
            raise ValueError(
                "claude CLI not found in PATH — install Claude Code"
            )

    def complete(self, prompt: str) -> str:
        result = _run_claude_cli(prompt, model=self.model)
        return result["result"]


def _run_claude_cli(
    prompt: str,
    model: str | None = None,
    system_prompt: str | None = None,
    allowed_tools: list[str] | None = None,
    on_event: Callable[[dict], None] | None = None,
) -> dict:
    """Run the ``claude`` CLI in print mode with streaming NDJSON output.

    Args:
        prompt: The user prompt.
        model: Model name to use.
        system_prompt: Optional system prompt.
        allowed_tools: List of tool names to allow (e.g. ``["Bash", "Write"]``).
        on_event: Optional callback invoked for each NDJSON event line.

    Returns:
        A dict with keys ``result`` (str), ``input_tokens`` (int),
        ``output_tokens`` (int).

    Raises:
        RuntimeError: If the CLI invocation fails.
    """
    cmd = ["claude", "-p", "--output-format", "stream-json"]
    if model:
        cmd.extend(["--model", model])
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])
    if allowed_tools:
        cmd.extend(["--allowedTools", ",".join(allowed_tools)])
    cmd.append(prompt)

    # Allow running from within a Claude Code session
    env = {**os.environ, "CLAUDECODE": ""}

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    result_text = ""
    input_tokens = 0
    output_tokens = 0

    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        if on_event is not None:
            on_event(event)

        if event.get("type") == "result":
            result_text = event.get("result", "")
            usage = event.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

    proc.wait()

    if proc.returncode != 0:
        stderr_output = proc.stderr.read() if proc.stderr else ""
        raise RuntimeError(
            f"claude CLI failed (exit {proc.returncode}): {stderr_output}"
        )

    return {
        "result": result_text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


class GoogleBackend:
    """Backend using the Google GenAI SDK (Gemini models)."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or DEFAULT_MODELS["google"]
        api_key = os.environ.get(API_KEY_ENV["google"])
        if not api_key:
            raise ValueError(
                f"Missing {API_KEY_ENV['google']} environment variable"
            )
        from google import genai

        self._client = genai.Client(api_key=api_key)

    def complete(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return response.text


class OpenAIBackend:
    """Backend using the OpenAI SDK (GPT models)."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or DEFAULT_MODELS["openai"]
        api_key = os.environ.get(API_KEY_ENV["openai"])
        if not api_key:
            raise ValueError(
                f"Missing {API_KEY_ENV['openai']} environment variable"
            )
        import openai

        self._client = openai.OpenAI(api_key=api_key)

    def complete(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Registry & factory
# ---------------------------------------------------------------------------

BACKEND_REGISTRY: dict[str, type[ModelBackend]] = {
    "anthropic": AnthropicBackend,
    "google": GoogleBackend,
    "openai": OpenAIBackend,
}


def create_backend(
    provider: str,
    model: str | None = None,
    economy: bool = False,
) -> ModelBackend:
    """Create a model backend for the given provider.

    For the ``"anthropic"`` provider, tries the SDK backend first (requires
    ``ANTHROPIC_API_KEY``).  If the key is missing, falls back to the
    ``claude`` CLI which handles OAuth authentication natively.

    Args:
        provider: Provider name (``"anthropic"``, ``"google"``, ``"openai"``).
        model: Override model name.  If ``None``, uses the default (or economy
            default when *economy* is ``True``).
        economy: When ``True`` and *model* is ``None``, selects a cheaper model.

    Returns:
        An instance satisfying the :class:`ModelBackend` protocol.

    Raises:
        ValueError: If *provider* is not in :data:`BACKEND_REGISTRY`.
    """
    if provider not in BACKEND_REGISTRY:
        raise ValueError(
            f"Unknown provider: {provider!r}. "
            f"Available: {', '.join(sorted(BACKEND_REGISTRY))}"
        )

    if model is None and economy:
        model = ECONOMY_MODELS.get(provider)

    cls = BACKEND_REGISTRY[provider]
    try:
        return cls(model=model)
    except (ValueError, ImportError):
        if provider == "anthropic":
            logger.info("ANTHROPIC_API_KEY not set, falling back to claude CLI")
            return ClaudeCliBackend(model=model)
        raise


def available_backends() -> list[str]:
    """Return provider names that have a usable backend.

    For Anthropic, this includes the ``claude`` CLI fallback.
    """
    available = []
    for provider, env_var in API_KEY_ENV.items():
        if os.environ.get(env_var):
            available.append(provider)
        elif provider == "anthropic" and shutil.which("claude"):
            available.append(provider)
    return available


def backend_as_judge_fn(backend: ModelBackend) -> Callable[[str], str]:
    """Adapt a :class:`ModelBackend` into a ``JudgeFn`` callable.

    The returned callable simply delegates to ``backend.complete()``.
    """
    return backend.complete
