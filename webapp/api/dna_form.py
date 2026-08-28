"""PROJECT_DNA form schema + renderer.

The creation flow is template-driven: the UI renders a form from :data:`SCHEMA`
(which mirrors ``templates/PROJECT_DNA_FILLABLE.md`` field-for-field), the user
fills it, and :func:`render_project_dna` writes those values back into the
genre-specific template under ``templates/genres/`` (single genre) or the
unified ``PROJECT_DNA_TEMPLATE.md`` layout (hybrid). Only after that does
bootstrapping/initialisation run.

``sub_agents_squad`` / ``canon_pack`` / ``genre_primary`` are derived from the
chosen genre via the squad map, so the author never has to know them.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from . import dna_genre_render
from .dna_genre_fields import EXTENDED_CANON_GENRES, GENRE_ENRICH_KEYS, GENRE_SECTIONS

_LOG = logging.getLogger(__name__)

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_SQUAD_MAP_PATH = _PACKAGE_ROOT / "subagents" / "squad_map.json"

GENRES = ["xianxia", "urban", "romance", "scifi", "time_travel", "meta_genre"]

#: The single last-resort genre. Previously eleven call sites each wrote their
#: own ``_g(fields, "genre", "xianxia") or "xianxia"``, so a novel with a missing
#: or unrecognised genre was silently processed as Xianxia — a sci-fi novel could
#: be drafted against the cultivation canon with no error anywhere. All of them
#: now go through :func:`resolve_genre`, which logs before falling back.
DEFAULT_GENRE = "xianxia"

# Genre dropdown with Vietnamese + English display labels (mirrors squad_map).
GENRE_OPTIONS = [
    {"value": "xianxia", "label": "Tiên Hiệp / Xianxia"},
    {"value": "urban", "label": "Đô Thị / Urban"},
    {"value": "romance", "label": "Ngôn Tình / Romance"},
    {"value": "scifi", "label": "Khoa Huyễn / Sci-fi"},
    {"value": "time_travel", "label": "Xuyên Không / Time Travel"},
    {"value": "meta_genre", "label": "Hệ Thống / Meta Genre"},
]

# Author "Đại Thần" style codes per genre (from canon system/<pack>/Author Style/).
# Used for both `style_model` and `worldbuilding_guide` dropdowns.
STYLE_BY_GENRE: dict[str, list[dict[str, str]]] = {
    "xianxia": [
        {"value": "NC", "label": "NC — Nhĩ Căn"},
        {"value": "TD", "label": "TD — Tiêu Đỉnh"},
        {"value": "CD", "label": "CD — Thần Đông"},
        {"value": "DG", "label": "DG — Đường Gia Tam Thiếu"},
        {"value": "OT", "label": "OT — Mực Thích Lặn Nước"},
        {"value": "PL", "label": "PL — Phong Lăng Thiên Hạ"},
        {"value": "PT", "label": "PT — Phương Tưởng"},
        {"value": "TH", "label": "TH — Ngã Cật Tây Hồng Thị"},
        {"value": "TT", "label": "TT — Thiên Tằm Thổ Đậu"},
        {"value": "VN", "label": "VN — Vong Ngữ"},
    ],
    "urban": [
        {"value": "KV", "label": "KV — Khiêu Vũ"},
        {"value": "LHH", "label": "LHH — Liễu Hạ Huệ"},
        {"value": "LUAG", "label": "LUAG — Lão Ưng Ăn Gà"},
        {"value": "NNND", "label": "NNND — Ngư Nhân Nhị Đại"},
        {"value": "PHHCH", "label": "PHHCH — Phong Hỏa Hí Chư Hầu"},
    ],
    "romance": [
        {"value": "CM", "label": "CM — Cố Mạn"},
        {"value": "DH", "label": "DH — Đồng Hoa"},
        {"value": "DM", "label": "DM — Đinh Mặc"},
        {"value": "PNTT", "label": "PNTT — Phỉ Ngã Tư Tồn"},
        {"value": "TDO", "label": "TDO — Tân Dĩ Ổ"},
    ],
    "scifi": [
        {"value": "LTH", "label": "LTH — Lưu Từ Hân"},
        {"value": "THCM", "label": "THCM — Thải Hồng Chi Môn"},
        {"value": "TNT", "label": "TNT — Thập Niên Thất"},
        {"value": "TTNB", "label": "TTNB — Thất Thập Nhị Biến"},
        {"value": "VT", "label": "VT — Viễn Đồng"},
    ],
    "time_travel": [
        {"value": "AV", "label": "AV — A Việt"},
        {"value": "BD", "label": "BD — Bùi Đồ Cẩu"},
        {"value": "HT", "label": "HT — Phẫn Nộ Hương Tiêu"},
        {"value": "LU", "label": "LU — Lão Ưng Cật Tiểu Kê"},
        {"value": "MB", "label": "MB — Mại Báo Tiểu Lang Quân"},
        {"value": "MN", "label": "MN — Mão Nị"},
        {"value": "NQ", "label": "NQ — Nguyệt Quan"},
        {"value": "TG", "label": "TG — Tam Giới Đại Sư"},
        {"value": "TT", "label": "TT — Trửu Tử"},
        {"value": "ZT", "label": "ZT — Zhttty / Trương Hằng"},
    ],
    "meta_genre": [
        {"value": "GHTK", "label": "GHTK — Giang Hồ Tái Kiến"},
        {"value": "MHTK", "label": "MHTK — Mặc Hương Đồng Khứu"},
        {"value": "MV", "label": "MV — Mặc Vũ"},
        {"value": "TP", "label": "TP — Tân Phong"},
        {"value": "TST", "label": "TST — Thanh Sam Thủ"},
    ],
}

CULTIVATION_SPEED_OPTIONS = [
    {"value": "", "label": "— Chọn —"},
    {"value": "fast", "label": "Nhanh (fast)"},
    {"value": "slow", "label": "Chậm (slow)"},
    {"value": "ultra_slow", "label": "Cực chậm (ultra_slow)"},
]

HYBRID_RATIO_OPTIONS = [
    {"value": "", "label": "— Không pha trộn —"},
    {"value": "80-20", "label": "80-20"},
    {"value": "70-30", "label": "70-30"},
    {"value": "60-40", "label": "60-40"},
    {"value": "50-50", "label": "50-50"},
]

# Prose / PROJECT_DNA output language (distinct from Studio UI locale).
OUTPUT_LANGUAGE_OPTIONS = [
    {"value": "vi", "label": "Tiếng Việt"},
    {"value": "en", "label": "English"},
    {"value": "ko", "label": "한국어 (Korean)"},
    {"value": "ja", "label": "日本語 (Japanese)"},
    {"value": "zh", "label": "中文 (Chinese)"},
    {"value": "pt", "label": "Português"},
    {"value": "fr", "label": "Français"},
    {"value": "custom", "label": "Tùy chỉnh…"},
]

OUTPUT_LANGUAGE_CODES = {o["value"] for o in OUTPUT_LANGUAGE_OPTIONS}

TONE_OPTIONS = [
    {"value": "", "label": "— Chọn / tự nhập —"},
    {"value": "bi tráng", "label": "Bi tráng"},
    {"value": "lạnh lý tính", "label": "Lạnh lý tính"},
    {"value": "sảng nhanh", "label": "Sảng nhanh"},
    {"value": "ngược tâm", "label": "Ngược tâm"},
    {"value": "hài lầy", "label": "Hài lầy"},
    {"value": "ấm áp chữa lành", "label": "Ấm áp / chữa lành"},
]

# Canon folder name per genre slug (for canon_pack + worldbuilding hints).
# Covers every canon pack under skills/novelkit-canon/canon/system/ — not just
# the 6 genres with a bespoke PROJECT_DNA template — so a novel in any genre
# resolves to its real folder (correct case/spacing) instead of falling back to
# the raw slug (which would miss the disk folder entirely).
_CANON_PACK = {
    "xianxia": "Xianxia",
    "urban": "Urban",
    "romance": "Romance",
    "scifi": "Sci-fi",
    "time_travel": "Time Travel",
    "meta_genre": "Meta Genre",
    "apocalypse": "Apocalypse",
    "cthulhu": "Cthulhu",
    "dark_theme": "Dark Theme",
    "many_children": "Many Children",
    "rules_horror": "Rules Horror",
    "short_form": "Short Form",
    "streaming": "Streaming",
    "substitute": "Substitute",
    "war_espionage": "War Espionage",
    "esports": "eSports",
}


def _slug(value: str) -> str:
    norm = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", norm.lower()).strip()


def _genre_to_squad() -> dict[str, str]:
    try:
        return json.loads(_SQUAD_MAP_PATH.read_text(encoding="utf-8"))["genre_to_squad"]
    except (OSError, json.JSONDecodeError, KeyError):
        return {}


def derive_squad(genre: str) -> str:
    """Map a genre to its specialist squad family (defaults to xianxia squad)."""
    key = _slug(genre)
    # Normalise the form's compact slugs to the squad_map's spaced aliases.
    key = {"scifi": "sci fi", "metagenre": "meta genre"}.get(key, key)
    return _genre_to_squad().get(key, "sub_agents")


def canon_pack(genre: str) -> str:
    return _CANON_PACK.get(_slug(genre).replace(" ", "_"), genre)


#: Slug aliases so a genre value spelled differently still resolves to the
#: canonical GENRES slug (the form emits select values, but a model or legacy
#: sidecar may use a spaced/variant form).
_GENRE_SLUG_ALIAS = {
    "sci_fi": "scifi",
    "scifi": "scifi",
    "metagenre": "meta_genre",
    "meta_genre": "meta_genre",
    "timetravel": "time_travel",
    "time_travel": "time_travel",
}


def _canonical_genre_slug(value: str) -> str:
    """Resolve a genre value to a canonical GENRES slug, or "" if unknown."""
    v = (value or "").strip()
    if not v:
        return ""
    if v in GENRES:
        return v
    slug = _slug(v).replace(" ", "_")
    slug = _GENRE_SLUG_ALIAS.get(slug, slug)
    return slug if slug in GENRES else ""


def resolve_genre(
    fields: dict[str, Any], *, where: str = "", strict: bool = False
) -> str:
    """Resolve a field map's primary genre, logging when it has to be guessed.

    Eleven call sites used to inline ``_g(fields, "genre", "xianxia") or
    "xianxia"``. Each independently decided that an absent or unrecognised genre
    means xianxia, so a sci-fi novel that lost its ``genre`` key was silently
    processed against the xianxia canon at any of those eleven points — no error,
    no log, and the mismatch only surfaced as wrong prose much later.

    Resolution now happens once, prefers ``genre_primary`` over the bare
    ``genre`` routing marker (which reads ``hybrid`` for blends), accepts the
    known aliases, and *records* every fallback so the guess is visible in the
    logs instead of invisible in the output. ``where`` names the call site.

    With ``strict=True`` an unresolvable genre raises :class:`ValueError` instead
    of falling back — for callers that select a genre-specific asset, where a
    wrong guess would silently render the wrong template.
    """
    for key in ("genre_primary", "genre"):
        canon = _canonical_genre_slug(_g(fields, key))
        if canon:
            return canon
    raw = _g(fields, "genre_primary") or _g(fields, "genre")
    if strict:
        raise ValueError(
            f"unresolvable genre {raw!r}"
            + (f" in {where}" if where else "")
        )
    _LOG.warning(
        "genre could not be resolved%s (raw=%r) — falling back to %s; "
        "the novel will be processed against the %s canon",
        f" in {where}" if where else "", raw, DEFAULT_GENRE, DEFAULT_GENRE,
    )
    return DEFAULT_GENRE


def normalize_secondary_genre(fields: dict[str, Any]) -> bool:
    """Coerce ``genre_secondary`` to a single valid genre slug, in place.

    Quick Setup sometimes lets the model return a multi-valued or free-form
    secondary genre (e.g. ``"romance, meta_genre"``). That corrupts every hybrid
    routing derivative — ``canon_pack_secondary`` becomes ``system/romance,
    meta_genre``, ``sub_agents_squad_secondary`` falls back to the default squad
    — and permanently wedges both the enrich loop (``style_secondary`` can never
    be defaulted for an unknown secondary genre, so it stays the "1 field
    remaining") and the style pre-flight (which requires a secondary style once a
    secondary genre is set). A real hybrid is always a single clean slug picked
    from the form dropdown, so any value that is not exactly one known genre —
    multi-valued, unknown, or equal to the primary — is cleared back to
    single-genre. Returns True when it changed anything.
    """
    raw = _g(fields, "genre_secondary")
    if not raw:
        return False
    parts = [p for p in re.split(r"[,/;]+", raw) if p.strip()]
    canon = _canonical_genre_slug(parts[0]) if len(parts) == 1 else ""
    primary = resolve_genre(fields, where="normalize_secondary_genre")
    if canon and canon != primary:
        if canon == raw:
            return False
        fields["genre_secondary"] = canon
        return True
    # Multi-valued, unknown, or same as the primary → not a valid hybrid.
    fields["genre_secondary"] = ""
    fields["style_secondary"] = ""
    return True


# --------------------------------------------------------------------------- #
# Form schema — sections + fields (mirrors PROJECT_DNA_FILLABLE.md).
# Each field: id, label, type (text|textarea|number|select), required, help,
# options (for select), placeholder, default.
# --------------------------------------------------------------------------- #

SCHEMA: list[dict[str, Any]] = [
    {
        "section": "Hạt giống",
        "fields": [
            {"id": "title", "label": "Tên tác phẩm", "type": "text", "required": True},
            {"id": "genre", "label": "Thể loại chính", "type": "select",
             "required": True, "options": GENRE_OPTIONS, "default": "xianxia"},
            {"id": "genre_secondary", "label": "Thể loại phụ (hybrid)", "type": "select",
             "options": [{"value": "", "label": "— Không —"}, *GENRE_OPTIONS]},
            {"id": "hybrid_ratio", "label": "Tỉ lệ hybrid", "type": "select",
             "options": HYBRID_RATIO_OPTIONS},
            {"id": "logline", "label": "Logline (1 câu)", "type": "textarea",
             "required": True, "placeholder": "Một câu pitch toàn truyện…"},
            {"id": "usp", "label": "Dấu riêng (USP)", "type": "textarea"},
            {"id": "theme", "label": "Chủ đề cốt lõi", "type": "textarea"},
            {"id": "audience", "label": "Đối tượng độc giả", "type": "textarea"},
            {"id": "output_language", "label": "Ngôn ngữ output (văn chương)",
             "type": "select", "options_source": "output_languages",
             "default": "vi",
             "help": "Ngôn ngữ Prose Writer và nội dung PROJECT_DNA ghi vào novel."},
            {"id": "output_language_custom", "label": "Ngôn ngữ tùy chỉnh",
             "type": "text", "placeholder": "vd: Deutsch, Español, Tiếng Thái…"},
        ],
    },
    {
        "section": "Phong cách & giọng văn",
        "fields": [
            {"id": "tone", "label": "Khí sắc chủ đạo", "type": "select",
             "options": TONE_OPTIONS},
            {"id": "style_model", "label": "Mã Đại Thần (style_model)",
             "type": "select", "options_source": "genre_styles",
             "help": "Danh sách Đại Thần đổi theo thể loại chính."},
            {"id": "style_secondary", "label": "Mã phụ (nếu pha trộn)",
             "type": "select", "options_source": "genre_styles"},
            {"id": "worldbuilding_guide", "label": "Đạo thư dựng giới",
             "type": "select", "options_source": "genre_styles"},
        ],
    },
    {
        "section": "Nhân vật chính",
        "fields": [
            {"id": "mc_name", "label": "Tên", "type": "text"},
            {"id": "mc_archetype", "label": "Cốt cách", "type": "textarea"},
            {"id": "mc_traits", "label": "Đặc điểm nổi bật", "type": "textarea"},
            {"id": "mc_motivation", "label": "Động cơ khởi đầu", "type": "textarea"},
            {"id": "mc_want", "label": "Mong cầu bề mặt (Want)", "type": "textarea"},
            {"id": "mc_need", "label": "Thiếu khuyết nội tâm (Need)", "type": "textarea"},
            {"id": "mc_ghost", "label": "Vết thương cũ (Ghost)", "type": "textarea"},
        ],
    },
    {
        "section": "Đối trọng / Phản diện",
        "fields": [
            {"id": "antagonist_name", "label": "Tên", "type": "text"},
            {"id": "antagonist_traits", "label": "Đặc điểm", "type": "textarea"},
            {"id": "antagonist_conflict", "label": "Xung đột cốt lõi với MC", "type": "textarea"},
        ],
    },
    {
        "section": "Thế câu dẫn độc giả",
        "fields": [
            {"id": "hook_strategy", "label": "Thế câu dẫn", "type": "textarea"},
        ],
    },
    {
        "section": "Thế giới & tu luyện",
        "fields": [
            {"id": "cultivation_speed", "label": "Tốc độ tu luyện", "type": "select",
             "options": CULTIVATION_SPEED_OPTIONS, "genres": ["xianxia"]},
            {"id": "cultivation_age_benchmarks", "label": "Mốc tuổi tu luyện", "type": "textarea",
             "genres": ["xianxia"]},
        ],
    },
    {
        "section": "Đồng hành đặc biệt",
        "fields": [
            {"id": "artifact", "label": "Pháp bảo", "type": "textarea", "genres": ["xianxia"]},
            {"id": "spirit_beast", "label": "Linh Thú", "type": "textarea", "genres": ["xianxia"]},
            {"id": "supporting_cast", "label": "Dàn nhân vật phụ", "type": "textarea"},
        ],
    },
    {
        "section": "Thông số",
        "fields": [
            {"id": "target_chapters", "label": "Số chương", "type": "number",
             "required": True, "default": 30},
            {"id": "arc_count", "label": "Số đại hồi", "type": "number"},
            {"id": "target_words_per_chapter", "label": "Số từ mỗi chương",
             "type": "number", "default": 2500},
        ],
    },
]


def schema() -> dict[str, Any]:
    """Return the form schema + genre→squad map for the UI."""
    return {
        "sections": SCHEMA,
        "genre_sections": GENRE_SECTIONS,
        "extended_canon_genres": EXTENDED_CANON_GENRES,
        "genres": GENRES,
        "genre_options": GENRE_OPTIONS,
        "genre_to_squad": _genre_to_squad(),
        "genre_styles": STYLE_BY_GENRE,
        "output_language_options": OUTPUT_LANGUAGE_OPTIONS,
        "genre_template_files": {
            g: dna_genre_render.genre_template_relpath(g) for g in GENRES
        },
    }


# --------------------------------------------------------------------------- #
# Fields completed by the enrich action: blank optional Full Setup fields plus
# the deep PROJECT_DNA content for sections IV-XIV. Quick Setup normally fills
# the form fields first; enrichment requests only values that are still absent.
# --------------------------------------------------------------------------- #

ENRICH_KEYS: tuple[tuple[str, str], ...] = (
    ("logline_test", "Logline TEST (Nhân vật phải … trước khi … nhưng …)"),
    # Optional form fields — Quick Setup normally fills these in its first call,
    # while Full Setup may leave them blank for the enrich action to complete.
    ("usp", "Dấu riêng (USP)"),
    ("theme", "Chủ đề cốt lõi"),
    ("audience", "Đối tượng độc giả"),
    ("tone", "Khí sắc chủ đạo"),
    # NOTE: ``style_model`` / ``style_secondary`` / ``worldbuilding_guide`` are
    # deliberately NOT enrichable. They are user-facing routing choices and must
    # remain stable rather than being guessed by the model. Author profiles are
    # informational metadata; worldbuilding selection still routes its guide.
    ("mc_name", "Tên nhân vật chính"),
    ("mc_archetype", "Cốt cách nhân vật chính"),
    ("mc_traits", "Đặc điểm nổi bật của nhân vật chính"),
    ("mc_motivation", "Động cơ khởi đầu của nhân vật chính"),
    ("mc_want", "Mong cầu bề mặt (Want)"),
    ("mc_need", "Thiếu khuyết nội tâm (Need), phải khác Want"),
    ("mc_ghost", "Vết thương cũ (Ghost)"),
    ("antagonist_name", "Tên / danh xưng phản diện cuối"),
    ("antagonist_traits", "Đặc điểm phản diện"),
    ("antagonist_conflict", "Xung đột cốt lõi của phản diện với MC"),
    ("hook_strategy", "Thế câu dẫn độc giả"),
    ("cultivation_speed", "Tốc độ tu luyện"),
    ("cultivation_age_benchmarks", "Mốc tuổi tu luyện"),
    ("artifact", "Pháp bảo / lợi thế đặc biệt"),
    ("spirit_beast", "Linh thú hoặc ghi rõ không áp dụng"),
    ("supporting_cast", "Ít nhất 3 nhân vật phụ có giọng riêng"),
    ("arc_count", "Số đại hồi dự kiến (chỉ trả về số)"),
    # World (IV)
    ("world_name", "Tên thế giới / Bối cảnh"),
    ("world_era", "Thời đại"),
    ("world_mindset", "Tư duy / Quy luật trung tâm thế giới"),
    ("world_secret", "Bí mật lịch sử / Lời nguyền nền"),
    ("world_locations", "3-5 địa điểm quan trọng"),
    # Power system (V)
    ("system_name", "Tên hệ thống sức mạnh / cơ chế"),
    ("system_tiers", "Các cấp bậc / giai tầng (thấp→cao)"),
    ("system_cost", "Cái giá đột phá / hạn chế sức mạnh"),
    ("system_resource", "Tài nguyên cốt lõi"),
    ("system_bottleneck", "Nút thắt chính tạo kịch tính"),
    ("system_golden_finger", "Kim Thủ Chỉ (lợi thế của MC)"),
    ("system_golden_finger_limit", "Giới hạn của Kim Thủ Chỉ"),
    # MC depth (VI)
    ("mc_lie", "Niềm tin sai (Lie) cần thay đổi"),
    ("mc_voice", "Giọng riêng của MC (cách nói, từ vựng)"),
    # Cast (VII)
    ("cast_love_interest", "Tình yêu / đối tác chính + rào cản"),
    ("cast_mentor", "Sư phụ / Mentor + bí mật giấu"),
    ("cast_allies", "2-3 huynh đệ / đồng đội (mỗi người 1 câu)"),
    ("cast_relationship_matrix", "Lưới quan hệ (2-4 dòng: MC↔nhân vật)"),
    # Villain depth (VIII)
    ("villain_want", "Mong cầu của phản diện (hợp lý)"),
    ("villain_human_moment", "Khoảnh khắc 'người' của phản diện"),
    ("villain_justified", "Vì sao phản diện ĐÚNG từ góc nhìn của hắn"),
    # Plot structure (IX)
    ("inciting_incident", "Sự kiện khởi phát"),
    ("midpoint_twist", "Cú lật giữa truyện (điều MC tin → sai)"),
    ("all_is_lost", "Khoảnh khắc đáy vực của MC"),
    ("climax", "Tầm nhìn đại cao trào"),
    ("ending_style", "Kiểu kết thúc (HE/BE/Open/Bittersweet)"),
    # Voice & taboo (X) + Creative Premise Contract
    ("sensory_palette", "Bảng giác quan ưu tiên (thị/thính/xúc…)"),
    ("core_wound", "Core Wound — vết thương lõi của MC"),
    ("irreversible_choice", "Irreversible Choice — lựa chọn không quay đầu"),
    ("moral_contradiction", "Moral Contradiction — mâu thuẫn đạo đức"),
    ("world_pressure", "World Pressure — sức ép thế giới ép lựa chọn"),
    ("motif_execution_angle", "Motif Execution Angle — góc thi triển motif"),
    ("reader_addiction_loop", "Reader Addiction Loop — vòng kéo độc giả"),
    ("scene_promise", "Scene Promise — lời hứa mỗi chương"),
    ("scene_vitality_contract", "Scene Vitality Contract — khế ước cảnh sống"),
    # Pacing & reader pull (XI)
    ("hook_mix", "Dàn thế câu dẫn (mix các loại hook)"),
    ("minor_payoff_cadence", "Nhịp tiểu sảng"),
    ("major_payoff_cadence", "Nhịp đại sảng"),
    ("strand_weave_targets", "Mục tiêu đan tuyến"),
    ("water_vs_burst_ratio", "Tỉ lệ chương tích lũy vs chương bùng nổ"),
    ("micro_payoff_per_chapter", "Mỗi chương phải trả (micro-payoff)"),
    # Seed master & thread registry (XII)
    ("seed_master", "Sổ phục bút (3 seed: cài tại / thu tại / mô tả)"),
    ("thread_registry", "Sổ tuyến truyện (Quest/Fire/Constellation)"),
    # Arc boss ladder (XIII)
    ("arc_boss_ladder", "Bậc thang trùm theo đại hồi (Arc 1-3)"),
    ("mini_bosses", "2-3 tiểu chướng / chướng ngại"),
    # DNA execution contract (XIV)
    ("mc_archetype_execution", "Cách thi triển cốt cách MC trong cảnh"),
    ("hook_strategy_execution", "Cách vận dụng thế câu dẫn trong cảnh"),
    ("style_execution", "Cách thi triển giọng dự án"),
    ("worldbuilding_execution", "Cách lộ luật thiên địa qua hành động"),
    ("world_frame_execution", "Cách bối cảnh ép lựa chọn"),
) + GENRE_ENRICH_KEYS


# --------------------------------------------------------------------------- #
# Quick Setup — let the LLM fill the whole template from a short brief.
# --------------------------------------------------------------------------- #

#: Style/routing fields that select WHICH canon the pipeline loads. They are not
#: creative content: ``style_model`` picks the Author Style profile that becomes
#: the top voice authority in the system prompt, and ``worldbuilding_guide``
#: picks the world canon. A model-invented value here silently rewrites the
#: novel's whole voice contract, so these are decided by the author's form
#: selection or by :func:`apply_style_defaults` — never by an LLM answer.
#: Excluded from BOTH generation (``_GEN_SKIP``) and enrichment
#: (``ENRICH_KEYS``); keep the two derived from this one set so they cannot drift.
STYLE_ROUTING_KEYS: frozenset[str] = frozenset(
    {"style_model", "style_secondary", "worldbuilding_guide"}
)

#: Fields the LLM should NOT invent in Quick Setup. These are user routing
#: choices (picked in the create form) or deterministic values — never creative
#: content. Letting the model invent them caused two production bugs:
#:   * ``genre_secondary`` fabricated as a multi-value ("romance, meta_genre")
#:     corrupted every hybrid derivative and wedged the enrich/style pre-flight;
#:   * ``style_model`` / ``worldbuilding_guide`` invented by the model overrode
#:     the author's explicit dropdown selection (user picks NC, DNA shows PT).
#: The author's form selection is authoritative for all of these.
_GEN_SKIP = {
    "target_chapters", "target_words_per_chapter", "arc_count",
    "output_language", "output_language_custom",
    "genre_secondary", "hybrid_ratio",
} | set(STYLE_ROUTING_KEYS)


def prose_contract_instruction(genre: str, style_model: str = "") -> str:
    """Return the standing prose contract used by DNA generation/enrichment.

    Author-style codes remain stable routing metadata but no longer contribute
    prose rules. The genre-level register sentences come from
    ``config/language_guard/<genre>.json``, which is the SAME source the drafting
    loop reads.
    """
    rules = [
        "Mã Author Style chỉ dùng để nhận diện lựa chọn; không suy luận hoặc mô "
        "phỏng văn phong từ tên, mã hay kiến thức bên ngoài về tác giả."
    ]
    try:
        from tools.novelkit_language_guard_tool import load_profile

        rules.extend(load_profile(genre).register_contract())
    except Exception:  # noqa: BLE001 — a missing profile must not block creation
        _LOG.warning("could not load register contract for genre %r", genre)
    return " ".join(rules)


def generation_prompt(
    brief: str,
    genre: str,
    title: str = "",
    *,
    output_language: str = "vi",
    output_language_custom: str = "",
) -> tuple[str, str]:
    """Build (system, user) prompts asking the model to fill the DNA fields.

    The model must return a single JSON object keyed by schema field id. We list
    every fillable field with its label + allowed options so the output is
    directly usable by :func:`render_project_dna`.
    """
    genre = genre if genre in GENRES else "xianxia"
    style_codes = ", ".join(o["value"] for o in STYLE_BY_GENRE.get(genre, []))
    lang_fields = {
        "output_language": output_language,
        "output_language_custom": output_language_custom,
    }
    lang_label = resolve_output_language_label(lang_fields)
    lang_rule = output_language_instruction(lang_fields)

    lines: list[str] = []
    seen: set[str] = set()

    def _append_field(f: dict[str, Any]) -> None:
        fid = f["id"]
        if fid in _GEN_SKIP or fid == "genre" or fid in seen:
            return
        allowed = f.get("genres")
        if allowed and genre not in allowed:
            return
        seen.add(fid)
        hint = ""
        if f.get("options_source") == "genre_styles":
            hint = f" (chọn 1 mã trong: {style_codes})"
        elif f.get("options"):
            opts = ", ".join(o["value"] for o in f["options"] if o["value"])
            if opts:
                hint = f" (gợi ý: {opts})"
        lines.append(f'- "{fid}": {f["label"]}{hint}')

    for section in SCHEMA:
        for f in section["fields"]:
            _append_field(f)
    for gsec in GENRE_SECTIONS.get(genre, []):
        for f in gsec["fields"]:
            _append_field(f)

    field_list = "\n".join(lines)
    prose_contract = prose_contract_instruction(genre)
    system = (
        "Bạn là biên kịch trưởng cho tiểu thuyết mạng đa thể loại. Từ một ý tưởng "
        "ngắn, bạn dựng bộ ADN sáng tác (PROJECT_DNA) đầy đủ, nhất quán, hấp dẫn. "
        f"{lang_rule} {prose_contract} "
        "CHỈ trả về một đối tượng JSON hợp lệ, không kèm giải thích, không markdown."
    )
    user = (
        f"Ý TƯỞNG/YÊU CẦU CỦA TÁC GIẢ:\n{brief.strip()}\n\n"
        f"Thể loại chính: {genre}\n"
        f"Ngôn ngữ output bắt buộc: {lang_label}\n"
        + (f"Tên tác phẩm (gợi ý): {title.strip()}\n" if title.strip() else "")
        + f"\nHãy điền nội dung bằng {lang_label} cho các trường sau (JSON, key đúng như id, "
        "giá trị là chuỗi; trường mã phong cách phải chọn đúng 1 mã hợp lệ; có thể "
        "để chuỗi rỗng nếu thực sự không hợp):\n"
        f"{field_list}\n\n"
        'Định dạng: {"title": "...", "logline": "...", ...}. Chỉ JSON.'
    )
    return system, user


# Batches of enrichment keys — kept small so each LLM call fits comfortably
# within the provider gateway's timeout (a single 75-field call 502s upstream).
def enrich_batches() -> list[list[tuple[str, str]]]:
    return enrich_batches_for([k for k, _ in ENRICH_KEYS])


def enrich_ids_for_genre(genre: str) -> list[str]:
    """Enrich field ids that are actually relevant to ``genre``.

    ``ENRICH_KEYS`` pools every genre's craft fields (it ends with
    ``+ GENRE_ENRICH_KEYS``, which carries romance/urban/scifi/time-travel/meta
    fields). A field that belongs to a *different* genre's section — or a base
    SCHEMA field gated to other genres (``cultivation_speed``, ``artifact``,
    ``spirit_beast`` …) — can never be filled for this novel and never renders
    in its PROJECT_DNA.md. Counting those toward "missing" makes ``enrich`` never
    reach ``done``: the client's ``enrichDnaAll`` loop then stalls and stops
    early, leaving genuine core fields (world/system/cast/premise) stuck on the
    ``_(tự sinh)_`` placeholder. Filtering to the novel's own genre lets enrich
    actually complete.
    """
    from .dna_genre_fields import GENRE_ENRICH_KEYS, GENRE_SECTIONS

    genre = genre if genre in GENRES else "xianxia"
    # Genre-only enrich fields (belong to some genre's extension section).
    genre_only_ids = {k for k, _ in GENRE_ENRICH_KEYS}
    this_genre_ids = {
        f["id"] for sec in GENRE_SECTIONS.get(genre, []) for f in sec["fields"]
    }
    # Base SCHEMA fields explicitly gated to specific genres.
    schema_gated: dict[str, set[str]] = {
        f["id"]: set(f["genres"])
        for sec in SCHEMA
        for f in sec["fields"]
        if f.get("genres")
    }

    out: list[str] = []
    for key, _ in ENRICH_KEYS:
        if key in genre_only_ids and key not in this_genre_ids:
            continue  # genre-only field belonging to another genre
        allowed = schema_gated.get(key)
        if allowed and genre not in allowed:
            continue  # base field gated to other genres
        out.append(key)
    return out


def genre_section_field_ids(genre: str) -> set[str]:
    """Field ids that live in this genre's own extension section.

    For xianxia these are ``mc_spirit_root`` / ``mc_starting_realm`` /
    ``mc_age_foundation`` / ``main_cultivation_method`` — optional craft detail
    the author can pick from the template's inline option hints (e.g. Linh căn:
    Đơn / Song / Tạp …). They render in the genre template but are secondary,
    not core spine like world/system/premise.
    """
    from .dna_genre_fields import GENRE_SECTIONS

    genre = genre if genre in GENRES else "xianxia"
    return {
        f["id"] for sec in GENRE_SECTIONS.get(genre, []) for f in sec["fields"]
    }


def blocking_enrich_ids_for_genre(genre: str) -> list[str]:
    """Enrich ids whose absence should block ``done`` / count as missing.

    A superset-minus: everything :func:`enrich_ids_for_genre` requests, minus the
    genre's own optional section fields (:func:`genre_section_field_ids`). Those
    section fields are still *requested* during enrich (best effort), but a model
    that omits a couple of them — common, since they are minor detail at the tail
    of the prompt — must not wedge the enrich loop on a permanent "N remaining".
    The author can fill them from the template's inline option hints.
    """
    section_ids = genre_section_field_ids(genre)
    return [
        k for k in enrich_ids_for_genre(genre)
        if k not in section_ids
    ]


#: Map of enrichment field id -> human label, for targeted retry passes.
ENRICH_LABELS: dict[str, str] = {k: label for k, label in ENRICH_KEYS}


def enrich_batches_for(keys: list[str], size: int = 6) -> list[list[tuple[str, str]]]:
    """Batch a subset of enrichment fields into (id, label) chunks.

    Unknown ids are skipped. Small batches keep each LLM call under the
    provider gateway timeout (a single 75-field call 502s upstream).
    """
    pairs = [(k, ENRICH_LABELS[k]) for k in keys if k in ENRICH_LABELS]
    return [pairs[i : i + size] for i in range(0, len(pairs), size)]


#: Enrich fields that describe the novel's WORLD/POWER system rather than its
#: characters or plot beats. When a batch contains any of these, the selected
#: Worldbuilding guide must be in the prompt: without it the model invents a
#: realm ladder from the logline alone (e.g. an ``NC`` novel got
#: "Tập Khí → Luyện Hồn → Ngộ Đạo → Vô Âm" — nothing to do with the Tiên Nghịch
#: canon that ``[NC] NhiCan_Worldbuilding_Complete.md`` actually defines), and
#: that fabrication is then locked into PROJECT_DNA where it outranks the real
#: canon for every later chapter.
_WORLD_ENRICH_KEYS: frozenset[str] = frozenset({
    "world_name", "world_era", "world_mindset", "world_secret",
    "world_locations", "world_pressure", "world_frame_execution",
    "system_name", "system_tiers", "system_cost", "system_resource",
    "system_bottleneck", "system_golden_finger", "system_golden_finger_limit",
    "system_ui_type", "system_origin", "system_relationship",
    "cultivation_speed", "cultivation_age_benchmarks",
    "artifact", "spirit_beast",
    "worldbuilding_execution",
})

#: Top-level (``#``) parts that carry a guide's structural core. Every shipped
#: guide follows the same two-part spine, while the ``##`` sub-headings inside
#: are named per master ("Đại Cảnh Giới Tổng Quan" vs "Hệ Thống Đấu Khí" vs
#: "Cấu Trúc Cơ Bản: Vòng — Cấp — Giai"), so matching the stable ``#`` parts
#: covers all 8 masters where keyword-matching ``##`` missed several:
#:   * ``TỔNG QUAN: ADN SÁNG TÁC`` — the author's creative pillars
#:   * ``PHẦN I`` — always the power/realm system (tu luyện / sức mạnh / đấu khí
#:     / nguyên lực / cảnh giới, depending on the master)
#: Each entry is ``(heading keyword, char budget)``. The budgets are per-part so
#: the power system is never dropped in favour of the pillars: the two parts run
#: 1.2-3.1K and 4.6-8.3K chars respectively across the 8 masters, so a single
#: shared cap silently discarded ``PHẦN I`` — the one part that carries the realm
#: ladder this whole excerpt exists to deliver.
_WB_PART_KEYS: tuple[tuple[str, int], ...] = (
    ("tổng quan: adn sáng tác", 2500),
    ("phần i:", 6500),
)

#: Worldbuilding guides that shipped without the ``[CODE]`` filename prefix.
#: Mirrors ``llm_loop._CODE_NAME_ALIAS`` (which cannot be imported here: the
#: dependency runs llm_loop → dna_form, never the reverse).
_WB_FILE_ALIAS = {"CD": "ThanDong"}

#: Per-call ceiling for the worldbuilding excerpt injected into an enrich batch.
#: The full guides are ~48-60K chars — far too large for a 6-field call — so only
#: the pillars + ladder sections are sent.
_WB_EXCERPT_MAX_CHARS = 6000


def worldbuilding_excerpt(
    genre: str, wb_code: str, limit: int = _WB_EXCERPT_MAX_CHARS
) -> str:
    """Structural excerpt of the selected Worldbuilding guide, or "".

    Returns the guide's creative-pillar and power-system parts (see
    :data:`_WB_PART_KEYS`) so DNA enrichment derives the power system from the
    author's actual canon instead of inventing one. Returns "" when the genre
    ships no guides (only Xianxia does today) or the selected master has none
    (``OT`` / ``PT`` deliberately have no guide — those authors rebuild their
    world per work), in which case the caller keeps the previous behaviour.
    """
    code = (wb_code or "").strip().upper()
    if not code:
        return ""
    guide_dir = (
        _PACKAGE_ROOT / "skills" / "novelkit-canon" / "canon" / "system"
        / canon_pack(genre) / "Worldbuilding guide"
    )
    if not guide_dir.is_dir():
        return ""
    try:
        matches = sorted(guide_dir.glob(f"[[]{code}[]]*.md"))
        alias = _WB_FILE_ALIAS.get(code)
        if not matches and alias:
            matches = sorted(guide_dir.glob(f"{alias}*.md"))
    except OSError:
        return ""
    if not matches:
        return ""
    try:
        text = matches[0].read_text(encoding="utf-8")
    except OSError:
        return ""

    def _budget_for(heading: str) -> Optional[int]:
        for key, budget in _WB_PART_KEYS:
            if key in heading:
                return budget
        return None

    # Collect each wanted ``#`` part, trimmed to ITS OWN budget on a line
    # boundary (never mid-table, which would hand the model a broken ladder row).
    sections: list[str] = []
    current: Optional[list[str]] = None
    budget = 0
    for line in text.splitlines():
        if line.startswith("# "):
            if current:
                sections.append("\n".join(current).strip())
            found = _budget_for(line[2:].strip().lower())
            current = [line] if found is not None else None
            budget = found or 0
            continue
        if current is not None:
            if sum(len(ln) + 1 for ln in current) + len(line) > budget:
                sections.append("\n".join(current).strip())
                current = None
                continue
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return "\n\n".join(piece for piece in sections if piece)[:limit]


def enrich_prompt(base: dict[str, Any], subset: list[tuple[str, str]]) -> tuple[str, str]:
    """Build (system, user) to fill ONE batch of deep enrichment fields,
    grounded in an existing novel's base form values."""
    genre = resolve_genre(base, where="enrich_prompt")
    style_codes = ", ".join(o["value"] for o in STYLE_BY_GENRE.get(genre, []))
    secondary = _g(base, "genre_secondary")
    secondary_style_codes = ", ".join(
        o["value"] for o in STYLE_BY_GENRE.get(secondary, [])
    )
    lang_label = resolve_output_language_label(base)
    lang_rule = output_language_instruction(base)
    seed_lines = [
        f"- {k}: {_g(base, k)}"
        for k in (
            "title", "logline", "usp", "theme", "audience", "tone", "genre",
            "genre_secondary", "style_model", "output_language", "output_language_custom",
            "mc_name", "mc_archetype",
            "mc_traits", "mc_motivation", "mc_want", "mc_need", "mc_ghost",
            "antagonist_name", "antagonist_traits", "antagonist_conflict",
            "hook_strategy", "cultivation_speed", "artifact", "spirit_beast",
            "supporting_cast",
        )
        if _g(base, k)
    ]
    enrich_lines = [f'- "{k}": {label}' for k, label in subset]
    prose_contract = prose_contract_instruction(genre, _g(base, "style_model"))
    system = (
        "Bạn là biên tập viên sáng tạo, hoàn thiện chiều sâu cho PROJECT_DNA của một "
        f"tiểu thuyết mạng. {lang_rule} {prose_contract} "
        "CHỈ trả về một đối tượng JSON hợp lệ."
    )

    # Ground world/power fields in the selected Worldbuilding guide. Mirrors the
    # transfer contract the drafting loop already applies (``_wb_guide_excerpt``):
    # take the STRUCTURE (how realms change the being, what each step costs) but
    # never the source work's proper nouns — so an NC novel inherits the four-Bộ
    # Tiên Nghịch spine without being renamed into a Tiên Nghịch clone.
    wb_block = ""
    if any(key in _WORLD_ENRICH_KEYS for key, _ in subset):
        excerpt = worldbuilding_excerpt(genre, _g(base, "worldbuilding_guide"))
        if excerpt:
            wb_block = (
                "\nĐẠO THƯ DỰNG GIỚI ĐÃ CHỌN — CĂN CỨ BẮT BUỘC cho các trường "
                "thế giới/hệ thống:\n"
                "KHẾ ƯỚC CHUYỂN GIAO: chỉ kế thừa CẤU TRÚC và NGUYÊN TẮC — số "
                "bậc, bản chất biến đổi ở mỗi bậc, cái giá phải trả, nút thắt và "
                "nhịp lộ thông tin. TUYỆT ĐỐI không sao chép tên riêng cảnh giới, "
                "tên nhân vật, tên tông môn hay địa danh từ tác phẩm tham chiếu: "
                "hãy tự đặt tên mới khớp với logline và title của truyện này.\n"
                "Cấm tự bịa một ladder không liên quan tới đạo thư dưới đây.\n\n"
                f"{excerpt}\n"
            )

    user = (
        "DỮ LIỆU HẠT GIỐNG ĐÃ CÓ:\n" + "\n".join(seed_lines) + "\n\n"
        f"Thể loại: {genre}. Mã phong cách hợp lệ: {style_codes}.\n"
        + (
            f"Mã phong cách phụ hợp lệ ({secondary}): "
            f"{secondary_style_codes}.\n"
            if secondary_style_codes
            else ""
        )
        + f"Ngôn ngữ output bắt buộc: {lang_label}.\n"
        + wb_block
        + f"\nHãy điền nội dung bằng {lang_label} cho các trường sau, nhất quán với hạt giống "
        "trên (JSON, key đúng id, chuỗi ngắn; matrix/registry/ladder có thể 2-4 "
        "dòng):\n"
        f"{chr(10).join(enrich_lines)}\n\n"
        "Chỉ JSON, điền HẾT các trường trong danh sách này."
    )
    return system, user


