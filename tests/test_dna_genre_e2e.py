"""End-to-end matrix tests for per-genre PROJECT_DNA template wiring.

Exercises the full HTTP create → disk → detail path for every Studio genre,
hybrid fallback, routing metadata, field injection, and re-render stability.
"""

from __future__ import annotations

import importlib
import json
import re
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from webapp.api import dna_form
from webapp.api.dna_genre_render import GENRE_TEMPLATE_FILE, genre_template_path

# Signature section each genre template must preserve (proves correct skeleton).
GENRE_SIGNATURE_SECTION: dict[str, str] = {
    "xianxia": "## VI. THẾ GIỚI TU CHÂN",
    "urban": "## VI. THẾ GIỚI ĐÔ THỊ",
    "romance": "## V. RÀO CẢN TÌNH YÊU",
    "scifi": "## VI. THẾ GIỚI KHOA HUYỄN",
    "time_travel": "## IV. CƠ CHẾ XUYÊN KHÔNG",
    "meta_genre": "## IV. HỆ THỐNG (QUAN TRỌNG NHẤT)",
}

GENRE_SQUAD: dict[str, str] = {
    "xianxia": "sub_agents",
    "urban": "sub_agents_do_thi",
    "romance": "sub_agents_ngon_tinh",
    "scifi": "sub_agents_khoa_huyen",
    "time_travel": "sub_agents_xuyen_khong",
    "meta_genre": "sub_agents_he_thong",
}

GENRE_CANON: dict[str, str] = {
    "xianxia": "system/Xianxia",
    "urban": "system/Urban",
    "romance": "system/Romance",
    "scifi": "system/Sci-fi",
    "time_travel": "system/Time Travel",
    "meta_genre": "system/Meta Genre",
}

HYBRID_PAIRS = [
    ("xianxia", "urban"),
    ("romance", "time_travel"),
    ("meta_genre", "scifi"),
]


@pytest.fixture()
def client(monkeypatch):
    storage = tempfile.mkdtemp()
    monkeypatch.setenv("NOVELKIT_AUTH", "off")
    monkeypatch.setenv("NOVELKIT_STORAGE_ROOT", storage)
    monkeypatch.setenv("NOVELKIT_WORKSPACE_ROOT", tempfile.mkdtemp())
    import webapp.api.deps as deps
    import webapp.api.novel_paths as novel_paths
    import webapp.api.service as service
    import webapp.api.main as main

    importlib.reload(deps)
    importlib.reload(novel_paths)
    importlib.reload(service)
    importlib.reload(main)
    return TestClient(main.app), Path(storage)


