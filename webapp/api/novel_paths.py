"""Filesystem paths for owner-scoped novel storage."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from webapp.db.models import Novel

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
STORAGE_ROOT = Path(
    os.environ.get("NOVELKIT_STORAGE_ROOT", PACKAGE_ROOT / "storage")
).resolve()


def novel_disk_path(novel: Novel) -> Path:
    return STORAGE_ROOT / "users" / novel.owner_user_id / "novels" / novel.id


def ensure_novel_dir(novel: Novel) -> Path:
    path = novel_disk_path(novel)
    path.mkdir(parents=True, exist_ok=True)
    return path


def tts_cache_user_path(user_id: str) -> Path:
    """Return an owner-scoped TTS cache path without exposing the user ID."""
    owner_scope = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    return STORAGE_ROOT / "tts_cache" / "users" / owner_scope
