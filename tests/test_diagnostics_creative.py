"""Creative-health diagnostics, 4 dimensions, read-only (Req 10; Property P23)."""

from __future__ import annotations

import hashlib
import json

import bootstrap  # noqa: F401
from delegate import delegate_tool
from plugins.memory.novelkit_memory import get_provider
from tools.novelkit_diagnostics_tool import diagnose


def _write_chapter(root, n):
    d = root / "chapters"
    d.mkdir(exist_ok=True)
    (d / f"chapter_{n:03d}.md").write_text(f"# Ch {n}\nnội dung", encoding="utf-8")


def _write_review(root, n, score, outcome):
    d = root / "reviews"
    d.mkdir(exist_ok=True)
    (d / f"chapter_{n:04d}_review.json").write_text(
        json.dumps({"chapter": n, "overall_score": score, "gate_outcome": outcome}),
        encoding="utf-8",
    )


def test_review_low_score_and_rewrite_rate(tmp_path):
    for n in (1, 2, 3, 4):
        _write_chapter(tmp_path, n)
    _write_review(tmp_path, 1, 90, "pass")
    _write_review(tmp_path, 2, 60, "hard_fail")
    _write_review(tmp_path, 3, 55, "hard_fail")
    _write_review(tmp_path, 4, 88, "pass")
    codes = {f["code"] for f in diagnose(tmp_path)}
    assert "review_score_low" in codes
    assert "rewrite_rate_high" in codes
    for f in diagnose(tmp_path):
        assert f["evidence"] and f["suggestion"]  # every finding actionable


def test_chapter_number_skip(tmp_path):
    for n in (1, 2, 4):  # missing 3
        _write_chapter(tmp_path, n)
    codes = {f["code"] for f in diagnose(tmp_path)}
    assert "chapter_number_skip" in codes


def test_character_disappeared(tmp_path):
    for n in range(1, 31):
        _write_chapter(tmp_path, n)
    get_provider().commit_episodic(
        scope=tmp_path,
        memory_facts=[{"category": "character_state", "subject": "Mộc Trần",
                       "field": "realm", "value": "Luyện Khí"}],
        chapter=1, commit_id="c1",
    )
    codes = {f["code"] for f in diagnose(tmp_path)}
    assert "character_disappeared" in codes


def test_compass_missing_when_arcmap_present(tmp_path):
    _write_chapter(tmp_path, 1)
    delegate_tool("novelkit_compass", action="upsert_arc", novel_path=str(tmp_path),
                  arc={"arc_id": "arc_001", "start_chapter": 1, "end_chapter": 12,
                       "estimated_chapters": 12, "arc_type": "tournament",
                       "status": "detailed"})
    codes = {f["code"] for f in diagnose(tmp_path)}
    assert "compass_missing" in codes


def test_diagnose_is_read_only(tmp_path):
    for n in (1, 2, 4):
        _write_chapter(tmp_path, n)
    _write_review(tmp_path, 1, 50, "hard_fail")

    def _snapshot():
        h = hashlib.sha256()
        for p in sorted(tmp_path.rglob("*")):
            if p.is_file():
                h.update(p.relative_to(tmp_path).as_posix().encode())
                h.update(p.read_bytes())
        return h.hexdigest()

    before = _snapshot()
    diagnose(tmp_path)
    diagnose(tmp_path, redact=True)
    assert _snapshot() == before  # no canon/state mutation (P23)


def test_diagnose_deterministic_and_redaction(tmp_path):
    _write_chapter(tmp_path, 1)
    _write_review(tmp_path, 1, 50, "hard_fail")
    assert diagnose(tmp_path) == diagnose(tmp_path)  # deterministic
    red = diagnose(tmp_path, redact=True)
    assert all(f["evidence"].get("redacted") for f in red)