def _rich_fields(genre: str) -> dict:
    """Form payload exercising cross-template field mappings."""
    style = (dna_form.STYLE_BY_GENRE.get(genre) or [{}])[0].get("value", "")
    base = {
        "title": f"E2E {genre}",
        "genre": genre,
        "logline": f"Logline thử nghiệm cho {genre}.",
        "usp": "USP thử nghiệm.",
        "theme": "Chủ đề thử.",
        "audience": "Độc giả 18+",
        "tone": "bi tráng",
        "style_model": style,
        "worldbuilding_guide": style,
        "mc_name": "Lâm Phong",
        "mc_archetype": "Nghịch mệnh",
        "mc_traits": "Lạnh lùng",
        "mc_motivation": "Tìm lại người thân",
        "mc_want": "Báo thù",
        "mc_need": "Học cách tin người",
        "mc_ghost": "Mất gia đình",
        "mc_lie": "Chỉ sức mạnh mới cứu được mọi thứ",
        "mc_voice": "Ít lời",
        "antagonist_name": "Hắc Ảnh",
        "antagonist_traits": "Lý tính",
        "antagonist_conflict": "Tranh đoạt quyền lực",
        "villain_want": "Kiểm soát thế giới",
        "villain_human_moment": "Nhớ mẹ",
        "villain_justified": "Bảo vệ loài mình",
        "hook_strategy": "Mở giữa truy sát",
        "cultivation_speed": "slow",
        "cultivation_age_benchmarks": "51 tuổi → Trúc Cơ",
        "artifact": "Kiếm cổ",
        "spirit_beast": "Hồ ly bạc",
        "supporting_cast": "A; B; C",
        "cast_love_interest": "Hàn Mặc",
        "cast_mentor": "Lão đạo",
        "cast_allies": "Huynh đệ A",
        "world_name": "Cửu Vực",
        "world_era": "Cổ đại",
        "world_mindset": "Tu tiên vi nghịch",
        "world_secret": "Thiên đạo chết",
        "world_locations": "A; B; C",
        "system_name": "Cửu Chuyển",
        "system_tiers": "L1 → L9",
        "system_cost": "Mất thọ",
        "system_bottleneck": "Linh khí",
        "system_golden_finger": "Panel",
        "system_golden_finger_limit": "Cooldown 24h",
        "inciting_incident": "Tai nạn",
        "midpoint_twist": "Thân phận lật",
        "all_is_lost": "Mất hết",
        "climax": "Đại chiến",
        "ending_style": "HE",
        "target_chapters": 12,
        "target_words_per_chapter": 3000,
        "arc_count": 3,
    }
    extras: dict[str, dict] = {
        "xianxia": {
            "mc_age_foundation": "16 tuổi phế mạch",
            "mc_spirit_root": "Hỗn Độn",
            "mc_starting_realm": "Luyện Khí",
            "main_cultivation_method": "Hỗn Nguyên Công",
        },
        "urban": {
            "mc_age": "28",
            "mc_occupation": "CEO",
            "mc_secret": "Dị năng ẩn",
            "urban_power_type": "Điện từ",
            "urban_power_limit": "Cooldown 6h",
        },
        "romance": {
            "mc_age": "24",
            "love_interest_secret": "Hôn nhân giả",
            "romance_barrier_1": "Gia đình phản đối",
            "romance_barrier_2": "Hiểu lầm lớn",
            "romance_barrier_3": "Tình địch",
        },
        "scifi": {
            "mc_age": "32",
            "mc_occupation": "Phi hành gia",
            "antagonist_codename": "NEXUS-7",
            "antagonist_threat": "Thu hoạch nhân loại",
            "scifi_tech_core": "Warp drive + AGI",
        },
        "time_travel": {
            "mc_modern_name": "Trương Vũ",
            "mc_modern_age": "30",
            "mc_modern_job": "Kỹ sư",
            "mc_modern_knowledge": "Kinh tế học",
            "transmigration_reason": "Tai nạn xe",
            "transmigration_type": "trọng sinh",
        },
        "meta_genre": {
            "system_ui_type": "Panel UI",
            "system_origin": "Trời ban",
            "system_relationship": "Hợp tác",
            "quest_reward_logic": "XP + skill unlock",
        },
    }
    base.update(extras.get(genre, {}))
    return base


def _parse_frontmatter(dna: str) -> dict[str, str]:
    if not dna.startswith("---"):
        return {}
    end = dna.find("\n---", 3)
    block = dna[3:end]
    out: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


@pytest.mark.parametrize("genre", dna_form.GENRES)
def test_e2e_create_single_genre_uses_genre_template(client, genre: str):
    api, storage = client
    fields = _rich_fields(genre)
    slug = f"e2e_{genre}"
    r = api.post("/api/novels", json={"name": slug, "fields": fields})
    assert r.status_code == 201, r.text

    dna = api.get(f"/api/novels/{slug}").json()["dna"]
    fm = _parse_frontmatter(dna)
    expected_tpl = f"skills/novelkit-canon/templates/genres/{GENRE_TEMPLATE_FILE[genre]}"

    assert fm.get("genre") == genre
    assert fm.get("template_source") == expected_tpl
    assert fm.get("sub_agents_squad") == GENRE_SQUAD[genre]
    assert fm.get("canon_pack") == GENRE_CANON[genre]
    assert GENRE_SIGNATURE_SECTION[genre] in dna
    assert "## XII. SỔ KIỂM KHỞI TẠO" in dna
    assert f"# PROJECT_DNA.md — E2E {genre}" in dna
    assert f"- **Tên tác phẩm:** E2E {genre}" in dna
    assert f"- **Logline (1 câu):** Logline thử nghiệm cho {genre}." in dna

    # Unified 14-section layout must NOT appear for single genre.
    assert "## II. THỂ LOẠI & ROUTING" not in dna

    # Sidecars written beside PROJECT_DNA on disk (owner-scoped storage).
    novel_dirs = list(storage.rglob("PROJECT_DNA.fields.json"))
    assert novel_dirs, "PROJECT_DNA.fields.json not written"
    fields_path = next(p for p in novel_dirs if p.parent.name)  # any match
    for p in novel_dirs:
        if json.loads(p.read_text()).get("genre") == genre:
            fields_path = p
            break
    sidecar = json.loads(fields_path.read_text())
    assert sidecar["genre"] == genre
    meta = json.loads(fields_path.with_name("PROJECT_DNA.meta.json").read_text())
    assert meta["sub_agents_squad"] == GENRE_SQUAD[genre]


