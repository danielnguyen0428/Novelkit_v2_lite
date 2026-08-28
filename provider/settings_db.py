"""Database-backed per-user LLM settings."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from provider.crypto import decrypt_secret, encrypt_secret
from provider.llm_client import LLMConfig
from webapp.db.models import UserLLMSettings

_LOG = logging.getLogger("novelkit.provider.settings_db")


def _safe_decrypt(ciphertext: str) -> str:
    """Decrypt a stored API key, degrading to empty on failure.

    Rotating ``NOVELKIT_SECRETS_KEY`` makes every previously-stored ciphertext
    undecryptable. Rather than 500 on every settings load for that user, we
    surface the key as empty (the UI then prompts for a re-entry) and log the
    failure so the rotation is diagnosable.
    """
    if not ciphertext:
        return ""
    try:
        return decrypt_secret(ciphertext)
    except Exception:  # noqa: BLE001 — decrypt failure must not break load
        _LOG.warning(
            "provider: stored API key could not be decrypted "
            "(NOVELKIT_SECRETS_KEY rotated?); treating as unset",
            exc_info=True,
        )
        return ""


def _legacy_settings_module():
    # Lazy import avoids circular imports with provider.settings delegating here.
    from provider import settings as legacy_settings

    return legacy_settings


def _row_for_user(db: Session, user_id: str) -> UserLLMSettings | None:
    return db.scalar(select(UserLLMSettings).where(UserLLMSettings.user_id == user_id))


def load_config(db: Session, user_id: str) -> LLMConfig:
    row = _row_for_user(db, user_id)
    if row is None:
        return _legacy_settings_module().load_config()
    return LLMConfig(
        base_url=row.base_url or LLMConfig.base_url,
        model=row.model or LLMConfig.model,
        api_key=_safe_decrypt(row.api_key_ciphertext or ""),
        temperature=float(row.temperature),
        max_tokens=int(row.max_tokens),
    )


def save_config(
    db: Session,
    user_id: str,
    *,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> LLMConfig:
    row = _row_for_user(db, user_id)
    current = load_config(db, user_id)
    legacy_provider = _legacy_settings_module().public_view().get("provider")
    existing_provider = row.provider if row is not None else legacy_provider

    if row is None:
        row = UserLLMSettings(
            user_id=user_id,
            provider=(provider.strip() if isinstance(provider, str) and provider.strip() else existing_provider),
            base_url=base_url if base_url is not None else current.base_url,
            model=model if model is not None else current.model,
            api_key_ciphertext=encrypt_secret(current.api_key) if current.api_key else None,
            temperature=temperature if temperature is not None else current.temperature,
            max_tokens=max_tokens if max_tokens is not None else current.max_tokens,
            updated_at=datetime.now(UTC),
        )
        db.add(row)
    else:
        if provider is not None:
            row.provider = provider.strip() or None
        row.base_url = base_url if base_url is not None else row.base_url
        row.model = model if model is not None else row.model
        row.temperature = temperature if temperature is not None else row.temperature
        row.max_tokens = max_tokens if max_tokens is not None else row.max_tokens
        row.updated_at = datetime.now(UTC)

    clean_key = api_key.strip() if api_key else ""
    if clean_key:
        row.api_key_ciphertext = encrypt_secret(clean_key)

    db.commit()
    return load_config(db, user_id)


def public_view(db: Session, user_id: str) -> dict[str, Any]:
    row = _row_for_user(db, user_id)
    if row is None:
        view = _legacy_settings_module().public_view()
    else:
        view = LLMConfig(
            base_url=row.base_url or LLMConfig.base_url,
            model=row.model or LLMConfig.model,
            api_key=_safe_decrypt(row.api_key_ciphertext or ""),
            temperature=float(row.temperature),
            max_tokens=int(row.max_tokens),
        ).masked()
        if row.provider:
            view["provider"] = row.provider

    # Lite always uses the operator's own provider configuration.
    view["mode"] = "custom"
    return view
