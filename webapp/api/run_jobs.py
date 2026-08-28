"""Persistent background AI run jobs for mobile clients."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import sessionmaker

from webapp.api.service import RunBusyError, SERVICE
from webapp.db.models import RunCommandRecord, RunJobRecord, UsageLedgerRecord, User
from webapp.db.session import SessionLocal

ACTIVE_JOB_STATUSES = ("queued", "running", "pausing")
VALID_COMMANDS = {"pause", "resume", "steer", "cancel_after_step"}

_NOVEL_ACTIVE: dict[str, str] = {}  # lock_key -> job_id, process-local hint only
_GUARD = threading.Lock()


def _lock_key(user_id: str, novel_slug: str) -> str:
    return f"{user_id}:{novel_slug}"


def _session_factory(db_factory: Any | None) -> sessionmaker:
    return db_factory or SessionLocal


def _load_steps(row: RunJobRecord) -> list[dict[str, Any]]:
    try:
        data = json.loads(row.steps_json or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _job_payload(row: RunJobRecord | None) -> dict[str, Any]:
    if row is None:
        return {
            "job_id": None,
            "status": "idle",
            "steps": [],
            "tasks_completed": 0,
            "chapters_drafted": 0,
            "chapters_synced": 0,
            "blocked": False,
            "breaker_open": False,
            "final_status": None,
            "stopped_reason": None,
            "error": None,
            "alreadyRunning": False,
        }
    error = row.error_code or row.error_message_redacted
    return {
        "job_id": row.id,
        "status": row.status,
        "steps": _load_steps(row),
        "tasks_completed": row.tasks_completed,
        "chapters_drafted": row.chapters_drafted,
        "chapters_synced": row.chapters_synced,
        "blocked": bool(row.blocked),
        "breaker_open": bool(row.breaker_open),
        "final_status": row.final_status,
        "stopped_reason": row.stopped_reason,
        "error": error,
        "alreadyRunning": row.status in ACTIVE_JOB_STATUSES,
        "current_task_key": row.current_task_key,
        "current_step": row.current_step,
        "state_version": row.state_version,
    }


def _latest_job(db, user_id: str, novel_slug: str) -> RunJobRecord | None:  # noqa: ANN001
    return db.scalar(
        select(RunJobRecord)
        .where(RunJobRecord.user_id == user_id, RunJobRecord.novel_id == novel_slug)
        .order_by(desc(RunJobRecord.requested_at))
        .limit(1)
    )


def _active_job(db, user_id: str, novel_slug: str) -> RunJobRecord | None:  # noqa: ANN001
    return db.scalar(
        select(RunJobRecord)
        .where(
            RunJobRecord.user_id == user_id,
            RunJobRecord.novel_id == novel_slug,
            RunJobRecord.status.in_(ACTIVE_JOB_STATUSES),
        )
        .order_by(desc(RunJobRecord.requested_at))
        .limit(1)
    )


def recover_orphaned_run_jobs(db_factory: Any | None = None) -> int:
    """Fail active jobs left behind by a previous server process."""
    factory = _session_factory(db_factory)
    db = factory()
    try:
        rows = list(
            db.scalars(
                select(RunJobRecord).where(
                    RunJobRecord.status.in_(ACTIVE_JOB_STATUSES)
                )
            )
        )
        finished_at = datetime.now(timezone.utc)
        for row in rows:
            row.status = "failed"
            row.finished_at = finished_at
            row.error_code = "process_restarted"
            row.error_message_redacted = "process_restarted"
            row.stopped_reason = "process_restarted"
        db.commit()
        return len(rows)
    finally:
        db.close()


def start_run_async(
    db_factory,
    user: User,
    novel_slug: str,
    *,
    max_steps: int,
    stop_after_chapters: int | None = None,
) -> dict[str, Any]:
    """Persist and enqueue a background run job."""
    factory = _session_factory(db_factory)
    key = _lock_key(user.id, novel_slug)
    db = factory()
    try:
        active = _active_job(db, user.id, novel_slug)
        if active is not None:
            return {
                "job_id": active.id,
                "status": active.status,
                "alreadyRunning": True,
            }

        job = RunJobRecord(
            user_id=user.id,
            novel_id=novel_slug,
            status="queued",
            max_steps=max_steps,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
    finally:
        db.close()

    with _GUARD:
        _NOVEL_ACTIVE[key] = job_id

    def _worker() -> None:
        db = factory()
        row: RunJobRecord | None = None
        try:
            row = db.get(RunJobRecord, job_id)
            if row is None:
                return
            row.status = "running"
            row.started_at = datetime.now(timezone.utc)
            db.commit()

            db_user = db.get(User, user.id)
            if db_user is None:
                row.status = "failed"
                row.error_code = "user_not_found"
                row.error_message_redacted = "User not found"
                return
            try:
                report = SERVICE.run(
                    db,
                    db_user,
                    novel_slug,
                    max_steps=max_steps,
                    stop_after_chapters=stop_after_chapters,
                )
                steps = report.get("steps", [])
                last_step = steps[-1] if steps else {}
                row.steps_json = json.dumps(steps, ensure_ascii=False)
                row.tasks_completed = int(report.get("tasks_completed", 0) or 0)
                row.chapters_drafted = int(report.get("chapters_drafted", 0) or 0)
                row.chapters_synced = int(report.get("chapters_synced", 0) or 0)
                row.blocked = 1 if report.get("blocked", False) else 0
                row.breaker_open = 1 if report.get("breaker_open", False) else 0
                row.final_status = report.get("final_status")
                row.stopped_reason = report.get("stopped_reason")
                row.current_task_key = last_step.get("task_key")
                row.current_step = last_step.get("stage")
                has_error = bool(report.get("error"))
                row.error_code = "run_failed" if has_error else None
                row.error_message_redacted = "run_failed" if has_error else None
                row.status = "completed"
            except RunBusyError:
                row.status = "failed"
                row.error_code = "already_running"
                row.error_message_redacted = "already_running"
            except Exception:  # noqa: BLE001
                row.status = "failed"
                row.error_code = "run_failed"
                # Exception strings can contain provider request fragments,
                # API credentials, or manuscript text. Persist only a stable
                # operational code; detailed diagnostics belong in ephemeral,
                # access-controlled tracing with explicit redaction.
                row.error_message_redacted = "run_failed"
        finally:
            row = db.get(RunJobRecord, job_id)
            if row is not None and row.finished_at is None:
                row.finished_at = datetime.now(timezone.utc)
            db.commit()
            db.close()
            with _GUARD:
                if _NOVEL_ACTIVE.get(key) == job_id:
                    _NOVEL_ACTIVE.pop(key, None)

    threading.Thread(target=_worker, daemon=True, name=f"run-job-{job_id[:8]}").start()
    return {"job_id": job_id, "status": "queued"}


def get_run_status(
    user_id: str,
    novel_slug: str,
    *,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Return persisted run job status for a novel owned by *user_id*."""
    db = SessionLocal()
    try:
        if job_id is not None:
            row = db.get(RunJobRecord, job_id)
            if row is None or row.user_id != user_id or row.novel_id != novel_slug:
                return _job_payload(None)
            return _job_payload(row)
        return _job_payload(_latest_job(db, user_id, novel_slug))
    finally:
        db.close()


