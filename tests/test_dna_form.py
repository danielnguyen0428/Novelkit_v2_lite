"""Unit tests for webapp.api.dna_form style-field handling (root-cause fix).

The enrich flow left a permanent ``[Tự sinh]`` + unchecked pre-flight when the
model answered the style fields (``style_model`` / ``worldbuilding_guide``) with
an author name or prose instead of the bare code: parse_generated dropped the
value and the enrich loop could never reach "done". These cover the two-part
fix — normalise recoverable answers, and deterministically default the rest.
"""

from __future__ import annotations

import json

import bootstrap  # noqa: F401
from webapp.api import dna_form


def _parse(mapping: dict) -> dict:
    return dna_form.parse_generated(json.dumps(mapping, ensure_ascii=False), "xianxia")


def test_parse_generated_normalizes_style_full_name():
    # "Nhĩ Căn" is the author name for code NC → recovered, not dropped.
    assert _parse({"style_model": "Nhĩ Căn"}).get("style_model") == "NC"


def test_parse_generated_normalizes_style_label_and_code():
    assert _parse({"style_model": "NC — Nhĩ Căn"}).get("style_model") == "NC"
    assert _parse({"worldbuilding_guide": "td"}).get("worldbuilding_guide") == "TD"


def test_parse_generated_drops_unmappable_style():
    # Pure prose cannot map to a code → dropped (the enrich default handles it).
    assert "style_model" not in _parse({"style_model": "một phong cách huyền ảo"})


def test_parse_generated_rejects_foreign_genre_code():
    # KV is an urban code, invalid for xianxia → dropped.
    assert "style_model" not in _parse({"style_model": "KV"})


def test_parse_generated_normalizes_secondary_style_against_secondary_genre():
    parsed = _parse({"genre_secondary": "romance", "style_secondary": "CM"})
    assert parsed["style_secondary"] == "CM"


def test_apply_style_defaults_fills_blank():
    fields = {"genre": "xianxia", "style_model": "", "worldbuilding_guide": ""}
    dna_form.apply_style_defaults(fields)
    assert fields["style_model"] == "NC"  # genre's first canonical author code
    assert fields["worldbuilding_guide"] == "NC"  # follows style_model


def test_apply_style_defaults_worldbuilding_follows_style_model():
    fields = {"genre": "xianxia", "style_model": "VN", "worldbuilding_guide": ""}
    dna_form.apply_style_defaults(fields)
    assert fields["worldbuilding_guide"] == "VN"


def test_apply_style_defaults_respects_only():
    # Only default the requested key; never pre-empt one whose batch hasn't run.
    fields = {"genre": "xianxia", "style_model": "", "worldbuilding_guide": ""}
    dna_form.apply_style_defaults(fields, only={"style_model"})
    assert fields["style_model"] == "NC"
    assert fields["worldbuilding_guide"] == ""


def test_apply_style_defaults_does_not_override_existing():
    fields = {"genre": "xianxia", "style_model": "TT", "worldbuilding_guide": "PL"}
    dna_form.apply_style_defaults(fields)
    assert fields["style_model"] == "TT"
    assert fields["worldbuilding_guide"] == "PL"


def test_apply_style_defaults_fills_hybrid_secondary_author():
    fields = {
        "genre": "xianxia",
        "genre_secondary": "romance",
        "style_model": "VN",
        "style_secondary": "",
        "worldbuilding_guide": "VN",
    }
    dna_form.apply_style_defaults(fields, only={"style_secondary"})
    assert fields["style_secondary"] == "CM"


def test_preflight_rejects_unknown_author_and_worldbuilding_codes():
    fields = {
        "genre": "xianxia",
        "style_model": "UNKNOWN",
        "worldbuilding_guide": "UNKNOWN",
    }
    assert dna_form._preflight_state(fields)["style"] is False


def test_normalize_style_selections_canonicalizes_sidecar_author_codes():
    fields = {
        "genre": "xianxia",
        "genre_secondary": "romance",
        "style_model": "Vong Ngữ",
        "worldbuilding_guide": "VN",
        "style_secondary": "Cố Mạn",
    }
    assert dna_form.normalize_style_selections(fields) == []
    assert fields["style_model"] == "VN"
    assert fields["style_secondary"] == "CM"


def test_enrichment_never_requests_style_routing_from_the_model():
    """Style/worldbuilding codes are routing, not creative content.

    They pick which ``*_rules.md`` profile becomes the top voice authority for
    every chapter, so a model guessing one silently rewrites the novel's voice.
    Enrich must never ask for them (they are resolved deterministically by
    :func:`apply_style_defaults` from the author's selection instead), for a
    plain genre and for a hybrid alike.
    """
    for key in dna_form.STYLE_ROUTING_KEYS:
        assert key not in dna_form.enrich_ids_for_genre("xianxia")
        assert key not in dna_form.blocking_enrich_ids_for_genre("xianxia")
        assert key not in dna_form.ENRICH_LABELS


