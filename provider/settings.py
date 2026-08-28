"""LLM settings persistence — gitignored file + environment overrides.

The API key is a secret: it is stored only in ``.secrets/llm_settings.json``
(gitignored) or environment variables, never committed and never returned by
the API in clear (see :meth:`LLMConfig.masked`).

Precedence: explicit saved file values, then environment variables fill any
field still empty. Environment-only operation (no saved file) is fully
supported for container/CI deployment.

Env vars::

    NOVELKIT_LLM_BASE_URL   NOVELKIT_LLM_MODEL   NOVELKIT_LLM_API_KEY
    NOVELKIT_LLM_TEMPERATURE   NOVELKIT_LLM_MAX_TOKENS
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from .llm_client import LLMConfig

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SECRETS_DIR = Path(os.environ.get("NOVELKIT_SECRETS_DIR", PACKAGE_ROOT / ".secrets"))
SETTINGS_PATH = SECRETS_DIR / "llm_settings.json"


def _from_env(base: LLMConfig) -> LLMConfig:
    """Fill empty fields from environment variables (env never overrides a
    non-empty saved value, except the key which env may supply if file lacks it)."""
    base.base_url = os.environ.get("NOVELKIT_LLM_BASE_URL", base.base_url)
    base.model = os.environ.get("NOVELKIT_LLM_MODEL", base.model)
    if not base.api_key:
        base.api_key = os.environ.get("NOVELKIT_LLM_API_KEY", "")
    temp = os.environ.get("NOVELKIT_LLM_TEMPERATURE")
    if temp:
        try:
            base.temperature = float(temp)
        except ValueError:
            pass
    mx = os.environ.get("NOVELKIT_LLM_MAX_TOKENS")
    if mx:
        try:
            base.max_tokens = int(mx)
        except ValueError:
            pass
    to = os.environ.get("NOVELKIT_LLM_TIMEOUT")
    if to:
        try:
            base.timeout = float(to)
        except ValueError:
            pass
    return base


def load_config(db: Any = None, user_id: Optional[str] = None) -> LLMConfig:
    """Load the effective LLM config (saved file merged with env defaults)."""
    if db is not None and user_id:
        from provider import settings_db

        return settings_db.load_config(db, user_id)
    config = LLMConfig()
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            config = LLMConfig(
                base_url=data.get("base_url") or config.base_url,
                model=data.get("model") or config.model,
                api_key=data.get("api_key") or "",
                temperature=float(data.get("temperature", config.temperature)),
                max_tokens=int(data.get("max_tokens", config.max_tokens)),
                timeout=float(data.get("timeout", config.timeout)),
            )
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            config = LLMConfig()
    return _from_env(config)


def save_config(
    db: Any = None,
    user_id: Optional[str] = None,
    *,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> LLMConfig:
    """Persist provided fields to the gitignored settings file (merge update).

    ``api_key`` is only overwritten when a non-empty value is supplied, so the
    UI can save other fields without resending the secret. An empty string
    submitted explicitly via ``clear_api_key`` is handled by the caller.
    """
    if db is not None and user_id:
        from provider import settings_db

        return settings_db.save_config(
            db,
            user_id,
            provider=provider,
            base_url=base_url,
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    current = load_config()
    current_raw: dict[str, Any] = {}
    if SETTINGS_PATH.exists():
        try:
            current_raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            current_raw = {}
    clean_key = api_key.strip() if api_key else ""
    merged = {
        "provider": provider if provider is not None else current_raw.get("provider"),
        "base_url": base_url if base_url is not None else current.base_url,
        "model": model if model is not None else current.model,
        "api_key": clean_key if clean_key else current.api_key,
        "temperature": (
            temperature if temperature is not None else current.temperature
        ),
        "max_tokens": max_tokens if max_tokens is not None else current.max_tokens,
    }
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(merged, indent=2) + "\n", encoding="utf-8"
    )
    # Lock down file perms (best-effort; secrets file).
    try:
        SETTINGS_PATH.chmod(0o600)
    except OSError:
        pass
    return load_config()


def clear_config() -> None:
    """Delete the saved settings file (env vars still apply)."""
    try:
        SETTINGS_PATH.unlink()
    except FileNotFoundError:
        pass


def public_view(db: Any = None, user_id: Optional[str] = None) -> dict[str, Any]:
    """Masked, secret-free view of the effective config for the API/UI."""
    if db is not None and user_id:
        from provider import settings_db

        return settings_db.public_view(db, user_id)
    view = load_config().masked()
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            provider = data.get("provider")
            if isinstance(provider, str) and provider.strip():
                view["provider"] = provider.strip()
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            pass
    # Lite always uses the operator's own provider configuration.
    view["mode"] = "custom"
    return view