def parse_generated(
    raw: str, genre: str, genre_secondary: str = ""
) -> dict[str, str]:
    """Parse the model's JSON into a clean ``fields`` dict for the form.

    Keeps only known field ids, coerces values to trimmed strings, and drops a
    style code that is not valid for the chosen genre. Robust to code fences and
    surrounding prose (extracts the first balanced ``{...}`` block). Nested
    object/array values (common for matrix/registry/ladder fields) are
    flattened into multi-line text instead of being dropped.
    """
    text = raw.strip()
    if "```" in text:
        text = re.sub(r"```(?:json)?", "", text).strip("` \n")
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}

    valid_ids = {f["id"] for sec in SCHEMA for f in sec["fields"]}
    valid_ids |= {f["id"] for secs in GENRE_SECTIONS.values() for sec in secs for f in sec["fields"]}
    valid_ids |= {k for k, _ in ENRICH_KEYS}
    style_fields = {
        f["id"]
        for sec in SCHEMA
        for f in sec["fields"]
        if f.get("options_source") == "genre_styles"
    }

    out: dict[str, str] = {}
    for key, value in data.items():
        if key not in valid_ids or value is None:
            continue
        val = _coerce_text(value)
        if not val:
            continue
        if key in style_fields:
            # Models often answer with the author's full name or the whole
            # "CODE — Name" label instead of the bare code. Normalise those to a
            # valid code for the genre rather than silently dropping the field
            # (a dropped style code left enrich unable to ever complete).
            style_genre = genre
            if key == "style_secondary":
                style_genre = genre_secondary or _coerce_text(
                    data.get("genre_secondary")
                )
            code = _normalize_style_code(val, style_genre)
            if not code:
                continue  # not resolvable to a valid style code for this genre
            val = code
        if key == "output_language" and val not in OUTPUT_LANGUAGE_CODES:
            continue
        out[key] = val
    return out


