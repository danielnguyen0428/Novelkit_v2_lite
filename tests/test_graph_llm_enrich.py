"""LLM Knowledge-Graph enrichment at arc/volume boundaries (Req 9).

The enrichment step is flag-gated (``graph_llm_enrich``, default OFF), runs ONLY
at Hồi/Cuốn boundaries, is canon-first (facts land in episodic memory via the
existing commit path — the KG reads them up later), carries provenance, and
verifies every extracted fact against the source prose so a hallucinated
subject can never be committed (Req 9.3/9.4/9.5).

The LLM is fully mocked (``_FakeClient``); no network is touched.
"""

from __future__ import annotations

import json

from integrations.autonovel import (
    AutoNovelWorkspace,
    LoopStage,
    LoopStep,
)
from integrations.autonovel.llm_loop import LLMAutoNovelLoop
from plugins.memory.novelkit_memory import get_provider


# --------------------------------------------------------------------------- #
# Fakes / fixtures
# --------------------------------------------------------------------------- #


class _FakeClient:
    """Minimal stand-in for the real LLMClient (no network).

    Mirrors the real ``LLMClient.complete`` keyword-only signature and counts
    how many times it is called so the flag-off test can prove the enrichment
    call never fires.
    """

    fingerprint = "fake:graph"

    def __init__(self, payload: str = "{}") -> None:
        self._payload = payload
        self.calls = 0

    def complete(
        self,
        *,
        system: str = "",
        user: str = "",
        messages=None,
        temperature=None,
        max_tokens=None,
    ) -> str:
        self.calls += 1
        return self._payload


def _ws(tmp_path) -> AutoNovelWorkspace:
    return AutoNovelWorkspace(root=tmp_path)


def _arc_step(chapter: int) -> LoopStep:
    return LoopStep(
        task_key="arc.arc_001.summary", stage=LoopStage.ARC_SUMMARY,
        phase="arc_summary", command="SUMMARISE_ARC",
        agent_role="Quality Auditor", chapter=chapter, arc=None,
        input_paths=(), output_paths=("summaries/arc_arc_001.md",),
        context_query=None,
    )


# Extractor output: A↔B is grounded, A↔Zzz and entity "Zzz" are hallucinated.
_ENRICH_JSON = json.dumps(
    {
        "entities": [
            {"name": "A", "kind": "người"},
            {"name": "B", "kind": "người"},
            {"name": "Zzz", "kind": "người"},
        ],
        "relationships": [
            {"a": "A", "b": "B", "type": "sư đồ"},
            {"a": "A", "b": "Zzz", "type": "kẻ thù"},
        ],
        "events": [
            {"subject": "A", "event_type": "đột phá", "chapter": 8,
             "summary": "A đột phá cảnh giới"},
        ],
    },
    ensure_ascii=False,
)


def _write_chapter(tmp_path, chapter: int, text: str) -> None:
    (tmp_path / "chapters").mkdir(parents=True, exist_ok=True)
    (tmp_path / "chapters" / f"chapter_{chapter:03d}.md").write_text(
        text, encoding="utf-8"
    )


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


def test_enrich_skipped_when_flag_off(tmp_path):
    """Flag OFF (explicit override): the boundary handler still writes its summary,
    but no extractor call fires and no enrichment fact is committed (Req 9.5)."""
    ws = _ws(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "longform.json").write_text(
        json.dumps({"flags": {"graph_llm_enrich": False}}), encoding="utf-8"
    )
    _write_chapter(tmp_path, 8, "A bái B làm thầy. A khổ luyện rồi đột phá cảnh giới.")
    client = _FakeClient(_ENRICH_JSON)
    loop = LLMAutoNovelLoop(client=client)

    result = loop.arc_summary(_arc_step(8), ws)

    # The arc summary artifact is still authored (base behaviour preserved).
    assert result.outcome == "done"
    assert (tmp_path / "summaries" / "arc_arc_001.md").exists()
    # No extractor call, no memory facts.
    assert client.calls == 0
    assert get_provider().store(tmp_path).all_items() == []


def test_enrich_commits_verified_facts_when_flag_on(tmp_path):
    """Flag ON: at the arc boundary the extractor is called once; only facts
    whose subjects are present in the source prose survive verification, and
    they are committed canon-first with provenance (Req 9.3/9.4)."""
    ws = _ws(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "longform.json").write_text(
        json.dumps({"flags": {"graph_llm_enrich": True}}), encoding="utf-8"
    )
    _write_chapter(tmp_path, 8, "A bái B làm thầy. A khổ luyện rồi đột phá cảnh giới.")
    client = _FakeClient(_ENRICH_JSON)
    loop = LLMAutoNovelLoop(client=client)

    loop.arc_summary(_arc_step(8), ws)

    # Exactly one extractor call fired for the enrichment.
    assert client.calls == 1

    items = get_provider().store(tmp_path).all_items()
    subjects = {i.subject for i in items}

    # Hallucinated subject never lands in memory (verify dropped it, Req 9.4).
    assert not any("Zzz" in s for s in subjects)

    # Grounded relationship A↔B committed with provenance + canonical subject.
    rels = [i for i in items if i.category.value == "relationships"]
    assert len(rels) == 1
    rel = rels[0]
    assert rel.subject == "A↔B"
    assert rel.payload.get("a") == "A" and rel.payload.get("b") == "B"
    assert rel.payload.get("source") == "graph_llm_enrich"
    assert rel.payload.get("provenance_chapter") == 8
    assert rel.source_chapter == 8
    assert rel.source_commit_id == "graph_enrich_8"

    # The grounded event is recorded on the timeline layer.
    timeline = [i for i in items if i.category.value == "timeline"]
    assert any(i.subject == "A" for i in timeline)

    # Grounded entities A and B are captured; the hallucinated one is not.
    cast = {i.subject for i in items if i.category.value == "minor_cast"}
    assert {"A", "B"} <= cast
    assert "Zzz" not in cast


def test_enrich_handles_bad_json_without_crashing(tmp_path):
    """A non-JSON extractor reply must not break the boundary handler and must
    commit nothing (best-effort, Req 9)."""
    ws = _ws(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "longform.json").write_text(
        json.dumps({"flags": {"graph_llm_enrich": True}}), encoding="utf-8"
    )
    _write_chapter(tmp_path, 8, "A gặp B trong mưa.")
    loop = LLMAutoNovelLoop(client=_FakeClient("xin lỗi, không có JSON ở đây"))

    result = loop.arc_summary(_arc_step(8), ws)

    assert result.outcome == "done"
    assert get_provider().store(tmp_path).all_items() == []