@pytest.mark.parametrize("primary,secondary", HYBRID_PAIRS)
def test_e2e_hybrid_uses_unified_template(client, primary: str, secondary: str):
    api, _storage = client
    fields = {**_rich_fields(primary), "genre_secondary": secondary, "hybrid_ratio": "70-30"}
    slug = f"e2e_hybrid_{primary}_{secondary}"
    r = api.post("/api/novels", json={"name": slug, "fields": fields})
    assert r.status_code == 201, r.text

    dna = api.get(f"/api/novels/{slug}").json()["dna"]
    fm = _parse_frontmatter(dna)
    assert fm.get("genre") == "hybrid"
    assert fm.get("template_source") == "templates/PROJECT_DNA_TEMPLATE.md"
    assert "## II. THỂ LOẠI & ROUTING" in dna
    assert "## XIII. SỔ KIỂM KHỞI TẠO" in dna
    assert GENRE_SIGNATURE_SECTION[primary] not in dna


def test_e2e_schema_exposes_all_genre_template_paths(client):
    api, _ = client
    sch = api.get("/api/dna-template").json()
    for genre in dna_form.GENRES:
        rel = sch["genre_template_files"][genre]
        assert rel.endswith(GENRE_TEMPLATE_FILE[genre])
        assert genre_template_path(genre) is not None


def test_e2e_rerender_after_field_merge_matches_create(client):
    """Simulate enrich merge: re-render must keep genre skeleton."""
    api, _ = client
    base = _rich_fields("romance")
    slug = "e2e_rerender_romance"
    api.post("/api/novels", json={"name": slug, "fields": base})
    merged = {**base, "cast_love_interest": "Nam chính đổi tên"}
    rerendered = dna_form.render_project_dna(merged)
    assert "## III. NỮ CHÍNH" in rerendered
    assert "- **Tên:** Lâm Phong" in rerendered
    assert "Nam chính đổi tên" in rerendered


def test_e2e_field_fill_coverage_audit():
    """Report how many mapped bullets receive values for a fully-filled form."""
    from webapp.api.dna_genre_render import _BULLET_RE, _field_for_label, _strip_template_shell

    for genre in dna_form.GENRES:
        raw = genre_template_path(genre).read_text(encoding="utf-8")
        body = _strip_template_shell(raw)
        fields = _rich_fields(genre)
        section = ""
        subsection = ""
        mapped = filled = unmapped = 0
        for line in body.splitlines():
            if line.startswith("## "):
                section = line[3:].strip()
                subsection = ""
                continue
            if line.startswith("### "):
                subsection = line[4:].strip().rstrip(":")
                continue
            m = _BULLET_RE.match(line)
            if not m:
                continue
            label = m.group(2).strip()
            fid = _field_for_label(section, subsection, label)
            if fid:
                mapped += 1
                if dna_form._g(fields, fid):
                    filled += 1
            else:
                unmapped += 1
        # At least seed + MC + plot bullets should map and fill.
        assert mapped >= 10, genre
        assert filled >= 15, f"{genre}: only {filled}/{mapped} mapped bullets filled"
        # Genre templates intentionally have many craft-only bullets without form ids.
        assert unmapped >= 5, genre


def test_e2e_logline_placeholder_cleared_when_provided():
    fields = _rich_fields("xianxia")
    out = dna_form.render_project_dna(fields)
    assert "_[Nhân vật] phải" not in out.split("- **Logline")[1].split("\n")[0]


def test_e2e_target_words_per_chapter_stamped_in_footer():
    fields = _rich_fields("urban")
    out = dna_form.render_project_dna(fields)
    assert "Số từ/chương: 3000" in out


def test_schema_exposes_genre_sections_and_extended_canon():
    s = dna_form.schema()
    assert "genre_sections" in s
    assert set(s["genre_sections"]) == set(dna_form.GENRES)
    for genre in dna_form.GENRES:
        assert len(s["genre_sections"][genre]) >= 1
    assert "extended_canon_genres" in s
    assert len(s["extended_canon_genres"]) >= 5
    xianxia_ids = {f["id"] for sec in s["genre_sections"]["xianxia"] for f in sec["fields"]}
    assert "mc_spirit_root" in xianxia_ids
    assert "romance_barrier_1" in {
        f["id"] for sec in s["genre_sections"]["romance"] for f in sec["fields"]
    }

    fields = {**_rich_fields("urban"), "target_words_per_chapter": 4200}
    out = dna_form.render_project_dna(fields)
    assert "Số từ/chương: 4200" in out