def _style_name_aliases(label: str) -> list[str]:
    """Author-name aliases from a style label, lower-cased.

    ``"NC — Nhĩ Căn"`` → ``["nhĩ căn"]`` and ``"ZT — Zhttty / Trương Hằng"`` →
    ``["zhttty", "trương hằng"]`` (a pen name plus its real name).
    """
    if "—" not in label:
        return []
    tail = label.split("—", 1)[1]
    return [part.strip().lower() for part in tail.split("/") if part.strip()]


def _normalize_style_code(value: str, genre: str) -> str:
    """Resolve a model-supplied style answer to a valid code for ``genre``.

    Accepts the bare code ("NC"), a bracketed code ("[NC]"), the full label
    ("NC — Nhĩ Căn"), a ``CODE - name`` variant, or the bare author name
    ("Nhĩ Căn"), case-insensitively. Returns "" when the answer cannot be mapped
    to a code this genre allows — the caller then falls back to
    :func:`apply_style_defaults` rather than to a guess.

    Matching is deliberately EXACT (after normalising separators): the previous
    two-way substring test (``name in low or low in name``) let any prose that
    merely mentioned an author bind to that code, e.g. a sentence like "giọng
    trầm, không dùng lối Vong Ngữ" resolved to ``VN`` — the exact opposite of
    what it says. Codes also collide across genres (``TT`` is Thiên Tằm Thổ Đậu
    in xianxia but Trửu Tử in time_travel), so a loose match could silently swap
    the master that governs the whole novel's voice.
    """
    val = (value or "").strip()
    if not val:
        return ""
    # "[NC]" / "**NC**" / "NC." → "nc"; collapse the label separators so
    # "NC - Nhĩ Căn" and "NC — Nhĩ Căn" normalise the same way.
    low = val.strip("[]()*`\"' \t.").lower()
    low = re.sub(r"\s*[—–-]\s*", " — ", low)
    low = re.sub(r"\s+", " ", low).strip()
    head = low.split(" — ", 1)[0].strip()

    options = STYLE_BY_GENRE.get(genre, [])
    for opt in options:  # exact code, bare or as the label's head
        code = opt["value"].lower()
        if low == code or head == code:
            return opt["value"]
    for opt in options:  # exact full label, or exact author name / alias
        label = opt["label"].lower()
        if low == re.sub(r"\s*[—–-]\s*", " — ", label):
            return opt["value"]
        if low in _style_name_aliases(opt["label"]):
            return opt["value"]
    return ""


