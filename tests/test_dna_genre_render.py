"""Tests for per-genre PROJECT_DNA template rendering."""

from __future__ import annotations

from webapp.api import dna_form
from webapp.api.dna_genre_render import genre_template_path, render_from_genre_template


def test_genre_template_paths_exist() -> None:
    for genre in dna_form.GENRES:
        assert genre_template_path(genre) is not None


def test_render_xianxia_fills_seed_fields() -> None:
    fields = {
        "title": "Thí Đề",
        "genre": "xianxia",
        "logline": "Một kiếm tu phải trả thù.",
        "usp": "Ký ức làm fuel tu luyện.",
        "target_chapters": "30",
        "target_words_per_chapter": "2500",
    }
    out = dna_form.render_project_dna(fields)
    assert "template_source: skills/novelkit-canon/templates/genres/PROJECT_DNA_XIANXIA.md" in out
    assert "## III. NHÂN VẬT CHÍNH (Tu Sĩ)" in out
    assert "- **Tên tác phẩm:** Thí Đề" in out
    assert "- **Logline (1 câu):** Một kiếm tu phải trả thù." in out
    assert "- **Dấu riêng (USP):** Ký ức làm fuel tu luyện." in out


def test_render_romance_uses_romance_template() -> None:
    fields = {
        "title": "Hoa Rơi",
        "genre": "romance",
        "logline": "Cô phải chọn tình yêu.",
        "target_chapters": "20",
        "style_model": "CM",
        "mc_name": "Lâm Tuyết",
        "cast_love_interest": "Hàn Mặc",
        "romance_barrier_1": "Gia đình phản đối",
        "romance_barrier_2": "Hiểu lầm",
        "romance_barrier_3": "Tình địch",
    }
    out = dna_form.render_project_dna(fields)
    assert "PROJECT_DNA_ROMANCE.md" in out
    assert "## III. NỮ CHÍNH" in out
    assert "## IV. NAM CHÍNH" in out
    assert "### Rào cản chính 1: Gia đình phản đối" in out
    assert "- **Mã Đại Thần:** CM" in out
    assert "`CM` Cố Mạn" not in out


def test_render_scifi_antagonist_codename() -> None:
    fields = {
        "title": "Sao Xa",
        "genre": "scifi",
        "logline": "Liên bang đối đầu AI.",
        "target_chapters": "10",
        "antagonist_codename": "NEXUS-7",
        "antagonist_threat": "Thu hoạch loài người",
        "scifi_tech_core": "Warp + AGI",
    }
    out = dna_form.render_project_dna(fields)
    assert "- **Tên / Mã danh:** NEXUS-7" in out
    assert "- **Mục tiêu:** Thu hoạch loài người" in out
    assert "- **Tổng quan công nghệ:** Warp + AGI" in out


def test_render_time_travel_modern_identity() -> None:
    fields = {
        "title": "Xuyên Cổ",
        "genre": "time_travel",
        "logline": "Kỹ sư xuyên không.",
        "target_chapters": "10",
        "mc_modern_name": "Trương Vũ",
        "mc_modern_age": "30",
        "mc_modern_job": "Kỹ sư",
        "transmigration_type": "trọng sinh",
    }
    out = dna_form.render_project_dna(fields)
    assert "- **Tên hiện đại:** Trương Vũ" in out
    assert "- **Loại xuyên không:** trọng sinh" in out


def test_render_xianxia_spirit_root() -> None:
    fields = {
        "title": "Linh Căn",
        "genre": "xianxia",
        "logline": "Tu tiên.",
        "target_chapters": "10",
        "mc_spirit_root": "Hỗn Độn",
        "mc_starting_realm": "Luyện Khí",
        "main_cultivation_method": "Hỗn Nguyên Công",
    }
    out = dna_form.render_project_dna(fields)
    assert "- **Linh căn:** Hỗn Độn" in out
    assert "- **Cảnh giới mở đầu:** Luyện Khí" in out
    assert "- **Công pháp chính:** Hỗn Nguyên Công" in out


def test_render_output_language_in_frontmatter_and_body() -> None:
    fields = {
        "title": "English Novel",
        "genre": "urban",
        "logline": "A CEO hides a secret.",
        "target_chapters": "10",
        "output_language": "en",
    }
    out = dna_form.render_project_dna(fields)
    assert "output_language: en" in out
    assert "output_language_label: English" in out
    assert "- **Ngôn ngữ output:** English" in out


def test_render_custom_output_language() -> None:
    fields = {
        "title": "Deutsch",
        "genre": "romance",
        "logline": "Liebe.",
        "target_chapters": "8",
        "output_language": "custom",
        "output_language_custom": "Deutsch",
    }
    out = dna_form.render_project_dna(fields)
    assert "output_language: custom" in out
    assert "output_language_label: Deutsch" in out
    assert "- **Ngôn ngữ output:** Deutsch" in out


def test_hybrid_falls_back_to_unified() -> None:
    fields = {
        "title": "Pha Trộn",
        "genre": "xianxia",
        "genre_secondary": "urban",
        "logline": "Tu tiên trong thành phố.",
        "target_chapters": "10",
    }
    out = dna_form.render_project_dna(fields)
    assert "template_source: templates/PROJECT_DNA_TEMPLATE.md" in out
    assert "## II. THỂ LOẠI & ROUTING" in out


def test_render_from_genre_template_requires_file() -> None:
    try:
        render_from_genre_template(
            {"genre": "not_a_real_genre", "title": "X"},
            g=dna_form._g,
            build_frontmatter=dna_form._build_frontmatter_lines,
            build_preflight=lambda f: dna_form._build_preflight_section(f, section_number="XII"),
        )
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected FileNotFoundError for unknown genre")
