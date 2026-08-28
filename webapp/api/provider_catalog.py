"""Small provider preset catalog for the local-only settings screen."""

from __future__ import annotations

from typing import Any


_OTHER_PRESETS: list[dict[str, Any]] = [
    {"id": "openai", "label": "OpenAI", "base_url": "https://api.openai.com/v1"},
    {
        "id": "openrouter",
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
    },
    {
        "id": "gemini",
        "label": "Gemini (OpenAI-compatible)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
    },
    {
        "id": "ollama",
        "label": "Local (Ollama)",
        "base_url": "http://localhost:11434/v1",
    },
]


def provider_catalog() -> dict[str, Any]:
    return {
        "tabs": [{"id": "other", "label": "OpenAI-compatible"}],
        "gateways": [],
        "other_presets": _OTHER_PRESETS,
    }


def detect_gateway_tab(_base_url: str) -> None:
    """Lite has no bundled gateway-specific tabs."""
    return None