def _coerce_text(value: Any) -> str:
    """Flatten a model value into trimmed multi-line text.

    Matrix/registry/ladder fields are often returned as nested objects or
    arrays; we keep that content as readable lines instead of discarding it.
    """
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return str(value).strip()
    if isinstance(value, list):
        lines = [_coerce_text(item) for item in value]
        return "\n".join(line for line in lines if line)
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            inner = _coerce_text(v)
            if not inner:
                continue
            if "\n" in inner:
                indented = "\n".join("  " + ln for ln in inner.splitlines())
                lines.append(f"{k}:\n{indented}")
            else:
                lines.append(f"{k}: {inner}")
        return "\n".join(lines)
    return ""


def _g(fields: dict[str, Any], key: str, default: str = "") -> str:
    val = fields.get(key, default)
    return "" if val is None else str(val).strip()


def resolve_output_language_label(fields: dict[str, Any]) -> str:
    """Human label for the novel's prose output language."""
    code = _g(fields, "output_language", "vi") or "vi"
    if code == "custom":
        return _g(fields, "output_language_custom") or "Custom"
    for opt in OUTPUT_LANGUAGE_OPTIONS:
        if opt["value"] == code:
            return opt["label"]
    return code


def output_language_instruction(fields: dict[str, Any]) -> str:
    """LLM system constraint for DNA/enrich generation."""
    label = resolve_output_language_label(fields)
    return (
        f"Tất cả nội dung văn bản phải được viết bằng {label}. "
        "Không trộn ngôn ngữ khác trừ tên riêng hoặc thuật ngữ cốt truyện cần giữ nguyên."
    )


