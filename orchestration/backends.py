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

import os
from typing import Callable, Protocol, runtime_checkable


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
    "anthropic": "ANTHROPIC_OAUTH_TOKEN",
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
    return cls(model=model)


def available_backends() -> list[str]:
    """Return provider names that have a valid API key set in the environment."""
    return [
        provider
        for provider, env_var in API_KEY_ENV.items()
        if os.environ.get(env_var)
    ]


def backend_as_judge_fn(backend: ModelBackend) -> Callable[[str], str]:
    """Adapt a :class:`ModelBackend` into a ``JudgeFn`` callable.

    The returned callable simply delegates to ``backend.complete()``.
    """
    return backend.complete
