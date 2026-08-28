"""Database layer — engine, session factory, and ORM models."""

from webapp.db.models import Base, Novel, User, make_author_slug
from webapp.db.session import SessionLocal, engine, get_db

__all__ = [
    "Base",
    "Novel",
    "SessionLocal",
    "User",
    "engine",
    "get_db",
    "make_author_slug",
]