def test_hybrid_enrich_prompt_lists_secondary_genres_author_codes():
    _system, user = dna_form.enrich_prompt(
        {"genre": "xianxia", "genre_secondary": "romance"},
        [("style_secondary", "Mã Đại Thần phụ")],
    )
    assert "Mã phong cách phụ hợp lệ (romance): CM, DH, DM, PNTT, TDO" in user


def test_generation_prompt_binds_tone_below_selected_style_contract():
    system, user = dna_form.generation_prompt(
        "Đại năng quy ẩn bán bánh bao.",
        "xianxia",
        output_language="vi",
    )
    prompt = system + "\n" + user
    assert "không được ghi đè" in prompt
    assert "tiếng lóng hiện đại" in prompt
    assert "không quá 2 câu cực ngắn" in prompt


def test_enrich_prompt_keeps_vn_as_neutral_metadata_even_for_hai_lay_tone():
    base = {
        "genre": "xianxia",
        "style_model": "VN",
        "tone": "hài lầy",
        "output_language": "vi",
    }
    system, user = dna_form.enrich_prompt(
        base,
        [("style_execution", "Cách thi triển giọng dự án")],
    )
    prompt = system + "\n" + user
    assert "VN" in prompt
    assert "không suy luận hoặc mô phỏng văn phong" in prompt
    assert "câu vừa làm trục" not in prompt
    assert "không được ghi đè" in prompt


def test_normalize_secondary_genre_clears_multivalue():
    # Root cause of "genre_secondary: romance, meta_genre": a model-fabricated
    # multi-value must collapse back to single-genre (not a valid hybrid).
    fields = {
        "genre": "xianxia",
        "genre_secondary": "romance, meta_genre",
        "style_secondary": "CM",
    }
    changed = dna_form.normalize_secondary_genre(fields)
    assert changed is True
    assert fields["genre_secondary"] == ""
    assert fields["style_secondary"] == ""


def test_normalize_secondary_genre_keeps_single_valid_hybrid():
    fields = {"genre": "xianxia", "genre_secondary": "romance"}
    changed = dna_form.normalize_secondary_genre(fields)
    assert changed is False
    assert fields["genre_secondary"] == "romance"


def test_normalize_secondary_genre_clears_when_same_as_primary():
    fields = {"genre": "xianxia", "genre_secondary": "xianxia"}
    dna_form.normalize_secondary_genre(fields)
    assert fields["genre_secondary"] == ""


def test_normalize_secondary_genre_clears_unknown():
    fields = {"genre": "xianxia", "genre_secondary": "khong_ton_tai"}
    dna_form.normalize_secondary_genre(fields)
    assert fields["genre_secondary"] == ""


def test_gen_skip_covers_routing_and_style_choices():
    # The author's create-form selection is authoritative — the model must never
    # invent genre_secondary / hybrid_ratio / any style code in Quick Setup.
    for key in (
        "genre_secondary", "hybrid_ratio",
        "style_model", "style_secondary", "worldbuilding_guide",
    ):
        assert key in dna_form._GEN_SKIP


def test_style_routing_keys_are_never_enrichable():
    """Routing/style codes must not be in ENRICH_KEYS.

    ``style_model`` selects the ``*_rules.md`` profile that becomes the top voice
    authority for every chapter, so a model guessing it silently rewrites the
    whole novel's voice. Asking the model for it was the remaining leak after
    ``_GEN_SKIP`` closed the generation path: Quick Setup left the field blank,
    enrich counted it "missing" and requested it. It is now resolved purely by
    :func:`apply_style_defaults` from the author's genre/form selection.
    """
    enrich_ids = {key for key, _ in dna_form.ENRICH_KEYS}
    assert dna_form.STYLE_ROUTING_KEYS.isdisjoint(enrich_ids)
    for genre in ("xianxia", "romance", "urban", "scifi", "time_travel"):
        assert dna_form.STYLE_ROUTING_KEYS.isdisjoint(
            set(dna_form.enrich_ids_for_genre(genre))
        )


def test_gen_skip_is_derived_from_style_routing_keys():
    # The two exclusion sets must not drift apart.
    assert dna_form.STYLE_ROUTING_KEYS <= dna_form._GEN_SKIP


def test_normalize_style_code_rejects_prose_that_merely_mentions_an_author():
    """The old two-way substring match bound any prose containing an author name.

    "không dùng lối Vong Ngữ" resolved to VN — the exact opposite of what it
    says — and silently became the novel's top style authority.
    """
    for prose in (
        "giọng trầm, không dùng lối Vong Ngữ",
        "kết hợp Nhĩ Căn và Thiên Tằm Thổ Đậu",
        "phong cách tương tự Nhĩ Căn nhưng nhanh hơn",
    ):
        assert dna_form._normalize_style_code(prose, "xianxia") == ""


def test_normalize_style_code_still_accepts_exact_forms():
    for value, expected in (
        ("NC", "NC"),
        ("nc", "NC"),
        ("[NC]", "NC"),
        ("NC — Nhĩ Căn", "NC"),
        ("NC - Nhĩ Căn", "NC"),
        ("Nhĩ Căn", "NC"),
        ("Vong Ngữ", "VN"),
    ):
        assert dna_form._normalize_style_code(value, "xianxia") == expected