def _with_output_language_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """Attach derived ``output_language_label`` for template rendering."""
    out = dict(fields)
    if not _g(out, "output_language"):
        out["output_language"] = "vi"
    out["output_language_label"] = resolve_output_language_label(out)
    return out


_GENRE_LABEL = {
    "xianxia": "Tiên Hiệp (Xianxia)",
    "urban": "Đô Thị (Urban)",
    "romance": "Ngôn Tình (Romance)",
    "scifi": "Khoa Huyễn (Sci-Fi)",
    "time_travel": "Xuyên Không (Time Travel)",
    "meta_genre": "Hệ Thống (Meta Genre)",
}
_GENRE_ROW = {
    "xianxia": 1, "urban": 2, "romance": 3,
    "time_travel": 4, "scifi": 5, "meta_genre": 6,
}


def normalize_style_selections(fields: dict[str, Any]) -> list[str]:
    """Canonicalize author selections in place and return unresolved routes."""
    genre = resolve_genre(fields, where="normalize_style_selections")
    secondary = _g(fields, "genre_secondary")
    checks = [
        ("style_model", genre),
        ("worldbuilding_guide", genre),
    ]
    if _g(fields, "style_secondary"):
        checks.append(("style_secondary", secondary))

    errors: list[str] = []
    for key, style_genre in checks:
        value = _g(fields, key)
        if not value:
            continue
        code = _normalize_style_code(value, style_genre)
        if code:
            fields[key] = code
        else:
            errors.append(
                f"{key}={value} không thuộc genre {style_genre or '(trống)'}"
            )
    return errors


