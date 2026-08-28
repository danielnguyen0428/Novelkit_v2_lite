"""Per-chapter style-stats self-mirror + repeated-sentence guard (Req 7; P19)."""

from __future__ import annotations

from plugins.context_engine.novelkit_context import (
    AuthorityTier,
    authority_rank_for_path,
)
from tools.novelkit_style_coherence_tool import (
    STYLE_STATS_REL,
    build_style_stats,
    repeated_sentence_findings,
)

_S1 = "Mộc Trần đứng lặng trên đỉnh núi, dõi mắt về phương xa thật lâu không nói."
_S2 = "Gió lạnh thổi qua vạt áo, cuốn theo vài cánh hoa rơi xuống khe đá sâu hút."
_S3 = "Hắn khẽ thở dài, trong lòng dâng lên một nỗi cô tịch khó gọi thành tên hôm nay."


def _write_chapter(novel_path, chapter, body):
    d = novel_path / "chapters"
    d.mkdir(exist_ok=True)
    (d / f"chapter_{chapter:03d}.md").write_text(body, encoding="utf-8")


def test_style_stats_deterministic_and_written(tmp_path):
    _write_chapter(tmp_path, 1, f"{_S1}\n\n{_S2}")
    _write_chapter(tmp_path, 2, f"{_S3}\n\n{_S2}")
    a = build_style_stats(tmp_path, 2, window=10)
    b = build_style_stats(tmp_path, 2, window=10)
    assert a == b  # deterministic (P19)
    assert (tmp_path / STYLE_STATS_REL).exists()
    assert a["through_chapter"] == 2 and a["sentence_count"] >= 3
    assert isinstance(a["top_openers"], list)


def test_style_stats_is_derivative_not_canon():
    # logs/ is derivative — style_stats must never rank as canon (P19).
    assert authority_rank_for_path("logs/style_stats.json") != AuthorityTier.CANON


def test_repeated_sentence_flagged_across_chapters():
    findings = repeated_sentence_findings(
        draft_text=f"{_S3}\n\n{_S1}",     # _S1 reused verbatim
        prev_texts=[f"{_S1}\n\n{_S2}"],
        window=3, repeat_max=1, min_len=40,
    )
    assert any(f["code"] == "REPEATED_SENTENCE" for f in findings)
    assert any(_S1 in f["sentence"] for f in findings)


def test_no_repeat_when_distinct():
    findings = repeated_sentence_findings(
        draft_text=_S3, prev_texts=[_S1], window=3, repeat_max=1, min_len=40
    )
    assert findings == []
