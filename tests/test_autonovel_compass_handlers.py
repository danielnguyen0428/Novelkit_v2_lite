"""AutoNovel adapter wiring for compass stages + minor-cast (Req 1,2,3,6)."""

from __future__ import annotations

import json

from integrations.autonovel import (
    AutoNovelAdapter,
    AutoNovelWorkspace,
    InMemoryAutoNovelLoop,
    LoopStage,
    LoopStep,
)
from integrations.autonovel.adapter import stage_for_task
from tools.novelkit_compass_tool import read_arc_map
from tools.novelkit_pipeline_tool import build_task_specs


def _ws(tmp_path):
    return AutoNovelWorkspace(root=tmp_path)


def _compass_step():
    return LoopStep(
        task_key="bootstrap.compass", stage=LoopStage.COMPASS, phase="2",
        command="CREATE_COMPASS", agent_role="Plot Weaver", chapter=None, arc=None,
        input_paths=(), output_paths=("outlines/compass.md", "outlines/arc_map.json"),
        context_query=None,
    )


def test_compass_task_maps_to_compass_stage():
    specs = {t.task_key: t for t in build_task_specs(1, 0, mode="compass")}
    assert "bootstrap.compass" in specs
    assert stage_for_task(specs["bootstrap.compass"]) is LoopStage.COMPASS
    # a chapter outline (same phase "2") must still map to OUTLINE, not COMPASS
    chapter_specs = {t.task_key: t for t in build_task_specs(1, 1)}
    assert stage_for_task(chapter_specs["chapter.0001.outline"]) is LoopStage.OUTLINE


def test_inmemory_compass_handler_writes_artifacts(tmp_path):
    ws = _ws(tmp_path)
    res = InMemoryAutoNovelLoop().compass(_compass_step(), ws)
    assert res.outcome == "done"
    assert (tmp_path / "outlines" / "compass.md").exists()
    arcs = read_arc_map(tmp_path).arcs
    assert {a.arc_id for a in arcs} == {"arc_001", "arc_002"}
    read_arc_map(tmp_path).validate()


def test_adapter_compass_run_crosses_arc_boundaries(tmp_path):
    ws = _ws(tmp_path)
    loop = InMemoryAutoNovelLoop(use_real_sync=False)
    adapter = AutoNovelAdapter.create(
        workspace=ws, loop=loop, target_chapters=16, mode="compass", novel="demo",
    )
    report = adapter.run(max_steps=500)
    assert report.stopped_reason == "drained"

    # Both arc summaries authored at their boundaries (Req 3 / P15 wiring).
    assert (tmp_path / "summaries" / "arc_arc_001.md").exists()
    assert (tmp_path / "summaries" / "arc_arc_002.md").exists()

    # Expansion frontier advanced across both arcs (Req 2; gating respected).
    assert adapter.engine.state.creative.expanded_through_chapter == 16

    # Both arcs ended up "done" with concrete bounds (no gap/overlap).
    arc_map = read_arc_map(tmp_path)
    arc_map.validate()
    statuses = {a.arc_id: a.status for a in arc_map.arcs}
    assert statuses == {"arc_001": "done", "arc_002": "done"}

    # Checkpoints recorded the new long-form steps.
    cp = (tmp_path / "logs" / "checkpoints.jsonl").read_text(encoding="utf-8")
    assert "arc_expanded" in cp and "arc_summary_written" in cp and "compass_updated" in cp

    # Volume boundary fired at the last arc of vol_001 (Req 3.2 / 1.4).
    assert (tmp_path / "summaries" / "volume_vol_001.md").exists()
    assert "volume_summary_written" in cp


def test_adapter_commit_minor_cast_sidecar_then_bump(tmp_path):
    ws = _ws(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "longform.json").write_text(
        json.dumps({"flags": {"minor_cast": True}}), encoding="utf-8"
    )
    adapter = AutoNovelAdapter.create(
        workspace=ws, loop=InMemoryAutoNovelLoop(use_real_sync=False),
        target_chapters=4, novel="demo",
    )
    (tmp_path / "drafts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "drafts" / "chapter_0002.cast.json").write_text(
        json.dumps([{"name": "Lão Chu", "brief_role": "chủ quán"}]), encoding="utf-8"
    )
    (tmp_path / "chapters").mkdir(parents=True, exist_ok=True)
    (tmp_path / "chapters" / "chapter_002.md").write_text("Lão Chu rót rượu.", encoding="utf-8")

    adapter._commit_minor_cast(2)  # intro from sidecar
    from plugins.memory.novelkit_memory import recent_cast

    item = [i for i in recent_cast(tmp_path) if i.subject == "Lão Chu"][0]
    assert item.payload["first_seen"] == 2

    # next chapter mentions the name (no sidecar) → appearance bump (P18)
    (tmp_path / "chapters" / "chapter_003.md").write_text("Lão Chu lại xuất hiện.", encoding="utf-8")
    adapter._commit_minor_cast(3)
    item = [i for i in recent_cast(tmp_path) if i.subject == "Lão Chu"][0]
    assert item.payload["last_seen"] == 3
    assert item.payload["appearance_count"] >= 2