def style_selection_errors(fields: dict[str, Any]) -> list[str]:
    """Return routing errors without mutating the caller's sidecar fields."""
    return normalize_style_selections(dict(fields))


def _preflight_state(fields: dict[str, Any]) -> dict[str, bool]:
    def has_values(*keys: str) -> bool:
        return all(
            (value := _g(fields, key))
            and "[Tự sinh]" not in value
            and "_(tự sinh" not in value.lower()
            for key in keys
        )

    def has_three_entries(key: str) -> bool:
        value = _g(fields, key)
        if not value:
            return False
        entries = [part.strip(" -*•\t") for part in re.split(r"[\n;,]+", value)]
        return len([entry for entry in entries if entry]) >= 3

    return {
        "seed": has_values("title", "logline", "usp"),
        "routing": has_values("genre"),
        "style": (
            has_values("style_model", "worldbuilding_guide")
            and (not _g(fields, "genre_secondary") or has_values("style_secondary"))
            and not style_selection_errors(fields)
        ),
        "world": (
            has_values("world_name", "world_secret", "world_locations")
            and has_three_entries("world_locations")
        ),
        "system": has_values("system_tiers", "system_cost", "system_bottleneck"),
        "mc": (
            has_values("mc_want", "mc_need", "mc_ghost", "mc_lie", "mc_voice")
            and _g(fields, "mc_want") != _g(fields, "mc_need")
        ),
        "cast": has_three_entries("supporting_cast"),
        "villain": has_values(
            "antagonist_name", "villain_want", "villain_human_moment"
        ),
        "plot": has_values("inciting_incident", "midpoint_twist", "climax"),
        "boss_ladder": has_values("arc_boss_ladder"),
        "mini_bosses": has_values("mini_bosses"),
    }


def _build_frontmatter_lines(fields: dict[str, Any]) -> list[str]:
    genre = resolve_genre(fields, where="_build_frontmatter_lines")
    secondary = _g(fields, "genre_secondary")
    is_hybrid = bool(secondary)
    squad = derive_squad(genre)
    squad_secondary = derive_squad(secondary) if secondary else ""
    pack = canon_pack(genre)
    pack_secondary = canon_pack(secondary) if secondary else ""
    generated = datetime.now(timezone.utc).date().isoformat()
    template_source = (
        "templates/PROJECT_DNA_TEMPLATE.md"
        if is_hybrid
        else (dna_genre_render.genre_template_relpath(genre) or "templates/PROJECT_DNA_TEMPLATE.md")
    )
    return [
        "---",
        f"generated: {generated}",
        f"genre: {'hybrid' if is_hybrid else genre}",
        f"genre_primary: {genre}",
        f"genre_secondary: {secondary}",
        f"hybrid_ratio: {_g(fields, 'hybrid_ratio')}",
        f"style_model: {_g(fields, 'style_model')}",
        f"style_blend: {_g(fields, 'style_secondary')}",
        f"worldbuilding_guide: {_g(fields, 'worldbuilding_guide')}",
        f"sub_agents_squad: {squad}",
        f"sub_agents_squad_secondary: {squad_secondary}",
        f"canon_pack: system/{pack}",
        f"canon_pack_secondary: {('system/' + pack_secondary) if pack_secondary else ''}",
        f"template_source: {template_source}",
        "status: draft",
        f"target_chapters: {_g(fields, 'target_chapters', '30')}",
        f"arc_count: {_g(fields, 'arc_count')}",
        f"target_words_per_chapter: {_g(fields, 'target_words_per_chapter', '2500')}",
        f"cultivation_speed: {_g(fields, 'cultivation_speed')}",
        f"cultivation_age_benchmarks: [{_g(fields, 'cultivation_age_benchmarks')}]",
        f"output_language: {_g(fields, 'output_language', 'vi') or 'vi'}",
        f"output_language_label: {resolve_output_language_label(fields)}",
        "---",
    ]


