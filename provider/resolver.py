"""Provider resolution seam over Hermes ``runtime_provider`` (Task 11.1, D6).

This module **does not** talk to any LLM. It loads the declarative
``config/provider.json``, applies environment overrides, and produces an ordered
chain of :class:`ProviderProfile` (primary → fallbacks) that Hermes
``runtime_provider`` executes. It is the migration of the legacy
``get_llm_failover_chain`` *semantics* (primary + fallbacks, lock/disable flags,
placeholder-credential filtering) with the legacy implementation and its
provider HTTP clients deliberately dropped.

Semantics preserved from the legacy Provider Failover Contract (CONTRACTS §4)::

    - The active provider is the ``llm.primary`` profile.
    - Python-side calls may use ``llm.fallbacks[]`` (or the ``LLM_FALLBACKS``
      env var) in primary → fallback order.
    - Failover can be locked off (``lock_primary`` / ``disable_fallbacks`` or the
      ``LLM_LOCK_PRIMARY`` / ``LLM_DISABLE_FALLBACKS`` env flags).
    - Profiles whose resolved credential looks like a placeholder are dropped so
      a guaranteed-401 profile never wastes a round-trip; if every profile is
      filtered the original chain is returned unchanged so upstream error
      reporting still has something to surface.

Credential resolution itself is delegated: callers pass a ``credential_lookup``
callable (in a real deployment this is Hermes' credential-pool resolver). The
default looks at the process environment only — never at any legacy
``~/.openclaw`` key-pool file.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

#: ``config/provider.json`` lives next to the other creative configs.
#: ``parents[1]`` is the package root (``provider/`` → ``novelkit-hermes/``).
PROVIDER_CONFIG_PATH: Path = (
    Path(__file__).resolve().parents[1] / "config" / "provider.json"
)

#: Credential prefixes/tokens that mark a dummy / unset key (ported, narrow).
_PLACEHOLDER_PREFIXES: tuple[str, ...] = (
    "placeholder-",
    "placeholder_",
    "your-",
    "your_",
    "<set-",
    "replace-",
)
_PLACEHOLDER_TOKENS: frozenset[str] = frozenset(
    {
        "",
        "none",
        "null",
        "todo",
        "changeme",
        "change-me",
        "change_me",
        "xxx",
        "xxxx",
        "xxxxxxxx",
    }
)

_TRUTHY = {"1", "true", "yes", "on"}


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ProviderProfile:
    """A single provider profile in the failover chain."""

    provider: str
    model: Optional[str] = None
    temperature: Optional[float] = None
    base_url: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"provider": self.provider}
        if self.model is not None:
            data["model"] = self.model
        if self.temperature is not None:
            data["temperature"] = self.temperature
        if self.base_url is not None:
            data["base_url"] = self.base_url
        data.update(self.extra)
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ProviderProfile":
        known = {"provider", "model", "temperature", "base_url"}
        return cls(
            provider=str(raw.get("provider") or "").strip(),
            model=(str(raw["model"]) if raw.get("model") else None),
            temperature=raw.get("temperature"),
            base_url=raw.get("base_url"),
            extra={k: v for k, v in raw.items() if k not in known},
        )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in _TRUTHY


def is_placeholder_credential(value: Optional[str]) -> bool:
    """True when ``value`` looks like a dummy / unset credential (ported)."""
    if value is None:
        return True
    s = value.strip()
    if not s:
        return True
    if s.lower() in _PLACEHOLDER_TOKENS:
        return True
    return any(s.lower().startswith(p) for p in _PLACEHOLDER_PREFIXES)


def _env_fallbacks(env: dict[str, str], env_key: str) -> Optional[list[dict[str, Any]]]:
    """Parse ``LLM_FALLBACKS`` (JSON list, or ``provider:model`` CSV)."""
    raw = (env.get(env_key) or "").strip()
    if not raw:
        return None
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        loaded = []
        for item in raw.split(","):
            item = item.strip()
            if not item:
                continue
            provider, _, model = item.partition(":")
            loaded.append(
                {"provider": provider.strip(), "model": model.strip() or None}
            )
    if not isinstance(loaded, list):
        return None
    return [entry for entry in loaded if isinstance(entry, dict)]


def load_provider_config(path: "str | Path | None" = None) -> dict[str, Any]:
    """Load ``config/provider.json`` (defaults to the package config)."""
    target = Path(path) if path is not None else PROVIDER_CONFIG_PATH
    if not target.exists():
        raise FileNotFoundError(f"provider config not found at {target}")
    with target.open(encoding="utf-8") as handle:
        config = json.load(handle)
    if not isinstance(config, dict):
        raise ValueError("provider config root must be a JSON object")
    return config


def creative_lane_requires_style_audit(config: Optional[dict[str, Any]] = None) -> bool:
    """Whether a creative-lane provider switch must check the style audit first.

    Reflects the Provider Failover Contract note (CONTRACTS §4): review the
    latest Style Coherence Audit before swapping models for a long run.
    """
    cfg = config if config is not None else load_provider_config()
    lane = cfg.get("creative_lane") or {}
    return bool(lane.get("style_audit_before_switch", True))


def _apply_env_overrides(
    primary: dict[str, Any],
    *,
    config: dict[str, Any],
    env: dict[str, str],
) -> tuple[dict[str, Any], Optional[list[dict[str, Any]]], bool]:
    """Apply env overrides → (primary, env_fallbacks, locked)."""
    keys = config.get("env_overrides") or {}
    primary = dict(primary)

    if keys.get("provider") and env.get(keys["provider"]):
        primary["provider"] = env[keys["provider"]]
    if keys.get("model") and env.get(keys["model"]):
        primary["model"] = env[keys["model"]]
    if keys.get("base_url") and env.get(keys["base_url"]):
        primary["base_url"] = env[keys["base_url"]]

    env_fallbacks = (
        _env_fallbacks(env, keys["fallbacks"]) if keys.get("fallbacks") else None
    )

    locked = bool(
        primary.get("lock_primary")
        or primary.get("disable_fallbacks")
        or (config.get("llm") or {}).get("lock_primary")
        or (config.get("llm") or {}).get("disable_fallbacks")
        or (keys.get("lock_primary") and _truthy(env.get(keys["lock_primary"])))
        or (
            keys.get("disable_fallbacks")
            and _truthy(env.get(keys["disable_fallbacks"]))
        )
    )
    return primary, env_fallbacks, locked


def resolve_provider_chain(
    config: Optional[dict[str, Any]] = None,
    *,
    credential_lookup: Optional[Callable[[str], Optional[str]]] = None,
    env: Optional[dict[str, str]] = None,
) -> list[ProviderProfile]:
    """Resolve the ordered provider chain (primary → fallbacks).

    Delegates credential resolution to ``credential_lookup`` (default: the
    process environment, ``<PROVIDER>_API_KEY``). Profiles with a placeholder
    credential are dropped; if every profile is filtered the unfiltered chain is
    returned so upstream error reporting still surfaces a profile.
    """
    cfg = config if config is not None else load_provider_config()
    env = dict(os.environ if env is None else env)
    llm = cfg.get("llm") or {}

    primary_raw = dict(llm.get("primary") or {})
    if not primary_raw.get("provider"):
        raise ValueError("provider config missing llm.primary.provider")

    primary_raw, env_fallbacks, locked = _apply_env_overrides(
        primary_raw, config=cfg, env=env
    )

    fallbacks_raw: list[dict[str, Any]]
    if locked:
        fallbacks_raw = []
    elif env_fallbacks is not None:
        fallbacks_raw = env_fallbacks
    else:
        fallbacks_raw = list(llm.get("fallbacks") or [])

    # Normalise: fallbacks inherit the primary model when they omit one.
    chain: list[ProviderProfile] = [ProviderProfile.from_dict(primary_raw)]
    for entry in fallbacks_raw:
        merged = dict(entry)
        if not merged.get("model"):
            merged["model"] = primary_raw.get("model")
        if not merged.get("temperature") and primary_raw.get("temperature") is not None:
            merged["temperature"] = primary_raw.get("temperature")
        profile = ProviderProfile.from_dict(merged)
        if profile.provider and profile not in chain:
            chain.append(profile)

    lookup = credential_lookup or _default_credential_lookup
    filtered = [
        profile
        for profile in chain
        if not is_placeholder_credential(lookup(profile.provider))
    ]
    return filtered if filtered else chain


def _default_credential_lookup(provider: str) -> Optional[str]:
    """Default credential resolver — environment only (no legacy key pool).

    Looks up ``<PROVIDER>_API_KEY`` (upper-cased, non-alphanumerics → ``_``).
    Real Hermes deployments inject the credential-pool resolver instead.
    """
    key = "".join(ch if ch.isalnum() else "_" for ch in provider.upper())
    return os.environ.get(f"{key}_API_KEY")
