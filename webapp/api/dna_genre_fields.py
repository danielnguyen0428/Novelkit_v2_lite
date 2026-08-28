"""Genre-specific form sections and extended canon metadata for Studio."""

from __future__ import annotations

from typing import Any

# Studio supports 6 genres with PROJECT_DNA templates. Other canon packs exist for
# pipeline/context-engine but need templates before joining the create-novel dropdown.
EXTENDED_CANON_GENRES: list[dict[str, str]] = [
    {"slug": "apocalypse", "label": "Tận Thế / Apocalypse"},
    {"slug": "cthulhu", "label": "Cthulhu / Cosmic Horror"},
    {"slug": "dark-theme", "label": "Dark Theme"},
    {"slug": "many-children", "label": "Many Children"},
    {"slug": "rules-horror", "label": "Rules Horror"},
    {"slug": "short-form", "label": "Short Form"},
    {"slug": "substitute", "label": "Substitute"},
    {"slug": "streaming", "label": "Streaming"},
    {"slug": "esports", "label": "eSports"},
    {"slug": "storydepth", "label": "StoryDepth (cross-genre)"},
    {"slug": "war-espionage", "label": "War Espionage"},
]

GENRE_SECTIONS: dict[str, list[dict[str, Any]]] = {
    "xianxia": [
        {
            "section": "Tiên Hiệp — căn cơ & tu luyện",
            "fields": [
                {
                    "id": "mc_age_foundation",
                    "label": "Tuổi / Căn cơ ban đầu",
                    "type": "text",
                    "placeholder": "vd: 16 tuổi, phế mạch",
                },
                {
                    "id": "mc_spirit_root",
                    "label": "Linh căn",
                    "type": "text",
                    "placeholder": "Đơn / Song / Tạp / Thiên biến / Hỗn Độn",
                },
                {
                    "id": "mc_starting_realm",
                    "label": "Cảnh giới mở đầu",
                    "type": "text",
                    "placeholder": "Luyện Khí / Trúc Cơ",
                },
                {
                    "id": "main_cultivation_method",
                    "label": "Công pháp chính",
                    "type": "textarea",
                },
            ],
        },
    ],
    "urban": [
        {
            "section": "Đô Thị — thân phận & dị năng",
            "fields": [
                {"id": "mc_age", "label": "Tuổi", "type": "text"},
                {
                    "id": "mc_occupation",
                    "label": "Nghề nghiệp / Thân phận",
                    "type": "text",
                    "placeholder": "CEO / bác sĩ / sinh viên",
                },
                {
                    "id": "mc_secret",
                    "label": "Bí mật của MC",
                    "type": "textarea",
                },
                {
                    "id": "urban_power_type",
                    "label": "Loại dị năng / siêu năng",
                    "type": "textarea",
                },
                {
                    "id": "urban_power_limit",
                    "label": "Giới hạn / Cooldown dị năng",
                    "type": "textarea",
                },
            ],
        },
    ],
    "romance": [
        {
            "section": "Ngôn tình — nam chính & rào cản",
            "fields": [
                {"id": "mc_age", "label": "Tuổi nữ chính", "type": "text"},
                {
                    "id": "cast_love_interest",
                    "label": "Tên nam chính",
                    "type": "text",
                },
                {
                    "id": "love_interest_secret",
                    "label": "Bí mật nam chính giấu",
                    "type": "textarea",
                },
                {
                    "id": "romance_barrier_1",
                    "label": "Rào cản tình yêu 1",
                    "type": "textarea",
                },
                {
                    "id": "romance_barrier_2",
                    "label": "Rào cản tình yêu 2",
                    "type": "textarea",
                },
                {
                    "id": "romance_barrier_3",
                    "label": "Rào cản tình yêu 3",
                    "type": "textarea",
                },
            ],
        },
    ],
    "scifi": [
        {
            "section": "Khoa Huyễn — nhân vật & đối thủ",
            "fields": [
                {"id": "mc_age", "label": "Tuổi", "type": "text"},
                {
                    "id": "mc_occupation",
                    "label": "Nghề nghiệp",
                    "type": "text",
                    "placeholder": "phi hành gia / kỹ sư / quân nhân",
                },
                {
                    "id": "antagonist_codename",
                    "label": "Tên / Mã đối thủ",
                    "type": "text",
                },
                {
                    "id": "antagonist_threat",
                    "label": "Mối đe dọa / Mục tiêu đối thủ",
                    "type": "textarea",
                },
                {
                    "id": "scifi_tech_core",
                    "label": "Công nghệ cốt lõi",
                    "type": "textarea",
                },
            ],
        },
    ],
    "time_travel": [
        {
            "section": "Xuyên không — linh hồn hiện đại",
            "fields": [
                {
                    "id": "mc_modern_name",
                    "label": "Tên hiện đại (trước xuyên)",
                    "type": "text",
                },
                {"id": "mc_modern_age", "label": "Tuổi hiện đại", "type": "text"},
                {
                    "id": "mc_modern_job",
                    "label": "Nghề nghiệp hiện đại",
                    "type": "text",
                },
                {
                    "id": "mc_modern_knowledge",
                    "label": "Kiến thức chuyên sâu mang sang",
                    "type": "textarea",
                },
                {
                    "id": "transmigration_reason",
                    "label": "Lý do xuyên không",
                    "type": "textarea",
                },
                {
                    "id": "transmigration_type",
                    "label": "Loại xuyên không",
                    "type": "text",
                    "placeholder": "tai nạn / hệ thống / trọng sinh",
                },
            ],
        },
    ],
    "meta_genre": [
        {
            "section": "Hệ thống — panel & quest",
            "fields": [
                {
                    "id": "system_ui_type",
                    "label": "Giao diện hệ thống",
                    "type": "text",
                    "placeholder": "panel / giọng nói / companion AI",
                },
                {
                    "id": "system_origin",
                    "label": "Nguồn gốc hệ thống",
                    "type": "textarea",
                },
                {
                    "id": "system_relationship",
                    "label": "Quan hệ MC ↔ System",
                    "type": "textarea",
                },
                {
                    "id": "quest_reward_logic",
                    "label": "Logic thưởng / phạt quest",
                    "type": "textarea",
                },
            ],
        },
    ],
}

