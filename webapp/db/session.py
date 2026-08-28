"""Database engine and session factory."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PACKAGE_ROOT / ".data" / "novelkit-lite.db"
DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.environ.get("NOVELKIT_DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

if DATABASE_URL == "sqlite:///:memory:":
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