def test_normalize_style_code_resolves_pen_name_aliases():
    # "ZT — Zhttty / Trương Hằng": either side of the slash is a valid answer.
    assert dna_form._normalize_style_code("Zhttty", "time_travel") == "ZT"
    assert dna_form._normalize_style_code("Trương Hằng", "time_travel") == "ZT"


def test_normalize_style_code_does_not_cross_genre_code_collision():
    # TT is Thiên Tằm Thổ Đậu in xianxia but Trửu Tử in time_travel.
    assert dna_form._normalize_style_code("Trửu Tử", "xianxia") == ""
    assert dna_form._normalize_style_code("Thiên Tằm Thổ Đậu", "time_travel") == ""


# --------------------------------------------------------------------------- #
# Worldbuilding canon grounding for DNA enrichment.
#
# Root cause it guards: enrich_prompt showed the model only the bare code
# ("style_model: NC") and never the guide that code selects, so the power ladder
# was invented from the logline. A real NC novel ended up with
# "Tập Khí → Luyện Hồn → Ngộ Đạo → Vô Âm" while the actual canon
# ([NC] NhiCan_Worldbuilding_Complete.md) defines the four-Bộ Tiên Nghịch spine.
# That fabrication then sat in PROJECT_DNA outranking canon for every chapter.
# --------------------------------------------------------------------------- #

import pytest

_XIANXIA_WB_CODES = ["NC", "TD", "CD", "DG", "PL", "TH", "TT", "VN"]


@pytest.mark.parametrize("code", _XIANXIA_WB_CODES)
def test_worldbuilding_excerpt_covers_every_shipped_guide(code: str):
    """Each guide must yield BOTH its pillars and its power-system part.

    The ``##`` sub-headings are named per master, so this matches the stable
    ``#`` parts instead ("TỔNG QUAN: ADN SÁNG TÁC" + "PHẦN I"). CD ships without
    the ``[CODE]`` filename prefix and is resolved via ``_WB_FILE_ALIAS``.
    """
    excerpt = dna_form.worldbuilding_excerpt("xianxia", code)
    assert excerpt, f"no worldbuilding excerpt for {code}"
    assert "TỔNG QUAN: ADN SÁNG TÁC" in excerpt
    assert "PHẦN I" in excerpt


def test_worldbuilding_excerpt_keeps_the_canon_realm_ladder():
    # The exact names the model previously failed to use for an NC novel.
    excerpt = dna_form.worldbuilding_excerpt("xianxia", "NC")
    for realm in ("Ngưng Khí", "Trúc Cơ", "Kết Đan", "Vấn Đỉnh", "Đạp Thiên"):
        assert realm in excerpt


def test_worldbuilding_excerpt_empty_for_masters_without_a_guide():
    # OT / PT deliberately ship no guide (those authors rebuild the world per
    # work), so grounding is skipped rather than faked.
    assert dna_form.worldbuilding_excerpt("xianxia", "OT") == ""
    assert dna_form.worldbuilding_excerpt("xianxia", "PT") == ""


def test_worldbuilding_excerpt_empty_for_genres_without_guides():
    assert dna_form.worldbuilding_excerpt("romance", "CM") == ""
    assert dna_form.worldbuilding_excerpt("xianxia", "") == ""


def test_enrich_prompt_grounds_world_fields_in_the_selected_guide():
    _system, user = dna_form.enrich_prompt(
        {
            "genre": "xianxia",
            "style_model": "NC",
            "worldbuilding_guide": "NC",
            "logline": "Một nhạc sư mù luyện đàn không thanh âm.",
        },
        [("system_tiers", "Các cấp bậc")],
    )
    assert "ĐẠO THƯ DỰNG GIỚI ĐÃ CHỌN" in user
    assert "Ngưng Khí" in user          # canon ladder reached the model
    assert "Cấm tự bịa một ladder" in user


def test_enrich_prompt_keeps_the_no_proper_noun_transfer_contract():
    """Option 1: inherit the STRUCTURE, never the source work's proper nouns."""
    _system, user = dna_form.enrich_prompt(
        {"genre": "xianxia", "worldbuilding_guide": "NC"},
        [("system_tiers", "Các cấp bậc")],
    )
    assert "KHẾ ƯỚC CHUYỂN GIAO" in user
    assert "không sao chép tên riêng" in user
    assert "tự đặt tên mới" in user


def test_enrich_prompt_omits_guide_for_non_world_batches():
    """Character/plot batches must not pay the ~6K-char canon cost."""
    _system, user = dna_form.enrich_prompt(
        {"genre": "xianxia", "worldbuilding_guide": "NC"},
        [("mc_name", "Tên nhân vật chính"), ("mc_ghost", "Vết thương cũ")],
    )
    assert "ĐẠO THƯ DỰNG GIỚI ĐÃ CHỌN" not in user
