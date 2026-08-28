"""Pure per-turn reminders + StopGuard (Req 8; Properties P20, P21)."""

from __future__ import annotations

from tools.novelkit_pipeline_tool import PipelineEngine, TaskStatus
from tools.novelkit_reminder import (
    book_complete,
    build_reminder,
    stop_guard,
)


def _ready_state():
    return PipelineEngine.create(target_chapters=3, novel="x", mode="full_plan").state


def _complete_state():
    eng = PipelineEngine.create(target_chapters=1, novel="x", mode="full_plan")
    # mark every task done and record a synced chapter 1
    for t in eng.state.tasks.values():
        t.status = TaskStatus.DONE.value
    return eng.state


def test_reminder_pure_no_mutation():
    s = _ready_state()
    snapshot = s.to_dict()
    r1 = build_reminder(s, doctor_blocking=[])
    r2 = build_reminder(s, doctor_blocking=[])
    assert r1 == r2  # deterministic (P20)
    assert "<system-reminder>" in r1
    assert s.to_dict() == snapshot  # no mutation (P20)


def test_reminder_reports_next_task():
    s = _ready_state()
    assert "Bước kế" in build_reminder(s)


def test_reminder_queue_guard():
    s = _ready_state()
    s.creative.rewrite_queue.append({"queue_id": "rw1", "status": "pending"})
    assert "Cấm bắt đầu chương mới" in build_reminder(s)


def test_stop_guard_blocks_until_complete():
    s = _ready_state()
    blocked, reason = stop_guard(s)
    assert blocked is True and reason == "work_remaining"

    done = _complete_state()
    blocked2, reason2 = stop_guard(done)
    assert blocked2 is False and reason2 == "book_complete"


def test_stop_guard_escalates_after_max_blocks():
    s = _ready_state()
    s.creative.stop_block_count = 3
    blocked, reason = stop_guard(s, max_stop_blocks=3)
    assert blocked is False and reason == "escalate"


def test_stop_guard_allows_when_no_ready_work():
    s = _ready_state()
    s.creative.paused = True  # nothing becomes ready while paused
    blocked, reason = stop_guard(s)
    assert blocked is False and reason == "no_ready_work"


def test_reminder_book_complete_message():
    done = _complete_state()
    assert "hoàn tất" in build_reminder(done)
