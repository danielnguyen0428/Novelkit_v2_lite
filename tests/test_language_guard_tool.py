"""Tests for the unified language guard tool (Task 7, Requirements 12 & 17).

The headline property is **P6 — Language guard soundness** (design.md
§"Correctness Properties"):

    An operational / out-of-genre token that is not in the whitelist
    (primary ∪ secondary) is always flagged; a token in the whitelist is
    never flagged.
    **Validates: Requirements 12.1**

The tool merges the two legacy guards (``genre_language_guard.py`` +
``xianxia_language_guard.py``) into one genre-parameterized scanner (finding
D1): Xianxia is just a profile, the per-genre banned lists are profiles, and a
shared operational blocklist applies to every genre.

Also covered:
  - Task 7.1 — single merged tool, genre as a parameter (no Xianxia code path);
  - Task 7.2 — the xianxia profile lives at config/language_guard/xianxia.json;
  - Task 7.3 — hybrid: whitelist = primary ∪ secondary, tokens outside both are
    still flagged, primary wins (secondary only *adds* whitelist entries);
  - self-registration into the Hermes tool registry.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from tools import registry
from tools.novelkit_language_guard_tool import (
    _UNIVERSAL_OPERATIONAL_TERMS,
    LANGUAGE_GUARD_CONFIG_DIR,
    GuardProfile,
    Violation,
    blocking_violations,
    language_guard_tool,
    load_profile,
    modern_register_allowed,
    normalize_genre,
    scan,
    scan_result,
    term_pattern,
)

# Import the module so the self-registration side effect runs.
import tools.novelkit_language_guard_tool  # noqa: F401


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #

#: Genres that have a profile on disk (xianxia is frozen, the rest were ported
#: from genre_language_guard.py into config/language_guard/*.json).
_GENRES = ["xianxia", "urban", "romance", "scifi", "time_travel", "meta_genre"]

#: Clean Vietnamese filler that contains no banned/operational substring in any
#: profile — used to surround a term under test without introducing extra hits.
_CLEAN_PROSE = "Nàng lặng lẽ nhìn ngọn núi xa, gió đêm thổi qua mái tóc dài."


def _embed(term: str) -> str:
    """Place ``term`` inside clean prose with safe word boundaries."""
    return f"Nàng nhìn núi, {term} hiện ra giữa trời đêm."


def _flagged_terms(text: str, genre: str, secondary=None) -> set[str]:
    return {v.term.casefold() for v in scan(text, genre, secondary)}


def _candidate_terms(genre: str) -> list[str]:
    """All terms that *could* be flagged for ``genre``: universal + profile."""
    profile = load_profile(genre)
    terms = list(_UNIVERSAL_OPERATIONAL_TERMS)
    terms.extend(bt.term for bt in profile.banned_terms)
    return terms


# --------------------------------------------------------------------------- #
# Task 7.2 — xianxia is a profile, not code
# --------------------------------------------------------------------------- #


def test_xianxia_profile_exists_on_disk():
    assert (LANGUAGE_GUARD_CONFIG_DIR / "xianxia.json").is_file()
    profile = load_profile("xianxia")
    assert profile.genre == "xianxia"
    assert profile.banned_terms, "xianxia profile should carry its banned terms"


def test_xianxia_profile_declares_strict_classical_register():
    assert load_profile("xianxia").strict_classical_register is True


def test_strict_classical_xianxia_promotes_profile_warnings_to_blocking():
    violations = scan("Hắn kiểm tra hồ sơ rồi cân nhắc logic trong đó.", "xianxia")
    assert violations
    assert all(v.severity == "warning" for v in violations)
    assert blocking_violations(violations, "xianxia") == violations


def test_scan_result_reports_strict_profile_warning_as_error():
    result = scan_result(
        "Hắn kiểm tra hồ sơ rồi cân nhắc logic trong đó.",
        "xianxia",
    )

    assert result["severity"] == "error"
    assert result["passed"] is False


def test_all_ported_genre_profiles_present():
    for genre in _GENRES:
        assert (LANGUAGE_GUARD_CONFIG_DIR / f"{genre}.json").is_file(), genre
        assert load_profile(genre).banned_terms, f"{genre} profile has no banned terms"


def test_normalize_genre_aliases():
    assert normalize_genre("Sci-fi") == "scifi"
    assert normalize_genre("sci fi") == "scifi"
    assert normalize_genre("Time Travel") == "time_travel"
    assert normalize_genre("Meta Genre") == "meta_genre"
    assert normalize_genre("  XIANXIA ") == "xianxia"


# --------------------------------------------------------------------------- #
# Task 7.1 — merged behaviour: operational + per-genre bans in one tool
# --------------------------------------------------------------------------- #


def test_universal_operational_terms_blocked_in_any_genre():
    """Requirement 12.1: runtime/metadata/debug etc. blocked regardless of genre."""
    text = "Nhân vật chính mở debug rồi xem metadata trong runtime của pipeline."
    for genre in _GENRES:
        flagged = _flagged_terms(text, genre)
        for term in ("debug", "metadata", "runtime", "pipeline"):
            assert term in flagged, f"{term} not flagged for {genre}"


def test_urban_blocks_cultivation_terms():
    text = "Hắn bắt đầu tu luyện linh khí để đột phá cảnh giới."
    flagged = _flagged_terms(text, "urban")
    assert {"tu luyện", "linh khí", "đột phá", "cảnh giới"} <= flagged


def test_scifi_blocks_magic_terms():
    text = "Phi thuyền mang theo pháp bảo và linh đan của tông môn cổ."
    flagged = _flagged_terms(text, "scifi")
    assert {"pháp bảo", "linh đan", "tông môn"} <= flagged


def test_clean_prose_has_no_violations():
    for genre in _GENRES:
        assert scan(_CLEAN_PROSE, genre) == [], genre


def test_xianxia_blocks_reported_modern_register_regression():
    """The exact production-style failure must never pass the Xianxia guard.

    Register patterns remain context-aware: modern-setting canon can opt out,
    and ambiguous sound-count uses such as ``hai tiếng chuông`` stay allowed.
    """
    text = (
        "Thảo nào sư phụ ngày xưa bảo luyện thể là khổ — giờ tao mới hiểu, "
        "luyện cái thân xác này còn khổ hơn luyện bộ xương Tiên Cốt. "
        "Đứng hai tiếng đã kêu răng rắc như sắp gãy."
    )
    result = scan_result(text, "xianxia", "romance")
    flagged = {v["term"].casefold(): v for v in result["violations"]}

    assert {"giờ tao mới hiểu", "đứng hai tiếng"} <= set(flagged)
    assert all(flagged[term]["severity"] == "error" for term in flagged)
    assert result["passed"] is False


def test_xianxia_blocks_reported_colloquial_pronouns_in_traditional_register():
    text = (
        "— Trụ ơi, tối rồi về ăn cơm với tao! "
        "Giọng A Mãnh, thằng bạn từ nhỏ, lẫn trong tiếng gió. "
        "— Sao mày không nói sớm?"
    )
    result = scan_result(text, "xianxia", "meta_genre")

    assert result["passed"] is False
    assert any(
        violation["severity"] == "error"
        and violation["term"] == "đại từ khẩu ngữ tao/mày"
        for violation in result["violations"]
    )


def test_xianxia_blocks_modern_buddy_narration_without_pronouns():
    result = scan_result(
        "Giọng A Mãnh, thằng bạn từ nhỏ, lẫn trong tiếng gió.",
        "xianxia",
        "meta_genre",
    )

    assert result["passed"] is False
    assert any(
        violation["severity"] == "error"
        and violation["term"] == "thằng bạn từ nhỏ"
        for violation in result["violations"]
    )


def test_xianxia_blocks_modern_clock_duration_in_ancient_setting():
    result = scan_result(
        "Hắn đứng trước cửa động cả tiếng đồng hồ mà không dám bước vào.",
        "xianxia",
    )

    assert result["passed"] is False
    assert any(
        violation["term"] == "thời lượng hiện đại tính bằng giờ"
        for violation in result["violations"]
    )


def test_modern_register_exception_requires_explicit_setting_metadata():
    assert modern_register_allowed({"world_era": "Thượng Cổ Hồng Lam"}) is False
    assert modern_register_allowed({"world_era": "Tu tiên đô thị hiện đại"}) is True
    assert modern_register_allowed({"allow_modern_register": True}) is True


def test_declared_modern_xianxia_allows_modern_time_and_slang_terms():
    result = scan_result(
        "Cơ mà đã sáu giờ rồi, đứng hai tiếng khiến tao mệt vãi.",
        "xianxia",
        allow_modern_register=True,
    )
    assert result["passed"] is True


def test_xianxia_colloquial_pattern_does_not_flag_eyebrow_nouns():
    text = (
        "Đôi mày bạc của lão cau lại. Mặt mày hắn căng thẳng, "
        "lông mày rậm phủ xuống."
    )
    assert scan(text, "xianxia") == []


def test_xianxia_colloquial_pattern_does_not_flag_classical_homonyms():
    text = (
        "Phong thái thanh tao, nét mày ngài thanh tú; "
        "hắn vẫn mày mò cổ trận giữa đêm."
    )
    assert scan(text, "xianxia") == []


def test_xianxia_allows_period_appropriate_lunar_calendar_terms():
    assert scan(
        "Ngày rằm, dân làng dâng hương trước cổ miếu dưới ánh trăng.",
        "xianxia",
    ) == []


def test_xianxia_blocks_contemporary_slang_and_external_reference():
    text = "Cơ mà cách này độc đáo vãi, đúng là Chí Phèo. Đệt."
    flagged = _flagged_terms(text, "xianxia")
    assert {"cơ mà", "vãi", "chí phèo", "đệt"} <= flagged


def test_xianxia_does_not_ban_ambiguous_hai_tieng_by_itself():
    assert scan("Ngoài sơn môn vang lên hai tiếng chuông.", "xianxia") == []


def test_acronyms_do_not_fire_inside_words():
    """Short upper-case acronyms (MC) match case-sensitively, not inside words."""
    # 'mc' lowercase inside an ordinary word must not trip the 'MC' ban.
    assert "mc" not in _flagged_terms("Cơm canh đạm bạc, mcdonald không tồn tại.", "xianxia")


# --------------------------------------------------------------------------- #
# Task 7.3 — hybrid: whitelist = primary ∪ secondary
# --------------------------------------------------------------------------- #


def test_hybrid_allows_secondary_genre_vocabulary():
    """Urban+Xianxia hybrid: cultivation terms are allowed (Req 12.2/17)."""
    text = "Hắn bắt đầu tu luyện linh khí để đột phá cảnh giới."
    assert _flagged_terms(text, "urban"), "urban alone should flag cultivation"
    assert _flagged_terms(text, "urban", "xianxia") == set(), (
        "urban+xianxia hybrid should allow cultivation vocabulary"
    )


def test_hybrid_still_blocks_terms_outside_both_whitelists():
    """Requirement 12.2: tokens outside both whitelists are still flagged."""
    text = "Hắn tu luyện linh khí nhưng vẫn mở debug và xem metadata."
    flagged = _flagged_terms(text, "urban", "xianxia")
    # cultivation allowed by xianxia, operational still blocked
    assert "tu luyện" not in flagged
    assert {"debug", "metadata"} <= flagged


def test_secondary_genre_only_adds_whitelist_not_bans():
    """Requirement 12.3: secondary only *adds* whitelist; its bans do not apply.

    'app' is banned by time_travel but not by xianxia. With xianxia primary and
    time_travel secondary, 'app' must NOT be flagged (secondary bans ignored),
    while operational terms are still caught.
    """
    text = "Trên ngọn núi nọ, một app kỳ lạ xuất hiện cùng metadata."
    flagged = _flagged_terms(text, "xianxia", "time_travel")
    assert "app" not in flagged
    assert "metadata" in flagged


# --------------------------------------------------------------------------- #
# P6 — Language guard soundness (headline property)
# --------------------------------------------------------------------------- #


@settings(max_examples=400)
@given(
    data=st.data(),
    genre=st.sampled_from(_GENRES),
    secondary=st.sampled_from([None, *_GENRES]),
)
def test_property_language_guard_soundness(data, genre, secondary):
    """P6: token outside whitelist(primary∪secondary) flagged; token in it not.

    **Validates: Requirements 12.1**
    """
    candidates = _candidate_terms(genre)
    term = data.draw(st.sampled_from(candidates))

    primary_profile = load_profile(genre)
    whitelist = set(primary_profile.whitelist)
    if secondary:
        whitelist |= set(load_profile(secondary).whitelist)

    text = _embed(term)
    flagged = _flagged_terms(text, genre, secondary)
    key = term.casefold()

    if key in whitelist:
        # Whitelist wins (hybrid case): never flagged.
        assert key not in flagged, f"{term!r} whitelisted but flagged"
    else:
        # Operational / out-of-genre token: always flagged.
        assert key in flagged, f"{term!r} not whitelisted but not flagged"


@settings(max_examples=200)
@given(genre=st.sampled_from(_GENRES))
def test_property_whitelisted_terms_never_flagged(genre):
    """Any term in a genre's own whitelist is never flagged for that genre.

    **Validates: Requirements 12.1**
    """
    profile = load_profile(genre)
    if not profile.whitelist:
        return
    for term in profile.whitelist:
        flagged = _flagged_terms(_embed(term), genre)
        assert term.casefold() not in flagged, f"{term!r} whitelisted yet flagged"


@settings(max_examples=200)
@given(genre=st.sampled_from(_GENRES))
def test_property_clean_prose_never_false_positive(genre):
    """Prose built only from clean filler never produces a violation.

    **Validates: Requirements 12.1**
    """
    assert scan(_CLEAN_PROSE, genre) == []


# --------------------------------------------------------------------------- #
# Tool entrypoint + registry
# --------------------------------------------------------------------------- #


def test_scan_result_summary_shape():
    res = scan_result("Mở debug để xem runtime.", "xianxia")
    assert res["severity"] == "error"
    assert res["passed"] is False
    assert res["total_hits"] >= 2
    assert {v["term"] for v in res["violations"]} >= {"debug", "runtime"}


def test_scan_result_clean_passes():
    res = scan_result(_CLEAN_PROSE, "urban")
    assert res["passed"] is True
    assert res["severity"] == "ok"
    assert res["violations"] == []


def test_violation_count_reflects_occurrences():
    text = "debug rồi lại debug, sau đó debug lần nữa."
    violations = scan(text, "xianxia")
    debug = next(v for v in violations if v.term == "debug")
    assert debug.count == 3
    assert debug.severity == "error"
    assert debug.source == "operational"


def test_empty_text_returns_no_violations():
    assert scan("", "xianxia") == []
    assert scan(None, "xianxia") == []  # type: ignore[arg-type]


def test_tool_is_self_registered():
    entry = registry.get("novelkit_language_guard")
    assert entry.fn is language_guard_tool
    assert entry.module == "tools.novelkit_language_guard_tool"
    assert "novelkit_language_guard" in registry.list_tools()


def test_tool_entrypoint_matches_scan_result():
    out = language_guard_tool("Mở debug.", "xianxia")
    assert out == scan_result("Mở debug.", "xianxia")


def test_unknown_genre_falls_back_to_operational_only():
    """A genre with no profile still catches universal operational language."""
    flagged = _flagged_terms("Một chương có metadata và pipeline.", "nonexistent_genre")
    assert {"metadata", "pipeline"} <= flagged
