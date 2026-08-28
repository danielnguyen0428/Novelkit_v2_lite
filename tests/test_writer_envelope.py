"""Writer-envelope assembly + feature-flag gating (Req 5.4, 6.4, 7.2, 14.2)."""

from __future__ import annotations

import json

import bootstrap  # noqa: F401
from delegate import delegate_tool
from plugins.memory.novelkit_memory import get_provider


def _enable(novel_path, *flags):
    (novel_path / "config").mkdir(parents=True, exist_ok=True)
    (novel_path / "config" / "longform.json").write_text(
        json.dumps({"flags": {f: True for f in flags}}), encoding="utf-8"
    )


def _disable(novel_path, *flags):
    (novel_path / "config").mkdir(parents=True, exist_ok=True)
    (novel_path / "config" / "longform.json").write_text(
        json.dumps({"flags": {f: False for f in flags}}), encoding="utf-8"
    )


def _seed(novel_path):
    get_provider().commit_episodic(
        scope=novel_path,
        memory_facts=[
            {"category": "minor_cast", "subject": "Lão Chu", "field": "profile",
             "value": "chủ quán", "payload": {"first_seen": 3, "last_seen": 9,
                                              "appearance_count": 2}},
            {"category": "character_state", "subject": "Mộc Trần", "field": "realm",
             "value": "Trúc Cơ"},
        ],
        chapter=9, commit_id="c9",
    )


def test_envelope_empty_when_flags_off(tmp_path):
    _seed(tmp_path)
    _disable(tmp_path, "recall", "minor_cast", "style_stats")
    env = delegate_tool("novelkit_recall", action="assemble_writer_context",
                        novel_path=str(tmp_path), chapter=20)
    assert env["related_chapters"] == []
    assert env["recent_cast"] == []
    assert env["style_stats"] is None


def test_envelope_populated_when_flags_on(tmp_path):
    _seed(tmp_path)
    _enable(tmp_path, "recall", "minor_cast", "style_stats")
    env = delegate_tool("novelkit_recall", action="assemble_writer_context",
                        novel_path=str(tmp_path), chapter=20)
    names = {c["name"] for c in env["recent_cast"]}
    assert "Lão Chu" in names
    # related_chapters references strictly-earlier chapters
    assert all(r["chapter"] < 20 for r in env["related_chapters"])


def test_envelope_pure(tmp_path):
    _seed(tmp_path)
    _enable(tmp_path, "recall", "minor_cast")
    a = delegate_tool("novelkit_recall", action="assemble_writer_context",
                      novel_path=str(tmp_path), chapter=20)
    b = delegate_tool("novelkit_recall", action="assemble_writer_context",
                      novel_path=str(tmp_path), chapter=20)
    assert a == b