def test_minor_cast_noop_when_flag_off(tmp_path):
    # Explicitly disable minor_cast flag via per-novel config override.
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "longform.json").write_text(
        json.dumps({"flags": {"minor_cast": False}}), encoding="utf-8"
    )
    ws = _ws(tmp_path)
    adapter = AutoNovelAdapter.create(
        workspace=ws, loop=InMemoryAutoNovelLoop(use_real_sync=False),
        target_chapters=4, novel="demo",
    )
    (tmp_path / "drafts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "drafts" / "chapter_0002.cast.json").write_text(
        json.dumps([{"name": "Lão Chu", "brief_role": "chủ quán"}]), encoding="utf-8"
    )
    adapter._commit_minor_cast(2)  # flag off → no-op
    from plugins.memory.novelkit_memory import recent_cast

    assert recent_cast(tmp_path) == []


class _FakeClient:
    """Minimal stand-in for the LLM client (no network)."""

    fingerprint = "fake:test"

    def complete(self, *, system="", user="", temperature=0.7, max_tokens=1000):
        return "MC đạt Đại Thừa, trả xong nợ nhân quả với sư môn."


def test_llm_loop_compass_authors_multi_volume_skeleton(tmp_path):
    """The real LLM loop's compass must size the skeleton from target_chapters
    across multiple volumes (fixes the 'one-arc drain' — review #1)."""
    from integrations.autonovel.llm_loop import LLMAutoNovelLoop

    ws = _ws(tmp_path)
    (tmp_path / "PROJECT_DNA.md").write_text(
        "---\ntitle: Demo\ngenre: xianxia\ntarget_chapters: 130\n---\n# Demo\n",
        encoding="utf-8",
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())
    loop.compass(_compass_step(), ws)

    arc_map = read_arc_map(tmp_path)
    arc_map.validate()  # partition/min-len invariants hold (P16)
    # ceil(130/12) = 11 arcs, grouped 5 per volume → 3 volumes
    assert len(arc_map.arcs) == 11
    assert len({a.volume_id for a in arc_map.arcs}) == 3
    assert all(a.status == "skeleton" for a in arc_map.arcs)
    compass_md = (tmp_path / "outlines" / "compass.md").read_text(encoding="utf-8")
    assert "nợ nhân quả" in compass_md  # ending direction from the client


class _CastClient:
    """Fake client returning a cast-intro JSON array (wrapped in prose)."""

    fingerprint = "fake:cast"

    def complete(self, *, system="", user="", temperature=0.7, max_tokens=1000):
        return 'Kết quả:\n[{"name":"Lão Chu","brief_role":"chủ quán Thanh Vân"}]\nHết.'


def test_llm_loop_emits_cast_intros_sidecar(tmp_path):
    """Seam #1: the LLM writer emits a cast sidecar that sync promotes into the
    minor-cast roster (flag-gated)."""
    from integrations.autonovel.llm_loop import LLMAutoNovelLoop

    ws = _ws(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "longform.json").write_text(
        json.dumps({"flags": {"minor_cast": True}}), encoding="utf-8"
    )
    LLMAutoNovelLoop(client=_CastClient())._emit_cast_intros(
        ws, 3, "Lão Chu rót rượu cho khách lạ."
    )
    sidecar = tmp_path / "drafts" / "chapter_0003.cast.json"
    assert sidecar.exists()
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    assert data[0]["name"] == "Lão Chu"
    assert "chủ quán" in data[0]["brief_role"]


def test_cast_intros_noop_when_flag_off(tmp_path):
    from integrations.autonovel.llm_loop import LLMAutoNovelLoop

    # Explicitly disable minor_cast flag via per-novel config override.
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "longform.json").write_text(
        json.dumps({"flags": {"minor_cast": False}}), encoding="utf-8"
    )
    ws = _ws(tmp_path)
    LLMAutoNovelLoop(client=_CastClient())._emit_cast_intros(ws, 3, "text có Lão Chu")
    assert not (tmp_path / "drafts" / "chapter_0003.cast.json").exists()


def test_doctor_clean_when_run_ends_on_volume_boundary(tmp_path):
    """A novel that finishes exactly on a volume boundary must not report a
    stale RAG index. Boundary maintenance (arc_summary, arc_map 'done',
    volume_summary, compass refresh, next-arc skeleton) writes canon AFTER the
    final sync's reindex; without a reindex at the end of boundary maintenance
    the doctor sees the index as stale and raises a blocking rag_index_stale.
    """
    from tools.novelkit_sync_tool import health_check

    ws = _ws(tmp_path)
    # InMemoryAutoNovelLoop.compass declares vol_001 = arc_001(1-8)+arc_002(9-16);
    # chapter 16 is the last chapter of the volume's last arc → volume boundary.
    adapter = AutoNovelAdapter.create(
        workspace=ws, loop=InMemoryAutoNovelLoop(), target_chapters=16, mode="compass"
    )
    report = adapter.run()
    assert report.chapters_synced == 16
    assert report.final_status == "completed"

    blocking = [i for i in health_check(tmp_path) if i.severity == "error"]
    codes = {i.code for i in blocking}
    assert "rag_index_stale" not in codes, f"stale index after boundary: {codes}"