# Extra enrich targets for genre-only craft bullets (beyond ENRICH_KEYS core).
GENRE_ENRICH_KEYS: tuple[tuple[str, str], ...] = (
    ("mc_spirit_root", "Linh căn của nhân vật chính"),
    ("mc_starting_realm", "Cảnh giới mở đầu"),
    ("mc_age_foundation", "Tuổi / căn cơ ban đầu"),
    ("main_cultivation_method", "Công pháp chính"),
    ("mc_age", "Tuổi nhân vật chính"),
    ("mc_occupation", "Nghề nghiệp / thân phận"),
    ("mc_secret", "Bí mật của MC"),
    ("urban_power_type", "Loại dị năng"),
    ("urban_power_limit", "Giới hạn dị năng"),
    ("love_interest_secret", "Bí mật nam chính giấu"),
    ("romance_barrier_1", "Rào cản tình yêu chính 1"),
    ("romance_barrier_2", "Rào cản tình yêu chính 2"),
    ("romance_barrier_3", "Rào cản tình yêu chính 3"),
    ("antagonist_codename", "Tên / mã đối thủ"),
    ("antagonist_threat", "Mối đe dọa của đối thủ"),
    ("scifi_tech_core", "Công nghệ cốt lõi"),
    ("mc_modern_name", "Tên hiện đại trước khi xuyên"),
    ("mc_modern_age", "Tuổi hiện đại"),
    ("mc_modern_job", "Nghề nghiệp hiện đại"),
    ("mc_modern_knowledge", "Kiến thức hiện đại mang sang"),
    ("transmigration_reason", "Lý do xuyên không"),
    ("transmigration_type", "Loại xuyên không"),
    ("system_ui_type", "Giao diện hệ thống"),
    ("system_origin", "Nguồn gốc hệ thống"),
    ("system_relationship", "Quan hệ MC với System"),
    ("quest_reward_logic", "Logic thưởng/phạt quest"),
)


def all_field_defs_for_genre(genre: str, base_schema: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Base SCHEMA fields visible for ``genre`` plus genre extension fields."""
    out: list[dict[str, Any]] = []
    for section in base_schema:
        for field in section["fields"]:
            allowed = field.get("genres")
            if allowed and genre not in allowed:
                continue
            out.append(field)
    for section in GENRE_SECTIONS.get(genre, []):
        out.extend(section["fields"])
    return out


def all_field_ids_for_genre(genre: str, base_schema: list[dict[str, Any]]) -> set[str]:
    return {f["id"] for f in all_field_defs_for_genre(genre, base_schema)}
