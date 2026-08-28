"""Local-only request dependencies.

The Lite edition has one operator and one local data store. It creates a stable
internal owner row so the existing creative service can keep its ownership and
settings boundaries without exposing login or account features in the UI/API.
"""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from webapp.db.models import User, make_author_slug
from webapp.db.session import get_db

LOCAL_OWNER_EMAIL = "local@novelkit.invalid"
LOCAL_OWNER_DISPLAY_NAME = "Local Writer"


def _get_or_create_local_owner(db: Session) -> User:
    owner = db.scalar(select(User).where(User.email == LOCAL_OWNER_EMAIL))
    if owner is None:
        owner = User(
            email=LOCAL_OWNER_EMAIL,
            display_name=LOCAL_OWNER_DISPLAY_NAME,
            author_slug=make_author_slug(LOCAL_OWNER_DISPLAY_NAME, session=db),
        )
        db.add(owner)
        db.commit()
        db.refresh(owner)
    return owner


def get_current_user(_request: Request, db: Session = Depends(get_db)) -> User:
    """Resolve the single local owner; no session, OAuth, or account is needed."""
    return _get_or_create_local_owner(db)