def enqueue_run_command(
    user_id: str,
    novel_slug: str,
    job_id: str,
    *,
    command_type: str,
    payload: dict[str, Any] | None = None,
    expected_state_version: int | None = None,
) -> dict[str, Any]:
    """Persist a step-boundary command for a run job."""
    if command_type not in VALID_COMMANDS:
        raise ValueError(f"invalid command_type {command_type!r}")
    db = SessionLocal()
    try:
        job = db.get(RunJobRecord, job_id)
        if job is None or job.user_id != user_id or job.novel_id != novel_slug:
            raise KeyError(job_id)
        command = RunCommandRecord(
            job_id=job_id,
            user_id=user_id,
            novel_id=novel_slug,
            command_type=command_type,
            payload_json=json.dumps(payload or {}, ensure_ascii=False),
            status="queued",
            expected_state_version=expected_state_version,
        )
        db.add(command)
        db.commit()
        db.refresh(command)
        return _command_payload(command)
    finally:
        db.close()


def _command_payload(command: RunCommandRecord) -> dict[str, Any]:
    try:
        payload = json.loads(command.payload_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    return {
        "id": command.id,
        "job_id": command.job_id,
        "user_id": command.user_id,
        "novel_id": command.novel_id,
        "command_type": command.command_type,
        "payload": payload,
        "status": command.status,
        "expected_state_version": command.expected_state_version,
        "created_at": command.created_at.isoformat() if command.created_at else None,
        "applied_at": command.applied_at.isoformat() if command.applied_at else None,
    }


def list_run_commands(user_id: str, novel_slug: str, job_id: str) -> list[dict[str, Any]]:
    """List persisted commands for a run job."""
    db = SessionLocal()
    try:
        job = db.get(RunJobRecord, job_id)
        if job is None or job.user_id != user_id or job.novel_id != novel_slug:
            return []
        rows = db.scalars(
            select(RunCommandRecord)
            .where(RunCommandRecord.job_id == job_id)
            .order_by(RunCommandRecord.created_at)
        ).all()
        return [_command_payload(row) for row in rows]
    finally:
        db.close()


def mark_run_command(
    command_id: str,
    *,
    status: str,
) -> dict[str, Any] | None:
    """Update command delivery status."""
    db = SessionLocal()
    try:
        command = db.get(RunCommandRecord, command_id)
        if command is None:
            return None
        command.status = status
        if status == "applied":
            command.applied_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(command)
        return _command_payload(command)
    finally:
        db.close()


def _usage_payload(row: UsageLedgerRecord) -> dict[str, Any]:
    try:
        retry_chain = json.loads(row.retry_chain_json or "[]")
    except json.JSONDecodeError:
        retry_chain = []
    return {
        "id": row.id,
        "user_id": row.user_id,
        "novel_id": row.novel_id,
        "job_id": row.job_id,
        "task_key": row.task_key,
        "step": row.step,
        "role": row.role,
        "provider": row.provider,
        "model_fingerprint": row.model_fingerprint,
        "input_tokens": row.input_tokens,
        "output_tokens": row.output_tokens,
        "cache_tokens": row.cache_tokens,
        "cost_estimate": row.cost_estimate,
        "currency": row.currency,
        "latency_ms": row.latency_ms,
        "outcome": row.outcome,
        "retry_chain": retry_chain,
        "prompt_version": row.prompt_version,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def record_usage_event(
    *,
    user_id: str,
    novel_slug: str,
    job_id: str | None,
    task_key: str,
    step: str,
    role: str,
    provider: str,
    model_fingerprint: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_tokens: int = 0,
    cost_estimate: float = 0.0,
    currency: str = "USD",
    latency_ms: int = 0,
    outcome: str,
    retry_chain: list[dict[str, Any]] | None = None,
    prompt_version: str | None = None,
) -> dict[str, Any]:
    """Persist a redacted usage/cost event for one model/tool call."""
    db = SessionLocal()
    try:
        row = UsageLedgerRecord(
            user_id=user_id,
            novel_id=novel_slug,
            job_id=job_id,
            task_key=task_key,
            step=step,
            role=role,
            provider=provider,
            model_fingerprint=model_fingerprint,
            input_tokens=max(0, int(input_tokens or 0)),
            output_tokens=max(0, int(output_tokens or 0)),
            cache_tokens=max(0, int(cache_tokens or 0)),
            cost_estimate=max(0.0, float(cost_estimate or 0.0)),
            currency=currency,
            latency_ms=max(0, int(latency_ms or 0)),
            outcome=outcome,
            retry_chain_json=json.dumps(retry_chain or [], ensure_ascii=False),
            prompt_version=prompt_version,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _usage_payload(row)
    finally:
        db.close()


def list_usage_events(
    user_id: str,
    novel_slug: str,
    *,
    job_id: str | None = None,
) -> list[dict[str, Any]]:
    """List redacted usage/cost events in user + novel scope."""
    db = SessionLocal()
    try:
        query = select(UsageLedgerRecord).where(
            UsageLedgerRecord.user_id == user_id,
            UsageLedgerRecord.novel_id == novel_slug,
        )
        if job_id is not None:
            query = query.where(UsageLedgerRecord.job_id == job_id)
        rows = db.scalars(query.order_by(UsageLedgerRecord.created_at)).all()
        return [_usage_payload(row) for row in rows]
    finally:
        db.close()
