"""End-to-end compass-mode smoke (Req 13.2; Properties P12, P13, P15)."""

from __future__ import annotations

import bootstrap  # noqa: F401
from delegate import delegate_tool
from tools.novelkit_pipeline_tool import PipelineEngine, PipelineState, TaskStatus

_BOOTSTRAP = (
    "bootstrap.characters", "bootstrap.world", "bootstrap.plot_threads",
    "bootstrap.timeline", "bootstrap.master_outline", "bootstrap.compass",
)


def _drive(engine: PipelineEngine, task_key: str) -> None:
    engine.plan_next(claim=True)
    engine.record_result(task_key, "done")


def _drive_bootstrap(engine: PipelineEngine) -> None:
    for key in _BOOTSTRAP:
        _drive(engine, key)


def test_compass_pipeline_end_to_end(tmp_path):
    eng = PipelineEngine.create(target_chapters=300, mode="compass", novel="demo")
    _drive_bootstrap(eng)
    assert all(eng.state.tasks[k].status == TaskStatus.DONE.value for k in _BOOTSTRAP)

    # Compass authored an arc map + expanded arc 1 (chapters 1..12).
    delegate_tool("novelkit_compass", action="upsert_arc", novel_path=str(tmp_path),
                  arc={"arc_id": "arc_001", "start_chapter": 1, "end_chapter": 12,
                       "estimated_chapters": 12, "arc_type": "growth_breakthrough",
                       "status": "detailed", "volume_id": "vol_001"})
    eng.advance_expansion(12)
    assert eng.state.creative.expanded_through_chapter == 12

    # P13: chapter 1 ready, chapter 13 not even seeded (beyond frontier).
    ready = {t.task_key for t in eng.ready_tasks()}
    assert "chapter.0001.outline" in ready
    assert "chapter.0013.outline" not in eng.state.tasks

    # Drive chapter 1 fully through the per-chapter chain.
    for suffix in ("outline", "write", "self_check", "review", "sync"):
        _drive(eng, f"chapter.0001.{suffix}")
    assert eng.state.tasks["chapter.0001.sync"].status == TaskStatus.DONE.value

    # P12: resume re-runs nothing done; orphaned in_progress reset only.
    eng.plan_next(claim=True)  # claim chapter 2 outline
    report = eng.resume()
    assert eng.state.tasks["chapter.0001.sync"].status == TaskStatus.DONE.value
    assert report.in_progress_reset >= 1
    assert report.next_task_key == "chapter.0002.outline"

    # P15: mark arc 1 done; doctor flags the missing arc summary, then clears.
    delegate_tool("novelkit_compass", action="upsert_arc", novel_path=str(tmp_path),
                  arc={"arc_id": "arc_001", "start_chapter": 1, "end_chapter": 12,
                       "estimated_chapters": 12, "arc_type": "growth_breakthrough",
                       "status": "done", "volume_id": "vol_001"})
    from tools.novelkit_sync_tool import health_check
    assert any(i.code == "summary_missing" for i in health_check(tmp_path))
    (tmp_path / "summaries").mkdir(exist_ok=True)
    (tmp_path / "summaries" / "arc_arc_001.md").write_text("tóm tắt", encoding="utf-8")
    (tmp_path / "summaries" / "volume_vol_001.md").write_text("tóm tắt", encoding="utf-8")
    assert not any(i.code == "summary_missing" for i in health_check(tmp_path))


def test_compass_state_roundtrips_through_store(tmp_path):
    """The compass-mode state must serialise + reload through the store with a
    valid digest (no schema/digest drift)."""
    from tools.novelkit_pipeline_state_store import PipelineStateStore

    eng = PipelineEngine.create(target_chapters=300, mode="compass", novel="demo")
    eng.advance_expansion(12)
    store = PipelineStateStore(tmp_path)
    store.save(eng.state)
    reloaded = store.load_state()
    assert reloaded.creative.mode == "compass"
    assert reloaded.creative.expanded_through_chapter == 12
    assert isinstance(reloaded, PipelineState)
