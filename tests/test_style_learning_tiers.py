"""Bước 2 & 3 self-learning: user-edit signal (Tier 1) + cross-novel global
craft profile (Tier 2). Both are P19 derivatives — never canon, context-only."""

from __future__ import annotations

import json

import tools.novelkit_style_coherence_tool as sct
from plugins.context_engine.novelkit_context import (
    AuthorityTier,
    authority_rank_for_path,
)
from tools.novelkit_style_coherence_tool import (
    STYLE_EDITS_REL,
    build_edit_signal,
    distill_global_profile,
    load_global_craft_metrics,
)

_DRAFT = (
    "Mộc Trần đứng lặng trên đỉnh núi, dõi mắt về phương xa thật lâu không nói. "
    "Gió lạnh thổi qua vạt áo, cuốn theo vài cánh hoa rơi xuống khe đá sâu hút. "
    "Hắn khẽ thở dài, trong lòng dâng lên một nỗi cô tịch khó gọi thành tên."
)
# User rewrote sentence 3 and kept the first two.
_EDITED = (
    "Mộc Trần đứng lặng trên đỉnh núi, dõi mắt về phương xa thật lâu không nói. "
    "Gió lạnh thổi qua vạt áo, cuốn theo vài cánh hoa rơi xuống khe đá sâu hút. "
    "Hắn nhắm mắt, để cơn gió cuốn đi cái mỏi mệt đọng lại suốt chặng đường dài."
)


def _write_draft(novel_path, chapter, body):
    d = novel_path / "drafts"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"chapter_{chapter:04d}.md").write_text(body, encoding="utf-8")


def _write_canon(novel_path, chapter, body):
    d = novel_path / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"chapter_{chapter:03d}.md").write_text(body, encoding="utf-8")


def _write_review(novel_path, chapter, score):
    d = novel_path / "reviews"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"chapter_{chapter:04d}_review.json").write_text(
        json.dumps({"chapter": chapter, "overall_score": score}), encoding="utf-8"
    )


# --- Tier 1: user-edit signal ---------------------------------------------


def test_edit_signal_captures_user_rewrite(tmp_path):
    # ch1 edited by user; ch2 just synced (draft==canon → no signal).
    _write_draft(tmp_path, 1, _DRAFT)
    _write_canon(tmp_path, 1, _EDITED)
    _write_draft(tmp_path, 2, _DRAFT)
    _write_canon(tmp_path, 2, _DRAFT)
    signal = build_edit_signal(tmp_path, 2, window=10)
    assert signal is not None
    assert signal["edited_chapters"] == [1]
    removed = [x["sentence"] for x in signal["removed_by_user"]]
    added = [x["sentence"] for x in signal["added_by_user"]]
    assert any("cô tịch" in s for s in removed)      # the deleted original
    assert any("mỏi mệt" in s for s in added)         # the user's replacement
    assert (tmp_path / STYLE_EDITS_REL).exists()


def test_edit_signal_none_when_no_edits(tmp_path):
    _write_draft(tmp_path, 1, _DRAFT)
    _write_canon(tmp_path, 1, _DRAFT)  # identical → not edited
    assert build_edit_signal(tmp_path, 1, window=10) is None


def test_edit_signal_deterministic(tmp_path):
    _write_draft(tmp_path, 1, _DRAFT)
    _write_canon(tmp_path, 1, _EDITED)
    a = build_edit_signal(tmp_path, 1, window=10)
    b = build_edit_signal(tmp_path, 1, window=10)
    assert a == b


def test_edit_signal_is_derivative_not_canon():
    assert authority_rank_for_path("logs/style_edits.json") != AuthorityTier.CANON


# --- Tier 2: cross-novel global craft profile ------------------------------


def test_global_profile_is_text_free_and_aggregates(tmp_path, monkeypatch):
    # Redirect the home-dir global store into tmp so the test is hermetic.
    gdir = tmp_path / "style_lab"
    monkeypatch.setattr(sct, "GLOBAL_STYLE_DIR", gdir)
    monkeypatch.setattr(sct, "GLOBAL_PROFILE_PATH", gdir / "global_profile.json")

    novel_a = tmp_path / "novel_a"
    _write_canon(novel_a, 1, _DRAFT)
    _write_review(novel_a, 1, 90)
    prof = distill_global_profile(novel_a, 1, window=10, min_score=85)
    assert prof is not None
    assert prof["novels_count"] == 1
    # Text-free: no prose/names, only numeric craft metrics.
    blob = json.dumps(prof)
    assert "Mộc Trần" not in blob
    assert set(prof["craft_metrics"]).issubset({
        "avg_sentence_words", "avg_paragraph_words",
        "dialogue_ratio", "lexical_diversity",
    })

    # A second novel folds in; idempotent per novel (re-run ≠ double count).
    novel_b = tmp_path / "novel_b"
    _write_canon(novel_b, 1, _EDITED)
    _write_review(novel_b, 1, 88)
    distill_global_profile(novel_b, 1, window=10, min_score=85)
    prof2 = distill_global_profile(novel_b, 1, window=10, min_score=85)
    assert prof2["novels_count"] == 2  # b counted once despite two runs

    metrics = load_global_craft_metrics()
    assert metrics is not None and metrics["novels_count"] == 2


def test_global_profile_none_without_high_scorers(tmp_path, monkeypatch):
    gdir = tmp_path / "style_lab"
    monkeypatch.setattr(sct, "GLOBAL_STYLE_DIR", gdir)
    monkeypatch.setattr(sct, "GLOBAL_PROFILE_PATH", gdir / "global_profile.json")
    novel = tmp_path / "novel"
    _write_canon(novel, 1, _DRAFT)
    _write_review(novel, 1, 70)  # below bar
    assert distill_global_profile(novel, 1, window=10, min_score=85) is None
