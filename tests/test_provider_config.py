"""Tests for the Hermes provider-resolution seam (Task 11.1, finding D6).

Covers the migrated Provider Failover Contract semantics:
- the declarative ``config/provider.json`` loads and is well-formed;
- the resolved chain is primary → fallbacks in order;
- ``lock_primary`` / env flags drop fallbacks;
- ``LLM_FALLBACKS`` / ``LLM_PROVIDER`` env overrides apply;
- placeholder credentials are filtered (but never to an empty chain);
- the creative-lane style-audit guard reflects the contract note;
- the legacy provider modules are **not** reintroduced into the package.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from provider.resolver import (
    PROVIDER_CONFIG_PATH,
    ProviderProfile,
    creative_lane_requires_style_audit,
    is_placeholder_credential,
    load_provider_config,
    resolve_provider_chain,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _no_cred(_provider: str) -> str:
    """Credential lookup that returns a real-looking key for every provider."""
    return "sk-real-key-0123456789"


def test_config_loads_and_is_wellformed() -> None:
    config = load_provider_config()
    assert config["runtime_provider"] == "hermes"
    assert config["llm"]["primary"]["provider"]
    assert isinstance(config["llm"]["fallbacks"], list)


def test_chain_is_primary_then_fallbacks_in_order() -> None:
    chain = resolve_provider_chain(credential_lookup=_no_cred)
    config = load_provider_config()
    assert chain[0].provider == config["llm"]["primary"]["provider"]
    expected_fallbacks = [f["provider"] for f in config["llm"]["fallbacks"]]
    assert [p.provider for p in chain[1:]] == expected_fallbacks


def test_fallbacks_inherit_primary_temperature() -> None:
    chain = resolve_provider_chain(credential_lookup=_no_cred)
    primary = chain[0]
    for fallback in chain[1:]:
        assert fallback.temperature == primary.temperature


def test_lock_primary_drops_fallbacks() -> None:
    config = load_provider_config()
    config["llm"]["lock_primary"] = True
    chain = resolve_provider_chain(config=config, credential_lookup=_no_cred)
    assert len(chain) == 1


def test_env_lock_primary_drops_fallbacks() -> None:
    chain = resolve_provider_chain(
        credential_lookup=_no_cred, env={"LLM_LOCK_PRIMARY": "1"}
    )
    assert len(chain) == 1


def test_env_provider_override_applies() -> None:
    chain = resolve_provider_chain(
        credential_lookup=_no_cred, env={"LLM_PROVIDER": "ollama"}
    )
    assert chain[0].provider == "ollama"


def test_env_fallbacks_override_csv() -> None:
    chain = resolve_provider_chain(
        credential_lookup=_no_cred,
        env={"LLM_FALLBACKS": "claude:claude-x, openai:gpt-x"},
    )
    assert [p.provider for p in chain[1:]] == ["claude", "openai"]
    assert chain[1].model == "claude-x"


def test_placeholder_credentials_are_filtered() -> None:
    def lookup(provider: str) -> str:
        # Only the primary provider has a real key; fallbacks are placeholders.
        primary = load_provider_config()["llm"]["primary"]["provider"]
        return "sk-real" if provider == primary else "placeholder-not-used"

    chain = resolve_provider_chain(credential_lookup=lookup)
    assert len(chain) == 1


def test_all_placeholder_returns_unfiltered_chain() -> None:
    chain = resolve_provider_chain(credential_lookup=lambda _p: "placeholder-x")
    # Every profile filtered → fall back to the unfiltered chain so upstream
    # error reporting still has something to surface.
    assert len(chain) >= 1


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, True),
        ("", True),
        ("   ", True),
        ("changeme", True),
        ("placeholder-foo", True),
        ("your-key-here", True),
        ("sk-abc123", False),
        ("AIzaSyRealKey", False),
    ],
)
def test_is_placeholder_credential(value, expected) -> None:
    assert is_placeholder_credential(value) is expected


def test_creative_lane_requires_style_audit() -> None:
    assert creative_lane_requires_style_audit() is True


def test_profile_roundtrip() -> None:
    profile = ProviderProfile(provider="gemini", model="m", temperature=0.1)
    assert ProviderProfile.from_dict(profile.to_dict()) == profile


def test_legacy_provider_modules_not_reintroduced() -> None:
    """The legacy provider stack must not exist anywhere in the package (Req 5)."""
    legacy = (
        "llm_config.py",
        "gemini_key_pool.py",
        "gemini_pool_status.py",
        "google_genai_compat.py",
    )
    found = [
        str(p.relative_to(PACKAGE_ROOT))
        for name in legacy
        for p in PACKAGE_ROOT.rglob(name)
    ]
    assert found == [], f"legacy provider files reintroduced: {found}"


def test_config_path_is_in_package() -> None:
    assert PROVIDER_CONFIG_PATH.exists()
    assert PROVIDER_CONFIG_PATH.name == "provider.json"
