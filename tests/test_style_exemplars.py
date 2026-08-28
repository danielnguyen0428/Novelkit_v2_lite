"""Per-novel style exemplar bank — positive few-shot from the writer's own
highest-reviewed prose (Tier 1 self-learning; P19 derivative, never canon)."""

from __future__ import annotations

import json

from plugins.context_engine.novelkit_context import (
    AuthorityTier,
    authority_rank_for_path,
)
from tools.novelkit_style_coherence_tool import (
    STYLE_EXEMPLARS_REL,
    build_exemplar_bank,
)

_GOOD = (
    "Mộc Trần đứng lặng trên đỉnh núi, dõi mắt về phương xa thật lâu không nói. "
    "Gió lạnh thổi qua vạt áo, cuốn theo vài cánh hoa rơi xuống khe đá sâu hút. "
    "Hắn khẽ thở dài, trong lòng dâng lên một nỗi cô tịch khó gọi thành tên."
)


def _write_chapter(novel_path, chapter, body):
    d = novel_path / "chapters"
    d.mkdir(exist_ok=True)
    (d / f"chapter_{chapter:03d}.md").write_text(body, encoding="utf-8")


def _write_review(novel_path, chapter, score):
    d = novel_path / "reviews"
    d.mkdir(exist_ok=True)
    (d / f"chapter_{chapter:04d}_review.json").write_text(
        json.dumps({"chapter": chapter, "overall_score": score}), encoding="utf-8"
    )


def test_exemplar_bank_keeps_only_high_scorers(tmp_path):
    _write_chapter(tmp_path, 1, _GOOD)
    _write_chapter(tmp_path, 2, _GOOD)
    _write_review(tmp_path, 1, 90)   # exemplar
    _write_review(tmp_path, 2, 70)   # below bar → excluded
    bank = build_exemplar_bank(tmp_path, 2, window=10, min_score=85)
    chapters = [e["chapter"] for e in bank["exemplars"]]
    assert chapters == [1]
    assert (tmp_path / STYLE_EXEMPLARS_REL).exists()
    assert bank["exemplars"][0]["excerpt"]


def test_exemplar_bank_deterministic_and_bounded(tmp_path):
    for c in range(1, 6):
        _write_chapter(tmp_path, c, _GOOD)
        _write_review(tmp_path, c, 85 + c)  # all pass, ascending scores
    a = build_exemplar_bank(tmp_path, 5, window=10, min_score=85, max_items=3)
    b = build_exemplar_bank(tmp_path, 5, window=10, min_score=85, max_items=3)
    assert a == b  # deterministic (P19)
    assert len(a["exemplars"]) == 3  # bounded
    # Highest score wins; chapter 5 (score 90) ranks first.
    assert a["exemplars"][0]["chapter"] == 5


def test_exemplar_bank_empty_without_reviews(tmp_path):
    _write_chapter(tmp_path, 1, _GOOD)
    bank = build_exemplar_bank(tmp_path, 1, window=10)
    assert bank["exemplars"] == []


def test_exemplar_bank_excludes_strict_xianxia_register_violation(tmp_path):
    (tmp_path / "PROJECT_DNA.md").write_text(
        "---\ngenre: xianxia\nworld_era: Thượng Cổ\n---\n",
        encoding="utf-8",
    )
    _write_chapter(
        tmp_path,
        1,
        _GOOD + ' A Mãnh gọi với theo: "Trụ ơi, trở về dùng bữa với tao!"',
    )
    _write_review(tmp_path, 1, 99)

    bank = build_exemplar_bank(tmp_path, 1, window=10, min_score=85)

    assert bank["exemplars"] == []


def test_exemplars_is_derivative_not_canon():
    assert authority_rank_for_path("logs/style_exemplars.json") != AuthorityTier.CANON