def _build_preflight_section(fields: dict[str, Any], *, section_number: str = "XIII") -> str:
    preflight = _preflight_state(fields)

    def done(item: str) -> str:
        return "☑" if preflight[item] else "□"

    def v(key: str, placeholder: str = "") -> str:
        return _g(fields, key) or placeholder

    return f"""## {section_number}. SỔ KIỂM KHỞI TẠO (Pre-flight)

```
{done('seed')} Hạt giống: lời dẫn + dấu riêng rõ ràng
{done('routing')} Thể loại đã chọn, điều phối xác nhận
{done('style')} Mã Đại Thần + đạo thư dựng giới đã khóa nếu có
{done('world')} Thế giới quan: ≥ 3 địa danh + 1 bí mật lịch sử
{done('system')} Sức mạnh: cấp bậc + giới hạn + nút thắt rõ
{done('mc')} Nhân vật chính: want ≠ need, có ghost, lie, giọng riêng
{done('cast')} ≥ 3 nhân vật phụ có giọng riêng
{done('villain')} Phản diện cuối có want + khoảnh khắc "người"
{done('plot')} Khởi phát + midpoint + climax đã có ý tưởng
{done('boss_ladder')} Bậc thang trùm đại hồi: {v('arc_boss_ladder', '[Tự sinh]')}
{done('mini_bosses')} Tiểu chướng / Chướng ngại: {v('mini_bosses', '[Tự sinh]')}
```"""


def render_project_dna(fields: dict[str, Any]) -> str:
    """Render form ``fields`` into a COMPLETE PROJECT_DNA.md.

    Single-genre novels use the matching file under
    ``templates/genres/PROJECT_DNA_<GENRE>.md``. Hybrid novels (or unknown
    genres) fall back to the unified ``PROJECT_DNA_TEMPLATE.md`` layout.
    """
    fields = _with_output_language_fields(fields)
    genre = resolve_genre(fields, where="render_project_dna")
    secondary = _g(fields, "genre_secondary")
    if not secondary and dna_genre_render.genre_template_path(genre):
        return dna_genre_render.render_from_genre_template(
            fields,
            g=_g,
            build_frontmatter=_build_frontmatter_lines,
            build_preflight=lambda f: _build_preflight_section(f, section_number="XII"),
        )
    return _render_unified_project_dna(fields)


