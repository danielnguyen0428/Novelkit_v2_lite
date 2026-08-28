"""Canon bundle structural checks (post-migration).

Verifies the shipped ``skills/novelkit-canon`` and ``subagents`` trees contain
the creative assets the runtime depends on. Byte-for-byte reconciliation against
``_novelkit_source`` is no longer required once migration is complete.
"""

from __future__ import annotations

import json
from pathlib import Path

from migration.inventory import PACKAGE_ROOT

_CANON = PACKAGE_ROOT / "skills" / "novelkit-canon"
_SUBAGENTS = PACKAGE_ROOT / "subagents"

_EXPECTED_PACKS = {
    "Apocalypse", "Cthulhu", "Dark Theme", "Many Children", "Meta Genre",
    "Romance", "Rules Horror", "Sci-fi", "Short Form", "StoryDepth",
    "Streaming", "Substitute", "Time Travel", "Urban", "War Espionage",
    "Xianxia", "eSports",
}


def test_canon_bundle_manifest_present_and_valid():
    skill_md = _CANON / "SKILL.md"
    meta_json = _CANON / "_meta.json"
    assert skill_md.is_file(), "skills/novelkit-canon/SKILL.md missing"
    assert meta_json.is_file(), "skills/novelkit-canon/_meta.json missing"
    meta = json.loads(meta_json.read_text(encoding="utf-8"))
    assert meta["slug"] == "novelkit-canon"
    assert set(meta["genrePacks"]) == _EXPECTED_PACKS


def test_all_17_genre_packs_present():
    sys_dir = _CANON / "canon" / "system"
    packs = {p.name for p in sys_dir.iterdir() if p.is_dir()}
    assert packs == _EXPECTED_PACKS
    assert len(packs) == 17


def test_storydepth_field_execution_preserved():
    field_exec = _CANON / "canon" / "system" / "StoryDepth" / "CREATE_NOVEL_FIELD_EXECUTION.md"
    assert field_exec.is_file(), "StoryDepth CREATE_NOVEL_FIELD_EXECUTION.md missing"
    assert field_exec.stat().st_size > 100


def test_xianxia_core_modules_preserved():
    xianxia = _CANON / "canon" / "system" / "Xianxia"
    names = " ".join(p.name for p in xianxia.rglob("*.md"))
    for needle in ("Progression", "World", "Texture", "Worldbuilding"):
        assert needle in names, f"Xianxia module missing: {needle}"


def test_vocabulary_whitelists_preserved():
    vocab = list((_CANON / "canon" / "system").rglob("vocabulary.txt"))
    assert vocab, "expected at least one vocabulary.txt in canon"


def test_templates_present():
    dst_count = sum(1 for p in (_CANON / "templates").rglob("*") if p.is_file())
    assert dst_count > 0


def test_standard_docs_migrated():
    docs = _CANON / "docs"
    for name in ("STYLE_GUIDE.md", "CONTRACTS.md", "API.md", "IDENTITY.md", "RUNBOOK.md"):
        assert (docs / name).is_file(), f"standard doc missing: {name}"


def test_all_soul_files_present():
    souls = list(_SUBAGENTS.rglob("SOUL.md"))
    assert len(souls) == 31, f"expected 31 SOUL.md (30 specialists + orchestrator), got {len(souls)}"


def test_orchestrator_soul_present():
    assert (_SUBAGENTS / "orchestrator" / "SOUL.md").is_file()


def test_six_specialist_squads_with_five_roles_each():
    squads = [d for d in _SUBAGENTS.iterdir()
              if d.is_dir() and d.name.startswith("sub_agents")]
    assert len(squads) == 6
    for squad in squads:
        souls = list(squad.rglob("SOUL.md"))
        assert len(souls) == 5, f"squad {squad.name} should have 5 roles, got {len(souls)}"


def test_squad_map_valid_and_points_at_real_dirs():
    squad_map = json.loads((_SUBAGENTS / "squad_map.json").read_text(encoding="utf-8"))
    families = set(squad_map["valid_squad_families"])
    assert set(squad_map["genre_to_squad"].values()) <= families
    for fam, info in squad_map["squads"].items():
        assert fam in families
        squad_dir = PACKAGE_ROOT / info["dir"]
        assert squad_dir.is_dir(), f"missing squad dir: {info['dir']}"
        for role in info["roles"]:
            assert (squad_dir / role / "SOUL.md").is_file(), f"missing {fam}/{role}/SOUL.md"
    assert (PACKAGE_ROOT / squad_map["orchestrator"]["soul"]).is_file()
