"""Pytest configuration — set test env before webapp.db imports."""

from __future__ import annotations

import base64
import os

import pytest


def _test_fernet_key() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")

# session.py creates the SQLAlchemy engine at import time; force in-memory DB
# before any test module imports webapp.db.
os.environ["NOVELKIT_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["NOVELKIT_AUTH"] = "off"
os.environ["NOVELKIT_SECRETS_KEY"] = _test_fernet_key()


def pytest_configure(config) -> None:
    os.environ["NOVELKIT_DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["NOVELKIT_AUTH"] = "off"
    os.environ["NOVELKIT_SECRETS_KEY"] = _test_fernet_key()


@pytest.fixture(autouse=True)
def _ensure_db_tables():
    """Create ORM tables for in-memory SQLite before each test."""
    from webapp.db.models import Base
    from webapp.db.session import engine

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
