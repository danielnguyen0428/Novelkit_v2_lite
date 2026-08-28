"""Provider catalog API."""

from __future__ import annotations

from webapp.api.provider_catalog import detect_gateway_tab, provider_catalog


def test_provider_catalog_shape():
    data = provider_catalog()
    assert data["tabs"] == [{"id": "other", "label": "OpenAI-compatible"}]
    assert data["gateways"] == []
    assert {preset["id"] for preset in data["other_presets"]} == {
        "openai",
        "openrouter",
        "gemini",
        "ollama",
    }
    assert detect_gateway_tab("https://api.openai.com/v1") is None
