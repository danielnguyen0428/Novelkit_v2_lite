"""SQLAlchemy persistence for the single-operator Lite runtime."""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _slugify_display_name(display_name: str) -> str:
    slug = display_name.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "author"


def make_author_slug(display_name: str, session: Session | None = None) -> str:
    """Derive a URL-safe author slug from *display_name*.

    When *session* is provided, append ``-2``, ``-3``, … until the slug is
    unused in ``users.author_slug``.
    """
    base = _slugify_display_name(display_name)
    if session is None:
        return base

    taken = set(session.scalars(select(User.author_slug)).all())
    if base not in taken:
        return base

    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"


class User(Base):
    """Internal local owner used to scope workspaces and provider settings.

    This is not a sign-in account and is never exposed as an API resource.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    author_slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    novels: Mapped[list[Novel]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    llm_settings: Mapped[UserLLMSettings | None] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Novel(Base):
    __tablename__ = "novels"
    __table_args__ = (UniqueConstraint("owner_user_id", "slug", name="uq_novel_owner_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(200), default="")
    logline: Mapped[str] = mapped_column(Text, default="")
    genre: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    owner: Mapped[User] = relationship(back_populates="novels")


class UserLLMSettings(Base):
    __tablename__ = "user_llm_settings"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    base_url: Mapped[str] = mapped_column(String(512), default="https://api.openai.com/v1")
    model: Mapped[str] = mapped_column(String(160), default="gpt-4o-mini")
    api_key_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperature: Mapped[float] = mapped_column(default=0.8)
    max_tokens: Mapped[int] = mapped_column(default=16384)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped[User] = relationship(back_populates="llm_settings")


class RunJobRecord(Base):
    """Persistent operational job metadata for creative pipeline runs."""

    __tablename__ = "run_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    novel_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    current_task_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    current_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    state_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message_redacted: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_steps: Mapped[int] = mapped_column(Integer, default=12)
    steps_json: Mapped[str] = mapped_column(Text, default="[]")
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    chapters_drafted: Mapped[int] = mapped_column(Integer, default=0)
    chapters_synced: Mapped[int] = mapped_column(Integer, default=0)
    blocked: Mapped[int] = mapped_column(Integer, default=0)
    breaker_open: Mapped[int] = mapped_column(Integer, default=0)
    final_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stopped_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)


class RunCommandRecord(Base):
    """Persistent step-boundary user command for a run job."""

    __tablename__ = "run_commands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(
        ForeignKey("run_jobs.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    novel_id: Mapped[str] = mapped_column(String(128), index=True)
    command_type: Mapped[str] = mapped_column(String(40))
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(32), default="queued")
    expected_state_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UsageLedgerRecord(Base):
    """Redacted per-call token/cost ledger for creative runtime usage."""

    __tablename__ = "usage_ledger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    novel_id: Mapped[str] = mapped_column(String(128), index=True)
    job_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    task_key: Mapped[str] = mapped_column(String(160), index=True)
    step: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(80))
    provider: Mapped[str] = mapped_column(String(80))
    model_fingerprint: Mapped[str] = mapped_column(String(200))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    outcome: Mapped[str] = mapped_column(String(40))
    retry_chain_json: Mapped[str] = mapped_column(Text, default="[]")
    prompt_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
