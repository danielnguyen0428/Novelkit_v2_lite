"""Per-turn reminders + StopGuard — fact→instruction decoupling (Req 8).

Instructions for "what to do next" are **recomputed every turn** from the
durable ``PipelineState`` (the facts), as pure functions, instead of being
baked into prompts/history. The rendered ``<system-reminder>`` is ephemeral: it
is never persisted to state or conversation history (Property P20). The DAG
remains the source of truth — these functions are a read-only projection and
never mutate state.

``stop_guard`` is the completion guard: it blocks a run from ending while the
book is unfinished and work remains, escalating only after repeated blocks so
it can never loop forever (Property P21).
"""

from __future__ import annotations

from typing import Optional

from tools.novelkit_pipeline_tool import PipelineEngine, PipelineState, TaskStatus

_OPEN_STATUSES = (
    TaskStatus.PENDING.value,
    TaskStatus.RETRYABLE.value,
    TaskStatus.IN_PROGRESS.value,
)

DEFAULT_MAX_STOP_BLOCKS = 3


def _queues_nonempty(state: PipelineState) -> bool:
    return bool(state.creative.rewrite_queue or state.creative.polish_queue)


def book_complete(state: PipelineState) -> bool:
    """True when the whole book is finished: target reached (if known), no open
    tasks, and the rewrite/polish queues are empty."""
    target = state.target_chapters
    if target is not None and state.highest_completed_sync() < target:
        return False
    has_open = any(t.status in _OPEN_STATUSES for t in state.tasks.values())
    return not has_open and not _queues_nonempty(state)


def flow_reminder(state: PipelineState) -> str:
    """What to do next per the DAG (or the end-of-arc brake)."""
    engine = PipelineEngine(state)
    ready = engine.ready_tasks()
    if not ready:
        if state.breaker.is_open:
            return "Bộ ngắt đang mở — xử lý gốc lỗi rồi resume; không tự lặp."
        if _queues_nonempty(state):
            return "Không có task nền sẵn sàng; xử lý hàng đợi viết lại/đánh bóng trước."
        return "Không có task sẵn sàng."
    task = ready[0]
    return f"Bước kế: chạy `{task.task_key}` (vai {task.agent_role}, phase {task.phase})."


def queue_guard_reminder(state: PipelineState) -> str:
    """Forbid starting a new chapter while the rewrite/polish queue is non-empty."""
    n_rewrite = len(state.creative.rewrite_queue)
    n_polish = len(state.creative.polish_queue)
    if not (n_rewrite or n_polish):
        return ""
    return (
        f"Cấm bắt đầu chương mới: còn {n_rewrite} mục viết lại + "
        f"{n_polish} mục đánh bóng chưa xử lý."
    )


def book_complete_reminder(state: PipelineState) -> str:
    return "Toàn bộ sách đã hoàn tất; được phép kết thúc run." if book_complete(state) else ""


def build_reminder(
    state: PipelineState, doctor_blocking: Optional[list] = None
) -> str:
    """Compose the ephemeral ``<system-reminder>`` for this turn (pure, P20)."""
    lines: list[str] = []
    complete = book_complete_reminder(state)
    if complete:
        lines.append(complete)
    else:
        lines.append(flow_reminder(state))
        guard = queue_guard_reminder(state)
        if guard:
            lines.append(guard)
    for issue in doctor_blocking or []:
        code = getattr(issue, "code", None) or (
            issue.get("code") if isinstance(issue, dict) else str(issue)
        )
        lines.append(f"CHẶN (doctor): {code} — xử lý trước khi tiếp tục.")
    body = "\n".join(f"- {ln}" for ln in lines if ln)
    return f"<system-reminder>\n{body}\n</system-reminder>"


def stop_guard(
    state: PipelineState, *, max_stop_blocks: int = DEFAULT_MAX_STOP_BLOCKS
) -> tuple[bool, str]:
    """Return ``(blocked, reason)`` — pure, no mutation (Property P21).

    Blocked **iff** the book is not complete AND (a ready task exists OR a
    rewrite/polish queue is non-empty). Escalates (allows stop) once
    ``stop_block_count`` has reached ``max_stop_blocks`` so it never loops.
    """
    if book_complete(state):
        return (False, "book_complete")
    engine = PipelineEngine(state)
    has_ready = bool(engine.ready_tasks())
    if not (has_ready or _queues_nonempty(state)):
        return (False, "no_ready_work")
    if state.creative.stop_block_count >= max_stop_blocks:
        return (False, "escalate")
    return (True, "work_remaining")


__all__ = [
    "book_complete",
    "flow_reminder",
    "queue_guard_reminder",
    "book_complete_reminder",
    "build_reminder",
    "stop_guard",
    "DEFAULT_MAX_STOP_BLOCKS",
]