def _render_unified_project_dna(fields: dict[str, Any]) -> str:
    """Render using the canonical 14-section ``PROJECT_DNA_TEMPLATE.md`` layout."""
    def v(key: str, placeholder: str = "") -> str:
        return _g(fields, key) or placeholder

    title = _g(fields, "title") or "Tác phẩm chưa đặt tên"
    genre = resolve_genre(fields, where="_render_unified_project_dna")
    secondary = _g(fields, "genre_secondary")
    is_hybrid = bool(secondary)
    chosen_row = _GENRE_ROW.get(genre, 1)
    preflight = _preflight_state(fields)

    def mark(row: int) -> str:
        return "☑" if row == chosen_row else "☐"

    def done(item: str) -> str:
        return "☑" if preflight[item] else "□"

    fm = _build_frontmatter_lines(fields)

    body = f"""# PROJECT_DNA.md — {title}

> **File này là SINGLE SOURCE OF TRUTH cho toàn bộ hệ thống Agentic AI.**
> Mọi Sub-Agent (World Builder → Character Architect → Plot Weaver → Prose Writer → Quality Auditor) ĐỌC file này TRƯỚC KHI bắt đầu bất kỳ tác vụ nào.

---

## I. HẠT GIỐNG (Seed)

- **Tên tác phẩm:** {v('title')}
- **Logline (1 câu pitch):** {v('logline')}
- **Thể loại chính:** {_GENRE_LABEL.get(genre, genre)}
- **Thể loại phụ:** {secondary or '_(không)_'}
- **Đối tượng độc giả:** {v('audience')}
- **Ngôn ngữ output:** {v('output_language_label')}
- **USP (Unique Selling Point):** {v('usp')}
- **Chủ đề cốt lõi:** {v('theme')}
- **Ước tính tổng số chương:** {_g(fields, 'target_chapters', '30')}
- **Ước tính số Arc:** {v('arc_count', '_(tự sinh)_')}

---

## II. THỂ LOẠI & ROUTING

| # | Thể Loại | Squad | Canon Pack | Chọn |
|---|---|---|---|---|
| 1 | Tiên Hiệp (Xianxia) | `sub_agents/` | `system/Xianxia/` | {mark(1)} |
| 2 | Đô Thị (Urban) | `sub_agents_do_thi/` | `system/Urban/` | {mark(2)} |
| 3 | Ngôn Tình (Romance) | `sub_agents_ngon_tinh/` | `system/Romance/` | {mark(3)} |
| 4 | Xuyên Không (Time Travel) | `sub_agents_xuyen_khong/` | `system/Time Travel/` | {mark(4)} |
| 5 | Khoa Huyễn (Sci-Fi) | `sub_agents_khoa_huyen/` | `system/Sci-fi/` | {mark(5)} |
| 6 | Hệ Thống (Meta Genre) | `sub_agents_he_thong/` | `system/Meta Genre/` | {mark(6)} |

**Có phải Hybrid không?** {'☑ Có' if is_hybrid else '☑ Không'}

- **Thể loại CHÍNH (Primary):** {_GENRE_LABEL.get(genre, genre)}
- **Thể loại PHỤ (Secondary):** {secondary or '_(không)_'}
- **Tỷ lệ pha trộn:** {v('hybrid_ratio', '_(không)_')}

---

## III. PHONG CÁCH ĐẠI THẦN

- **Phong cách chính (Mã):** {v('style_model')}
- **Phong cách phụ (Mã):** {v('style_secondary', '_(không)_')}
- **Worldbuilding guide (Mã):** {v('worldbuilding_guide')}
- **Khí sắc / Từ khóa giọng văn:** {v('tone')}
- **Quy tắc ưu tiên:** PROJECT_DNA/canon truyện > Worldbuilding guide > Author Style.

---

## IV. THẾ GIỚI QUAN

### A. Nền Tảng Chung

- **Tên thế giới / Bối cảnh:** {v('world_name', '_(tự sinh)_')}
- **Thời đại:** {v('world_era', '_(tự sinh)_')}
- **Tư duy / Quy luật trung tâm:** {v('world_mindset', '_(tự sinh)_')}
- **Bí mật lịch sử / Lời nguyền:** {v('world_secret', '_(tự sinh)_')}
- **Địa điểm quan trọng:** {v('world_locations', '_(tự sinh)_')}

### B. Tu Luyện / Cơ Chế _(nếu áp dụng)_

- **Tốc độ tu luyện:** {v('cultivation_speed', '_(tự sinh)_')}
- **Mốc tuổi tu luyện:** {v('cultivation_age_benchmarks', '_(tự sinh)_')}

---

## V. HỆ THỐNG SỨC MẠNH / CƠ CHẾ CỐT LÕI

- **Tên hệ thống:** {v('system_name', '_(tự sinh)_')}
- **Các cấp bậc / Giai tầng:** {v('system_tiers', '_(tự sinh)_')}
- **Cái giá đột phá / Hạn chế:** {v('system_cost', '_(tự sinh)_')}
- **Tài nguyên cốt lõi:** {v('system_resource', '_(tự sinh)_')}
- **Nút thắt chính:** {v('system_bottleneck', '_(tự sinh)_')}
- **Kim Thủ Chỉ (Golden Finger):** {v('system_golden_finger') or v('artifact', '_(tự sinh)_')}
- **Giới hạn Kim Thủ Chỉ:** {v('system_golden_finger_limit', '_(tự sinh)_')}
- **Đồng hành đặc biệt (Linh Thú):** {v('spirit_beast', '_(không)_')}

---

## VI. NHÂN VẬT CHÍNH

- **Tên:** {v('mc_name')}
- **Cốt cách / Archetype:** {v('mc_archetype')}
- **Ngoại hình / Đặc điểm nổi bật:** {v('mc_traits')}
- **Động cơ khởi đầu:** {v('mc_motivation')}

### Tâm Lý & Nội Tâm

- **Want (muốn gì — mục tiêu bề mặt):** {v('mc_want')}
- **Need (cần gì — khác want):** {v('mc_need')}
- **Lie (niềm tin sai cần thay đổi):** {v('mc_lie', '_(tự sinh)_')}
- **Ghost (quá khứ ám ảnh):** {v('mc_ghost')}
- **Voice (giọng riêng):** {v('mc_voice', '_(tự sinh)_')}

---

## VII. DÀN NHÂN VẬT

- **Dàn nhân vật phụ:** {v('supporting_cast', '_(tự sinh ≥ 3 nhân vật có giọng riêng)_')}

### Tình Yêu / Đối Tác Chính

- **Tình yêu / đối tác chính:** {v('cast_love_interest', '_(tự sinh)_')}
- **Sư phụ / Mentor:** {v('cast_mentor', '_(tự sinh)_')}
- **Huynh đệ / Đồng đội:** {v('cast_allies', '_(tự sinh)_')}

### Relationship Matrix

{v('cast_relationship_matrix', '_(tự sinh: MC↔nhân vật chính, MC↔mentor, MC↔phản diện)_')}

---

## VIII. PHẢN DIỆN

### Phản Diện Cuối Cùng (Final Boss)

- **Tên / Danh xưng:** {v('antagonist_name')}
- **Đặc điểm:** {v('antagonist_traits')}
- **Xung đột cốt lõi với MC:** {v('antagonist_conflict')}
- **Want phản diện:** {v('villain_want', '_(tự sinh)_')}
- **Khoảnh khắc "người":** {v('villain_human_moment', '_(tự sinh)_')}
- **Vì sao hắn ĐÚNG (từ góc nhìn của hắn):** {v('villain_justified', '_(tự sinh)_')}

### Phản Diện Arc

| Arc | Phản Diện | Loại | Liên hệ Boss cuối |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |

---

## IX. CỐT TRUYỆN & CẤU TRÚC NARRATIVE

### A. Tổng Quan

- **Sự kiện khởi phát (Inciting Incident):** {v('inciting_incident', '_(tự sinh)_')}
- **Midpoint Twist:** {v('midpoint_twist', '_(tự sinh)_')}
- **All Is Lost Moment:** {v('all_is_lost', '_(tự sinh)_')}
- **Tầm nhìn Climax:** {v('climax', '_(tự sinh)_')}
- **Kiểu kết thúc:** {v('ending_style', '_(tự sinh)_')}
- **Thế câu dẫn độc giả (Hook):** {v('hook_strategy', '_(tự sinh)_')}

### B. Arc Planning

| Arc | Tên Arc | Chapters | Phản Diện | Sự Kiện Chính |
|---|---|---|---|---|
| 1 | | Ch.1 - Ch.__ | | |
| 2 | | Ch.__ - Ch.__ | | |
| 3 | | Ch.__ - Ch.__ | | |

### C. Seed Master — Phục Bút Xuyên Suốt

{v('seed_master', '_(tự sinh: 3 seed — cài tại / thu tại / mô tả)_')}

### D. Thread Registry (Tuyến Truyện)

{v('thread_registry', '_(tự sinh: Quest / Fire / Constellation)_')}

---

## X. GIỌNG VĂN & CẤM KỴ

- **Từ khóa giọng văn:** {v('tone', '_(tự sinh)_')}
- **Chủ đề cốt lõi:** {v('theme', '_(tự sinh)_')}
- **Bảng giác quan:** {v('sensory_palette', '_(tự sinh)_')}

### Creative Premise Contract

- **Core Wound:** {v('core_wound', '_(tự sinh)_')}
- **Irreversible Choice:** {v('irreversible_choice', '_(tự sinh)_')}
- **Moral Contradiction:** {v('moral_contradiction', '_(tự sinh)_')}
- **World Pressure:** {v('world_pressure', '_(tự sinh)_')}
- **Motif Execution Angle:** {v('motif_execution_angle', '_(tự sinh)_')}
- **Reader Addiction Loop:** {v('reader_addiction_loop', '_(tự sinh)_')}
- **Scene Promise:** {v('scene_promise', '_(tự sinh)_')}
- **Scene Vitality Contract:** {v('scene_vitality_contract', '_(tự sinh)_')}

### Anti-AI DNA Checklist (Prose Writer & Quality Auditor PHẢI tuân thủ)

```
CẤM TUYỆT ĐỐI:
  □ "vô cùng", "cực kỳ", "rất" (dùng hình ảnh thay thế)
  □ "Không chỉ... mà còn..."
  □ "Điều này cho thấy/chứng minh/phản ánh..."
  □ Mở 3+ đoạn liên tiếp bằng cùng chủ ngữ
  □ "Hắn cảm thấy [tính từ]" — phải SHOW, không TELL
  □ Infodump > 100 chữ liên tục
  □ Tiếng lóng/chửi tục hiện đại và tham chiếu văn hóa ngoài thế giới truyện
  □ Đơn vị giờ hiện đại trong bối cảnh cổ phong (dùng canh, khắc, giờ Thìn/Tỵ)
  □ Quá 2 câu cực ngắn liên tiếp, trừ chiến đấu hoặc chấn động thật sự
  □ Punchline gượng, chơi chữ tự giải thích, đám đông cười phụ họa
```

---

## XI. NHỊP ĐỘ & CẤU TRÚC TỰ SINH

- **Dàn thế câu dẫn:** {v('hook_mix', '[Tự sinh]')}
- **Nhịp tiểu sảng:** {v('minor_payoff_cadence', '[Tự sinh]')}
- **Nhịp đại sảng:** {v('major_payoff_cadence', '[Tự sinh]')}
- **Mục tiêu đan tuyến:** {v('strand_weave_targets', '[Tự sinh]')}
- **Chương tích lũy vs chương bùng nổ:** {v('water_vs_burst_ratio', '[Tự sinh]')}
- **Mỗi chương phải trả:** {v('micro_payoff_per_chapter', '[Tự sinh]')}

### Thước đo cố định

- **Số từ mỗi chương:** {_g(fields, 'target_words_per_chapter', '2500')}
- **Điểm chất lượng tối thiểu:** 85/100
- **Phục bút mỗi chương:** ≥ 1
- **Giới hạn giải thích liền mạch:** ≤ 100 chữ

---

## XII. KHẾ ƯỚC THI TRIỂN HẠT GIỐNG

- **Cách thi triển cốt cách nhân vật chính:** {v('mc_archetype_execution', '[Tự sinh]')}
- **Cách vận dụng thế câu dẫn:** {v('hook_strategy_execution', '[Tự sinh]')}
- **Cách thi triển văn phong:** {v('style_execution', '[Tự sinh]')}
- **Cách lộ thiên địa:** {v('worldbuilding_execution', '[Tự sinh]')}
- **Cách bối cảnh ép lựa chọn:** {v('world_frame_execution', '[Tự sinh]')}

---

{_build_preflight_section(fields, section_number="XIII")}

---

## XIV. HYBRID GENRE EXAMPLES

```yaml
# Example: Tiên Hiệp + Hắc Ám
# genre: hybrid
# genre_secondary: dark theme
# hybrid_ratio: 70-30
```

---

*File này là SINGLE SOURCE OF TRUTH cho toàn bộ hệ thống Agentic AI.*
*Pipeline: World Builder → Character Architect → Plot Weaver → Prose Writer → Quality Auditor*
*Orchestrator: Lãng Khách (浪客) — Tổng Quản*
"""
    return "\n".join(fm) + "\n\n" + body


def required_missing(fields: dict[str, Any]) -> list[str]:
    """Return labels of required fields left blank."""
    missing: list[str] = []
    for section in SCHEMA:
        for f in section["fields"]:
            if f.get("required") and not _g(fields, f["id"]):
                missing.append(f["label"])
    return missing


def target_chapters_of(fields: dict[str, Any]) -> int:
    try:
        return max(1, int(float(_g(fields, "target_chapters", "30"))))
    except (ValueError, TypeError):
        return 30


def apply_style_defaults(
    fields: dict[str, Any], only: Optional[set[str]] = None
) -> dict[str, Any]:
    """Guarantee the style fields the pre-flight checklist needs are never left
    blank after AI completion.

    ``style_model`` falls back to the primary genre's first canonical author,
    ``style_secondary`` to the secondary genre's first author, and
    ``worldbuilding_guide`` to ``style_model``. Models frequently
    answer these with a full author name or prose instead of the bare code, so
    even after :func:`parse_generated` normalisation they can be dropped; without
    a deterministic fallback the enrich loop can never reach "done" and the field
    renders as a permanent ``[Tự sinh]`` with the pre-flight "style" item
    unchecked. The author can still change either value in the PROJECT_DNA tab.

    ``only`` limits which keys are defaulted (used by the enrich flow to default
    a field only after the model has actually been asked for it, never before).
    Mutates and returns ``fields``.
    """
    keys = only if only is not None else {
        "style_model", "style_secondary", "worldbuilding_guide"
    }
    genre = resolve_genre(fields, where="default_style_selections")
    options = STYLE_BY_GENRE.get(genre) or STYLE_BY_GENRE.get(DEFAULT_GENRE, [])
    default_code = options[0]["value"] if options else ""
    if "style_model" in keys and not _g(fields, "style_model") and default_code:
        fields["style_model"] = default_code
    if "worldbuilding_guide" in keys and not _g(fields, "worldbuilding_guide"):
        fields["worldbuilding_guide"] = _g(fields, "style_model") or default_code
    secondary = _g(fields, "genre_secondary")
    secondary_options = STYLE_BY_GENRE.get(secondary, [])
    if (
        "style_secondary" in keys
        and secondary_options
        and not _g(fields, "style_secondary")
    ):
        fields["style_secondary"] = secondary_options[0]["value"]
    return fields


def squad_of(fields: dict[str, Any]) -> str:
    return derive_squad(resolve_genre(fields, where="squad_of"))
