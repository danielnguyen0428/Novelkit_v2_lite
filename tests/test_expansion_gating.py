"""Compass-mode expansion gating + agent-driven arc expansion (Req 2; P13, P14)."""

from __future__ import annotations

from tools.novelkit_pipeline_tool import PipelineEngine, TaskStatus


def _drive(engine: PipelineEngine, task_key: str) -> None:
    engine.plan_next(claim=True)
    engine.record_result(task_key, "done")


def test_compass_seeds_bootstrap_with_compass_task():
    eng = PipelineEngine.create(target_chapters=300, mode="compass", novel="x")
    keys = {t.task_key for t in eng.state.tasks.values()}
    assert "bootstrap.characters" in keys
    assert "bootstrap.compass" in keys
    # No chapter tasks seeded yet in compass mode.
    assert not any(k.startswith("chapter.") for k in keys)


def test_chapter_not_ready_until_arc_expanded():
    eng = PipelineEngine.create(target_chapters=300, mode="compass", novel="x")
    ready = {t.task_key for t in eng.ready_tasks()}
    assert "bootstrap.characters" in ready
    assert eng.state.creative.expanded_through_chapter == 0
    assert not any(k.startswith("chapter.0001") for k in ready)  # gated (P13)


def test_advance_expansion_unblocks_chapters_and_is_idempotent():
    eng = PipelineEngine.create(target_chapters=300, mode="compass", novel="x")
    inserted = eng.advance_expansion(12)  # expand arc 1 (chapters 1..12)
    assert inserted > 0
    assert eng.state.creative.expanded_through_chapter == 12
    # chapter 1 outline now exists and (after bootstrap) can become ready
    assert "chapter.0001.outline" in eng.state.tasks
    assert "chapter.0013.outline" not in eng.state.tasks  # beyond frontier (gated)
    # Idempotent: re-expanding the same frontier inserts nothing (P14).
    assert eng.advance_expansion(12) == 0


def test_legacy_mode_unaffected_by_gating():
    eng = PipelineEngine.create(target_chapters=10, novel="x", mode="full_plan")  # full_plan
    keys = {t.task_key for t in eng.state.tasks.values()}
    assert "chapter.0001.outline" in keys  # seeded as before
    assert "bootstrap.compass" not in keys  # no compass task in legacy
    # chapter 1 outline ready after master_outline done — no expansion gate
    assert eng._chapter_is_expanded(eng.state.tasks["chapter.0001.outline"]) is True


def test_compass_chapter_ready_after_full_bootstrap_and_expansion():
    eng = PipelineEngine.create(target_chapters=300, mode="compass", novel="x")
    for key in (
        "bootstrap.characters", "bootstrap.world", "bootstrap.plot_threads",
        "bootstrap.timeline", "bootstrap.master_outline", "bootstrap.compass",
    ):
        eng.state.tasks[key].status = TaskStatus.DONE.value
    eng.advance_expansion(12)
    ready = {t.task_key for t in eng.ready_tasks()}
    assert "chapter.0001.outline" in ready
