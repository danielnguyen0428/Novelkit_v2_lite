"""Fernet helpers for encrypting provider API keys.

Set ``NOVELKIT_SECRETS_KEY`` to a Fernet-compatible key. In production, generate
one with:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

If the environment value is not already a valid Fernet key, we deterministically
derive one from it (SHA-256) so dev/test can use mnemonic strings. Tests should
set a fixed key only inside the test environment.
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken


def _resolved_fernet_key() -> bytes:
    raw = (os.environ.get("NOVELKIT_SECRETS_KEY") or "").strip()
    if not raw:
        raise RuntimeError(
            "NOVELKIT_SECRETS_KEY is required. "
            "Generate with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    raw_bytes = raw.encode("utf-8")
    try:
        Fernet(raw_bytes)
        return raw_bytes
    except Exception:
        digest = hashlib.sha256(raw_bytes).digest()
        return base64.urlsafe_b64encode(digest)


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        return ""
    token = Fernet(_resolved_fernet_key()).encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        data = Fernet(_resolved_fernet_key()).decrypt(ciphertext.encode("utf-8"))
    except InvalidToken as exc:
        raise RuntimeError("Unable to decrypt API key with NOVELKIT_SECRETS_KEY.") from exc
    return data.decode("utf-8")
