from __future__ import annotations

from webapp.db.models import Base, RunJobRecord, UsageLedgerRecord, User
from webapp.db.session import SessionLocal, engine


def _reset_db() -> User:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = User(
            email="meow@example.com",
            display_name="Meow",
            author_slug="meow",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def test_run_job_status_is_persisted_beyond_process_memory(monkeypatch):
    user = _reset_db()
    import webapp.api.run_jobs as run_jobs

    def _fake_run(_db, _user, _novel_slug, *, max_steps, stop_after_chapters=None):  # noqa: ANN001
        return {
            "steps": [{"task_key": "chapter.0001.sync", "stage": "synchronise"}],
            "tasks_completed": max_steps,
            "chapters_drafted": 1,
            "chapters_synced": 1,
            "blocked": False,
            "breaker_open": False,
            "final_status": "completed",
            "stopped_reason": "drained",
            "error": None,
        }

    class _ImmediateThread:
        def __init__(self, *, target, **_kwargs):  # noqa: ANN001
            self.target = target

        def start(self) -> None:
            self.target()

    monkeypatch.setattr(run_jobs.SERVICE, "run", _fake_run)
    monkeypatch.setattr(run_jobs.threading, "Thread", _ImmediateThread)

    queued = run_jobs.start_run_async(None, user, "demo", max_steps=3)
    run_jobs._NOVEL_ACTIVE.clear()

    status = run_jobs.get_run_status(user.id, "demo", job_id=queued["job_id"])

    assert status["status"] == "completed"
    assert status["tasks_completed"] == 3
    assert status["current_task_key"] == "chapter.0001.sync"
    assert status["alreadyRunning"] is False


def test_startup_marks_orphaned_active_jobs_as_failed():
    user = _reset_db()
    from webapp.api.main import _create_db_tables

    db = SessionLocal()
    try:
        jobs = [
            RunJobRecord(user_id=user.id, novel_id=f"novel-{status}", status=status)
            for status in ("queued", "running", "pausing", "completed")
        ]
        db.add_all(jobs)
        db.commit()
    finally:
        db.close()

    _create_db_tables()

    db = SessionLocal()
    try:
        by_novel = {
            row.novel_id: row
            for row in db.query(RunJobRecord).order_by(RunJobRecord.novel_id).all()
        }
        for status in ("queued", "running", "pausing"):
            row = by_novel[f"novel-{status}"]
            assert row.status == "failed"
            assert row.error_code == "process_restarted"
            assert row.error_message_redacted == "process_restarted"
            assert row.stopped_reason == "process_restarted"
            assert row.finished_at is not None

        completed = by_novel["novel-completed"]
        assert completed.status == "completed"
        assert completed.error_code is None
    finally:
        db.close()


def test_run_commands_are_persisted_for_job():
    user = _reset_db()
    import webapp.api.run_jobs as run_jobs

    db = SessionLocal()
    try:
        job = RunJobRecord(user_id=user.id, novel_id="demo", status="running")
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
    finally:
        db.close()

    command = run_jobs.enqueue_run_command(
        user.id,
        "demo",
        job_id,
        command_type="pause",
        payload={"reason": "review"},
        expected_state_version=7,
    )
    listed = run_jobs.list_run_commands(user.id, "demo", job_id)

    assert command["command_type"] == "pause"
    assert command["expected_state_version"] == 7
    assert listed == [command]


def test_usage_ledger_records_token_cost_without_raw_prompt():
    user = _reset_db()
    import webapp.api.run_jobs as run_jobs

    event = run_jobs.record_usage_event(
        user_id=user.id,
        novel_slug="demo",
        job_id="job-1",
        task_key="chapter.0001.write",
        step="draft",
        role="writer",
        provider="runtime_default",
        model_fingerprint="model:fingerprint",
        input_tokens=123,
        output_tokens=456,
        cache_tokens=7,
        cost_estimate=0.0123,
        currency="USD",
        latency_ms=890,
        outcome="done",
        retry_chain=[{"provider": "runtime_default", "outcome": "done"}],
        prompt_version="writer:v2.2.0",
    )
    listed = run_jobs.list_usage_events(user.id, "demo", job_id="job-1")

    assert listed == [event]
    assert event["task_key"] == "chapter.0001.write"
    assert event["input_tokens"] == 123
    assert event["cost_estimate"] == 0.0123
    assert "prompt" not in event

    db = SessionLocal()
    try:
        rows = db.query(UsageLedgerRecord).all()
        assert len(rows) == 1
        assert rows[0].prompt_version == "writer:v2.2.0"
    finally:
        db.close()


def test_run_failure_does_not_persist_exception_text(monkeypatch):
    user = _reset_db()
    import webapp.api.run_jobs as run_jobs

    def _failed_run(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("private manuscript and sk-secret-key must not persist")

    class _ImmediateThread:
        def __init__(self, *, target, **_kwargs):  # noqa: ANN001
            self.target = target

        def start(self) -> None:
            self.target()

    monkeypatch.setattr(run_jobs.SERVICE, "run", _failed_run)
    monkeypatch.setattr(run_jobs.threading, "Thread", _ImmediateThread)

    queued = run_jobs.start_run_async(None, user, "private-novel", max_steps=1)

    db = SessionLocal()
    try:
        row = db.get(RunJobRecord, queued["job_id"])
        assert row is not None
        assert row.error_code == "run_failed"
        assert row.error_message_redacted == "run_failed"
        assert "manuscript" not in row.error_message_redacted
        assert "sk-secret-key" not in row.error_message_redacted
    finally:
        db.close()
