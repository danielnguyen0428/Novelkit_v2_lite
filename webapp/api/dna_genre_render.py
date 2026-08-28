"""Render PROJECT_DNA.md from per-genre templates in novelkit-canon.

Studio loads ``skills/novelkit-canon/templates/genres/PROJECT_DNA_<GENRE>.md``
when the author picks a single primary genre (non-hybrid). Hybrid novels still
use the unified ``PROJECT_DNA_TEMPLATE.md`` layout via ``dna_form``.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_GENRE_TEMPLATES_DIR = _PACKAGE_ROOT / "skills" / "novelkit-canon" / "templates" / "genres"

GENRE_TEMPLATE_FILE: dict[str, str] = {
    "xianxia": "PROJECT_DNA_XIANXIA.md",
    "urban": "PROJECT_DNA_URBAN.md",
    "romance": "PROJECT_DNA_ROMANCE.md",
    "scifi": "PROJECT_DNA_SCIFI.md",
    "time_travel": "PROJECT_DNA_TIME_TRAVEL.md",
    "meta_genre": "PROJECT_DNA_META_GENRE.md",
}

# Labels → form field ids (global when the label is unambiguous).
_GLOBAL_BULLET_FIELDS: dict[str, str] = {
    "Tên tác phẩm": "title",
    "Logline (1 câu)": "logline",
    "Dấu riêng (USP)": "usp",
    "Chủ đề cốt lõi": "theme",
    "Đối tượng độc giả": "audience",
    "Ngôn ngữ output": "output_language_label",
    "Ngôn ngữ viết": "output_language_label",
    "Khí sắc chủ đạo": "tone",
    "Mã Đại Thần": "style_model",
    "Đạo thư dựng giới": "worldbuilding_guide",
    "Want (muốn gì)": "mc_want",
    "Need (cần gì — khác Want)": "mc_need",
    "Ghost (vết thương cũ)": "mc_ghost",
    "Ghost": "mc_ghost",
    "Thế câu dẫn": "hook_strategy",
    "Inciting Incident": "inciting_incident",
    "Midpoint Twist": "midpoint_twist",
    "All Is Lost": "all_is_lost",
    "Climax Vision": "climax",
    "Ending": "ending_style",
    "Ending Type": "ending_style",
    "Want phản diện": "villain_want",
    "Khoảnh khắc \"người\"": "villain_human_moment",
    "Vì sao hắn ĐÚNG (từ góc nhìn của hắn)": "villain_justified",
    "Mốc tuổi benchmark": "cultivation_age_benchmarks",
    "Ladder": "system_tiers",
    "Bottleneck chính": "system_bottleneck",
    "Cái giá đột phá": "system_cost",
    "Kim Thủ Chỉ (nếu có)": "system_golden_finger",
    "Kim Thủ Chỉ (Golden Finger)": "system_golden_finger",
    "Giới hạn Kim Thủ Chỉ": "system_golden_finger_limit",
    "Lie (niềm tin sai cần thay đổi)": "mc_lie",
    "Voice riêng": "mc_voice",
    "Voice (giọng riêng)": "mc_voice",
    "Câu hỏi tồn tại": "mc_motivation",
    "Tên thế giới / Bối cảnh": "world_name",
    "Thời đại": "world_era",
    "Tư duy / Quy luật trung tâm": "world_mindset",
    "Bí mật lịch sử / Lời nguyền": "world_secret",
    "Địa điểm quan trọng": "world_locations",
    "Tên hệ thống": "system_name",
    "Tài nguyên cốt lõi": "system_resource",
    "Nút thắt chính": "system_bottleneck",
    "Tên / Phẩm cấp": "artifact",
    "Tên / Chủng loại": "spirit_beast",
    "Đạo lữ / Chính thất": "cast_love_interest",
    "Sư phụ / Mentor": "cast_mentor",
    "Đồng môn / Huynh đệ": "cast_allies",
    "Dàn nhân vật phụ": "supporting_cast",
    "Creative Premise Contract": "core_wound",
    "Scene Vitality Contract": "scene_vitality_contract",
    "Cultivation Clock cadence": "minor_payoff_cadence",
    "Fuel accumulation plan": "strand_weave_targets",
    "Major breakthrough milestones": "major_payoff_cadence",
    "Intimacy beats cadence": "minor_payoff_cadence",
    "Misunderstanding rhythm": "hook_mix",
    # Genre pacing bullets (section X/XI) — progression = major, beats = minor.
    "Power progression cadence": "major_payoff_cadence",
    "Scandal/face-slapping beats": "minor_payoff_cadence",
    "Tech progression cadence": "major_payoff_cadence",
    "Scientific discovery rhythm": "minor_payoff_cadence",
    "Status progression cadence": "major_payoff_cadence",
    "Butterfly effect milestones": "minor_payoff_cadence",
    "System interaction cadence": "major_payoff_cadence",
    "Level up / quest complete rhythm": "minor_payoff_cadence",
}

# Section header substring → label → field (disambiguate repeated labels like "Tên").
_SECTION_BULLET_FIELDS: dict[str, dict[str, str]] = {
    "III. NHÂN VẬT CHÍNH": {
        "Tên / Danh xưng": "mc_name",
        "Tên": "mc_name",
        "Cốt cách": "mc_archetype",
        "Đặc điểm nổi bật": "mc_traits",
        "Động cơ khởi đầu": "mc_motivation",
        "Tuổi / Căn cơ ban đầu": "mc_age_foundation",
        "Linh căn": "mc_spirit_root",
        "Cảnh giới mở đầu": "mc_starting_realm",
        "Tuổi": "mc_age",
        "Nghề nghiệp / Thân phận": "mc_occupation",
        "Xuất thân": "mc_motivation",
        "Bí mật của MC": "mc_secret",
        "Archetype": "mc_archetype",
        "Tính cách cốt lõi": "mc_traits",
    },
    "III. NỮ CHÍNH": {
        "Tên": "mc_name",
        "Tính cách cốt lõi": "mc_traits",
        "Archetype": "mc_archetype",
        "Voice riêng": "mc_voice",
    },
    "IV. NAM CHÍNH": {
        "Tên": "cast_love_interest",
        "Archetype": "antagonist_traits",
        "Bí mật anh giấu": "love_interest_secret",
    },
    "IV. ĐẠO ĐỐI LẬP": {
        "Tên / Danh hiệu": "antagonist_name",
        "Đạo / Pháp môn": "antagonist_traits",
        "Xung đột cốt lõi với MC": "antagonist_conflict",
    },
    "IV. ĐỐI TRỌNG": {
        "Tên / Thế lực": "antagonist_name",
        "Thân phận": "antagonist_traits",
        "Tại sao đối đầu MC": "antagonist_conflict",
    },
    "IV. ĐỐI THỦ": {
        "Tên / Văn minh": "antagonist_name",
        "Tên / Mã danh": "antagonist_codename",
        "Mục tiêu": "antagonist_threat",
        "Mối đe dọa": "antagonist_conflict",
    },
    "VIII. PHẢN DIỆN": {
        "Tên / Danh xưng": "antagonist_name",
        "Đặc điểm": "antagonist_traits",
        "Xung đột cốt lõi với MC": "antagonist_conflict",
    },
    "VI. THẾ GIỚI TU CHÂN": {
        "Thiên Đạo": "world_mindset",
        "Bí cảnh chính (1-3)": "world_locations",
    },
    "VI. THẾ GIỚI ĐÔ THỊ": {
        "Thành phố / Quốc gia": "world_name",
        "Setting chính": "world_locations",
    },
    "VI. THẾ GIỚI KHOA HUYỄN": {
        "Tên thiên hà / Vũ trụ": "world_name",
        "Thời đại": "world_era",
    },
    "V. THỜI ĐẠI ĐẾN": {
        "Tên triều đại / Quốc gia": "world_name",
        "Niên đại": "world_era",
    },
    "IV. CƠ CHẾ XUYÊN KHÔNG": {
        "Loại xuyên không": "transmigration_type",
    },
    "V. THẾ GIỚI BASE": {
        "Tên thế giới gốc": "world_name",
        "Bối cảnh": "world_era",
    },
    "VIII. BỐI CẢNH": {
        "Bối cảnh xã hội": "world_name",
        "Môi trường chính": "world_locations",
        "Thời đại": "world_era",
    },
    "IV. HỆ THỐNG": {
        "Tên hệ thống": "system_name",
        "Loại hệ thống": "system_tiers",
        "Giao diện": "system_ui_type",
        "Nguồn gốc": "system_origin",
    },
    "VII. HỆ THỐNG TU LUYỆN MC": {
        "Công pháp chính": "main_cultivation_method",
    },
    "VII. HỆ THỐNG SỨC MẠNH": {
        "Hệ thống chính": "system_name",
    },
}

# ``###`` subsection header → label → field (scoped under current ``##`` section).
_SUBSECTION_BULLET_FIELDS: dict[str, dict[str, str]] = {
    "Linh Hồn Gốc (Hiện Đại)": {
        "Tên hiện đại": "mc_modern_name",
        "Tuổi hiện đại": "mc_modern_age",
        "Nghề nghiệp hiện đại": "mc_modern_job",
        "Kiến thức chuyên sâu": "mc_modern_knowledge",
        "Lý do chết / Xuyên không": "transmigration_reason",
    },
    "Thân Phận Mới (Cổ Đại)": {
        "Tên mới": "mc_name",
    },
    "Siêu Năng Lực / Dị Năng": {
        "Loại năng lực": "urban_power_type",
        "Giới hạn / Cooldown": "urban_power_limit",
    },
    "MC ↔ System Relationship": {
        "Loại quan hệ": "system_relationship",
    },
    "Quest System": {
        "Reward logic": "quest_reward_logic",
    },
}

# ``### Heading N:`` lines (romance barriers) → field id.
_HEADING_FILLS: dict[str, str] = {
    "Rào cản chính 1": "romance_barrier_1",
    "Rào cản chính 2": "romance_barrier_2",
    "Rào cản chính 3 (nếu có)": "romance_barrier_3",
    "Rào cản chính 3": "romance_barrier_3",
}

_BULLET_RE = re.compile(r"^(- \*\*(.+?):\*\*)(?:\s*)(.*)$")
_HEADING_RE = re.compile(r"^###\s+(.+?):\s*$")
_STYLE_HINT_RE = re.compile(r"^\s+-\s+`")
_OUTPUT_LANG_MARKER = "- **Ngôn ngữ output:**"


def _inject_output_language_line(body: str, label: str) -> str:
    """Ensure genre templates expose prose output language in section I."""
    if not label or _OUTPUT_LANG_MARKER in body:
        return body
    lines = body.splitlines()
    out: list[str] = []
    inserted = False
    for line in lines:
        out.append(line)
        if not inserted and line.startswith("## I."):
            out.append(f"{_OUTPUT_LANG_MARKER} {label}")
            inserted = True
    if not inserted:
        out.insert(0, f"{_OUTPUT_LANG_MARKER} {label}")
    return "\n".join(out)


def _strip_template_shell(raw: str) -> str:
    """Drop the template H1 + YAML frontmatter; return the section body."""
    lines = raw.splitlines()
    idx = 0
    if lines and lines[idx].startswith("# PROJECT_DNA"):
        idx += 1
    if idx < len(lines) and lines[idx].strip() == "---":
        idx += 1
        while idx < len(lines) and lines[idx].strip() != "---":
            idx += 1
        if idx < len(lines):
            idx += 1
    return "\n".join(lines[idx:]).lstrip("\n")


def genre_template_path(genre: str) -> Optional[Path]:
    """Return the on-disk genre template, or ``None`` if unavailable."""
    slug = (genre or "").strip().lower().replace(" ", "_")
    if slug == "sci_fi":
        slug = "scifi"
    fname = GENRE_TEMPLATE_FILE.get(slug)
    if not fname:
        return None
    path = _GENRE_TEMPLATES_DIR / fname
    return path if path.is_file() else None


def genre_template_relpath(genre: str) -> Optional[str]:
    path = genre_template_path(genre)
    if not path:
        return None
    try:
        return str(path.relative_to(_PACKAGE_ROOT))
    except ValueError:
        return str(path)


def render_from_genre_template(
    fields: dict[str, Any],
    *,
    g: Callable[[dict[str, Any], str, str], str],
    build_frontmatter: Callable[[dict[str, Any]], list[str]],
    build_preflight: Callable[[dict[str, Any]], str],
) -> str:
    """Fill a per-genre PROJECT_DNA template from form ``fields``."""
    from .dna_form import resolve_genre

    # Strict: this function picks a template FILE from the genre, so guessing here
    # would render a xianxia document for a novel of a different genre. An
    # unresolvable genre must surface as the FileNotFoundError below instead.
    # Strict: this function picks a genre-SPECIFIC template file, so guessing a
    # genre here would silently render the wrong document. Reported as
    # FileNotFoundError to keep this function's existing contract.
    try:
        genre = resolve_genre(fields, where="dna_genre_render", strict=True)
    except ValueError as exc:
        raise FileNotFoundError(str(exc)) from exc
    title = g(fields, "title") or "Tác phẩm chưa đặt tên"
    template_path = genre_template_path(genre)
    if not template_path:
        raise FileNotFoundError(f"No genre template for {genre!r}")

    raw = template_path.read_text(encoding="utf-8")
    fm = "\n".join(build_frontmatter(fields)) + "\n"
    body = _strip_template_shell(raw)
    body = _fill_body(body, fields, genre, g)
    body = _inject_output_language_line(body, g(fields, "output_language_label"))
    preflight = build_preflight(fields)
    return (
        fm
        + "\n"
        + f"# PROJECT_DNA.md — {title}\n\n"
        + body.rstrip()
        + "\n\n"
        + preflight
        + "\n"
    )


def _fill_body(
    body: str,
    fields: dict[str, Any],
    genre: str,
    g: Callable[[dict[str, Any], str, str], str],
) -> str:
    section = ""
    subsection = ""
    skip_style_hints = False
    out: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            subsection = ""
            skip_style_hints = False
            out.append(line)
            continue

        if line.startswith("### "):
            heading_match = _HEADING_RE.match(line)
            if heading_match:
                heading = heading_match.group(1).strip()
                field_id = _HEADING_FILLS.get(heading)
                value = g(fields, field_id) if field_id else ""
                if value:
                    out.append(f"### {heading}: {value}")
                else:
                    out.append(line)
                subsection = heading
                skip_style_hints = False
                continue
            subsection = line[4:].strip().rstrip(":")
            skip_style_hints = False
            out.append(line)
            if "Công Nghệ Cốt Lõi" in subsection:
                tech = g(fields, "scifi_tech_core")
                if tech:
                    out.append(f"- **Tổng quan công nghệ:** {tech}")
            continue

        if skip_style_hints and _STYLE_HINT_RE.match(line):
            continue

        match = _BULLET_RE.match(line)
        if not match:
            out.append(line)
            continue

        prefix, label, _rest = match.groups()
        label = label.strip()
        field_id = _field_for_label(section, subsection, label)
        value = g(fields, field_id) if field_id else ""
        if label == "Mã Đại Thần" and value:
            out.append(f"{prefix} {value}")
            skip_style_hints = True
            continue
        if value:
            out.append(f"{prefix} {value}")
        else:
            out.append(line)
        skip_style_hints = False

    words = g(fields, "target_words_per_chapter", "2500") or "2500"
    text = "\n".join(out)
    text = re.sub(
        r"(Số từ/chương:\s*)\d+",
        rf"\g<1>{words}",
        text,
    )
    return text


def _field_for_label(section: str, subsection: str, label: str) -> Optional[str]:
    if subsection:
        for sub_key, mapping in _SUBSECTION_BULLET_FIELDS.items():
            if sub_key in subsection and label in mapping:
                return mapping[label]
    for sec_key, mapping in _SECTION_BULLET_FIELDS.items():
        if sec_key in section and label in mapping:
            return mapping[label]
    return _GLOBAL_BULLET_FIELDS.get(label)
