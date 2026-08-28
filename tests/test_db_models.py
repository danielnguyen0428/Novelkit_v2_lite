"""SQLAlchemy model and author-slug tests."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, sessionmaker

from webapp.db.models import Base, User, make_author_slug
from webapp.db.session import engine


@pytest.fixture()
def db_session() -> Session:
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_user_author_slug_unique(db_session: Session) -> None:
    slug1 = make_author_slug("Alice", session=db_session)
    u1 = User(
        email="a@x.com",
        display_name="Alice",
        author_slug=slug1,
    )
    db_session.add(u1)
    db_session.commit()

    slug2 = make_author_slug("Alice", session=db_session)
    u2 = User(
        email="b@x.com",
        display_name="Alice",
        author_slug=slug2,
    )
    db_session.add(u2)
    db_session.commit()

    assert u1.author_slug == "alice"
    assert u2.author_slug == "alice-2"
