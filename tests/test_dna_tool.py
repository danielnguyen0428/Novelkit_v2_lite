"""Tests for the DNA tool (Task 9.5, Requirements 11/15/17).

Covers genre resolution (alias + composite + ratio validation), PROJECT_DNA
parsing, the deterministic enrichment plan, planning-doc bootstrap (incl.
idempotency), metadata sidecar helpers, and self-registration.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tools import registry
from tools.novelkit_dna_tool import (
    DEFAULT_COMPOSITE_RATIO,
    GenreSpec,
    bootstrap_docs,
    dna_tool,
    enrich,
    parse_composite_genre,
    parse_dna,
    resolve_genre,
    resolve_genre_spec,
    slugify_genre,
    slugify_title,
)


def _tmp() -> Path:
    return Path(tempfile.mkdtemp())


_DNA = """---
genre_primary: xianxia
target_chapters: 150
---
# PROJECT_DNA — Thí Đề Vạn Tâm
- **Tên tác phẩm:** Thí Đề
- **Nhân vật chính:** Lý Mỗ
- **Tư duy thế giới:** [Tư duy thế giới]
- **Tên pháp hệ:** Cửu Chuyển Đan Đạo
"""


# --------------------------------------------------------------------------- #
# Genre resolution
# --------------------------------------------------------------------------- #


def test_resolve_genre_canonical_slug() -> None:
    assert resolve_genre("xianxia") == "xianxia"
    assert resolve_genre("urban") == "urban"


def test_resolve_genre_vietnamese_alias() -> None:
    assert resolve_genre("tu tiên") == "xianxia"
    assert resolve_genre("xuyên việt") == "time_travel"


def test_resolve_genre_unknown_is_none() -> None:
    assert resolve_genre("một thể loại không tồn tại zzz") is None
    assert resolve_genre("") is None


def test_composite_genre_with_ratio() -> None:
    spec = resolve_genre_spec("thành phố với tu tiên 60-40")
    assert spec.primary == "urban"
    assert spec.secondary == "xianxia"
    assert spec.ratio == "60-40"
    assert spec.is_hybrid


def test_composite_default_ratio() -> None:
    primary, secondary, ratio = parse_composite_genre("thành phố với tu tiên")
    assert ratio == DEFAULT_COMPOSITE_RATIO


def test_composite_bad_ratio_raises() -> None:
    with pytest.raises(ValueError):
        parse_composite_genre("thành phố với tu tiên 60-50")


def test_too_many_genres_raises() -> None:
    with pytest.raises(ValueError):
        parse_composite_genre("tu tiên + đô thị + ngôn tình")


def test_slugify_helpers() -> None:
    assert slugify_genre("Tiên Hiệp") == "tien hiep"
    assert slugify_title("Thí Đề Vạn Tâm") == "thi_de_van_tam"
    assert slugify_title("") == "untitled_novel"


# --------------------------------------------------------------------------- #
# Parsing + enrichment
# --------------------------------------------------------------------------- #


def test_parse_dna_fields() -> None:
    parsed = parse_dna(_DNA)
    assert parsed.title == "Thí Đề"
    assert parsed.protagonist == "Lý Mỗ"
    assert parsed.genre_primary == "xianxia"


def test_enrich_flags_placeholders() -> None:
    result = enrich(_DNA)
    keys = {p["key"] for p in result["pending_fields"]}
    # The worldbuilding field is a placeholder → pending.
    assert "world_mindset" in keys
    # The system name is filled → not pending.
    assert "system_name" in result["filled_fields"]
    assert not result["complete"]


# --------------------------------------------------------------------------- #
# Bootstrap docs
# --------------------------------------------------------------------------- #


def test_bootstrap_docs_creates_and_is_idempotent() -> None:
    novel = _tmp()
    (novel / "PROJECT_DNA.md").write_text(_DNA, encoding="utf-8")
    first = bootstrap_docs(novel)
    assert set(first["updated"]) == {"PLAN.md", "GOAL_TRACKER.md", "memory/Memory.md"}
    assert (novel / "PLAN.md").exists()
    assert (novel / "GOAL_TRACKER.md").exists()
    assert (novel / "memory" / "Memory.md").exists()
    # Second run skips already-filled docs.
    second = bootstrap_docs(novel)
    assert second["updated"] == []


def test_bootstrap_missing_dna_raises() -> None:
    with pytest.raises(FileNotFoundError):
        bootstrap_docs(_tmp())


def test_tool_dispatch_resolve_genre() -> None:
    out = dna_tool("resolve_genre", genre_text="tu tiên")
    assert out["primary"] == "xianxia"


def test_self_registration() -> None:
    entry = registry.get("novelkit_dna")
    assert entry.fn is dna_tool


# --------------------------------------------------------------------------- #
# Property-based tests
# --------------------------------------------------------------------------- #


@settings(max_examples=150)
@given(st.text())
def test_resolve_genre_never_raises(text: str) -> None:
    result = resolve_genre(text)
    assert result is None or isinstance(result, str)


@settings(max_examples=100)
@given(st.text(), st.text())
def test_parse_dna_never_raises(text: str, meta_value: str) -> None:
    parsed = parse_dna(text, {"genre": meta_value})
    assert isinstance(parsed.frontmatter, dict)


@settings(max_examples=80)
@given(
    st.sampled_from(["tu tiên", "thành phố", "xuyên việt", "lãng mạn", "tận thế"]),
    st.sampled_from(["tu tiên", "thành phố", "khoa học viễn tưởng"]),
    st.integers(min_value=1, max_value=99),
)
def test_valid_composite_ratio_sums_to_100(prim: str, sec: str, share: int) -> None:
    ratio = f"{share}-{100 - share}"
    primary, secondary, resolved_ratio = parse_composite_genre(f"{prim} với {sec} {ratio}")
    assert resolved_ratio == ratio
    assert isinstance(primary, str)
    assert secondary is None or isinstance(secondary, str)
