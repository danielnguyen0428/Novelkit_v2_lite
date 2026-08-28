"""Tests for the Phase 0 migration inventory (Requirement 1).

Covers Property 10 (migration completeness): every creative-knowledge /
creative-config file maps to *exactly one* target artifact — no orphans.

    **Validates: Requirements 1.1**

Includes unit tests for concrete classification examples + edge cases, and a
Hypothesis property test that exercises the classifier across the path input
space to prove the must-keep <-> single-target invariant holds universally.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from migration import inventory
from migration.inventory import (
    Category,
    DEFAULT_SOURCE_ROOT,
    MappingStatus,
    MUST_KEEP_CATEGORIES,
    build_inventory,
    classify,
    find_orphans,
    load_baseline,
    must_keep_records,
    scan,
)

_SOURCE_AVAILABLE = DEFAULT_SOURCE_ROOT.is_dir()

# --------------------------------------------------------------------------- #
# Smart path generator: realistic NovelKit-style relative paths.
# --------------------------------------------------------------------------- #

_TOP_DIRS = [
    "system", "templates", ".creative_refs", "config", "scripts", "SKILL",
    "sub_agents", "sub_agents_do_thi", "sub_agents_he_thong",
    "sub_agents_khoa_huyen", "sub_agents_ngon_tinh", "sub_agents_xuyen_khong",
    "novels", "tests", "logs", "state", "database", "memory",
    ".rag", ".openclaw", ".test_artifacts", "docs",
]

_LEAF_NAMES = [
    "SOUL.md", "HEARTBEAT.md", "TOOLS.md", "SKILL.md", "_meta.json",
    "STYLE_GUIDE.md", "CONTRACTS.md", "API.md", "RUNBOOK.md", "IDENTITY.md",
    "GLOSSARY.md", "app.js", "Dockerfile", "README.md", "MEMORY.md",
    "ai_flavor_patterns.json", "account_tiers.json", "xianxia_language_guard.json",
    "control_plane.py", "ai_flavor_detector.py", "dispatcher_adapter.py",
    "vocabulary.txt", "creative_input_bundle.md", "chapter.0001.md",
]

_segment = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_.-",
    min_size=1,
    max_size=12,
).filter(lambda s: s not in {".", ".."})


@st.composite
def relative_paths(draw):
    """Generate plausible source-relative paths, biased toward real shapes."""
    top = draw(st.sampled_from(_TOP_DIRS) | _segment)
    mids = draw(st.lists(_segment, min_size=0, max_size=4))
    leaf = draw(st.sampled_from(_LEAF_NAMES) | _segment)
    return "/".join([top, *mids, leaf])


# --------------------------------------------------------------------------- #
# Property: classify is total, deterministic, and obeys the must-keep contract.
# --------------------------------------------------------------------------- #


@settings(max_examples=400)
@given(relative_paths())
def test_property_classify_must_keep_has_exactly_one_target(rel_path):
    """P10: a must-keep file always resolves to exactly one non-empty target.

    **Validates: Requirements 1.1**
    """
    category, status, target, must_keep, _note = classify(rel_path)

    # Total & well-typed.
    assert isinstance(category, Category)
    assert isinstance(status, MappingStatus)

    # must_keep is exactly the creative categories.
    assert must_keep == (category in MUST_KEEP_CATEGORIES)

    if must_keep:
        # Exactly one target: a single, non-empty path string.
        assert isinstance(target, str) and target.strip()
        assert "\n" not in target
        # Must-keep is never marked as removed legacy.
        assert status != MappingStatus.REMOVED_LEGACY
    else:
        # Non creative-asset files are never silently flagged must-keep.
        assert category in {Category.BUSINESS_LOGIC, Category.LEGACY_INFRA}


@settings(max_examples=200)
@given(relative_paths())
def test_property_classify_is_deterministic(rel_path):
    """Classification must be stable for a given path.

    **Validates: Requirements 1.1**
    """
    assert classify(rel_path) == classify(rel_path)


# --------------------------------------------------------------------------- #
# Property over the real scan: no orphans, full coverage.
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(not _SOURCE_AVAILABLE, reason="_novelkit_source archive not present")
def test_real_scan_has_no_orphans():
    """Every must-keep file in the live inventory has a target (no orphan)."""
    records = scan()
    orphans = find_orphans(records)
    assert orphans == [], f"orphan must-keep files: {[o.path for o in orphans]}"


@pytest.mark.skipif(not _SOURCE_AVAILABLE, reason="_novelkit_source archive not present")
def test_real_scan_must_keep_targets_are_unique_and_single():
    """Each must-keep source maps to one target; targets do not collide."""
    records = scan()
    mk = must_keep_records(records)
    targets = [r.target for r in mk]
    assert all(t for t in targets)
    assert len(targets) == len(set(targets)), "must-keep targets must be distinct"


@pytest.mark.skipif(not _SOURCE_AVAILABLE, reason="_novelkit_source archive not present")
def test_inventory_coverage_complete():
    inv = build_inventory()
    assert inv["summary"]["orphan_count"] == 0
    assert inv["summary"]["coverage_complete"] is True
    assert inv["summary"]["must_keep_count"] > 0


# --------------------------------------------------------------------------- #
# Baseline freeze guard (Task 1.2): live scan must still satisfy the contract.
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(not _SOURCE_AVAILABLE, reason="_novelkit_source archive not present")
def test_frozen_baseline_matches_live_scan():
    """The frozen must-keep set is reproducible from a fresh scan.

    Guards against accidental drops of creative assets after freeze.
    """
    baseline = load_baseline()
    frozen = {r["path"] for r in baseline["must_keep"]}
    live = {r.path for r in must_keep_records(scan())}
    missing = frozen - live
    added = live - frozen
    assert not missing, f"creative assets dropped since freeze: {sorted(missing)}"
    assert not added, f"new must-keep assets not in frozen baseline: {sorted(added)}"


@pytest.mark.skipif(not _SOURCE_AVAILABLE, reason="_novelkit_source archive not present")
def test_frozen_baseline_every_entry_has_single_target():
    baseline = load_baseline()
    for entry in baseline["must_keep"]:
        assert entry["target"], f"frozen orphan: {entry['path']}"


# --------------------------------------------------------------------------- #
# Unit tests: concrete classification examples + edge cases.
# --------------------------------------------------------------------------- #


def test_genre_canon_is_creative_knowledge():
    cat, status, target, mk, _ = classify("system/Xianxia/Cultivation_Progression_System.md")
    assert cat == Category.CREATIVE_KNOWLEDGE
    assert status == MappingStatus.KEPT
    assert target.startswith("skills/novelkit-canon/canon/system/")
    assert mk is True


def test_orchestrator_soul_root():
    cat, _s, target, mk, _ = classify("SOUL.md")
    assert cat == Category.CREATIVE_KNOWLEDGE
    assert target == "subagents/orchestrator/SOUL.md"
    assert mk is True


def test_specialist_soul():
    cat, _s, target, mk, _ = classify("sub_agents_ngon_tinh/hong_nhan/SOUL.md")
    assert cat == Category.CREATIVE_KNOWLEDGE
    assert target == "subagents/sub_agents_ngon_tinh/hong_nhan/SOUL.md"
    assert mk is True


def test_xianxia_guard_config_standardized():
    cat, _s, target, mk, _ = classify("config/xianxia_language_guard.json")
    assert cat == Category.CREATIVE_CONFIG
    assert target == "config/language_guard/xianxia.json"
    assert mk is True


def test_account_tiers_config_is_legacy():
    cat, status, target, mk, _ = classify("config/account_tiers.json")
    assert cat == Category.LEGACY_INFRA
    assert status == MappingStatus.REMOVED_LEGACY
    assert target is None
    assert mk is False


def test_business_logic_extracted():
    cat, status, target, mk, _ = classify("scripts/ai_flavor_detector.py")
    assert cat == Category.BUSINESS_LOGIC
    assert status == MappingStatus.EXTRACTED
    assert target == "tools/novelkit_ai_flavor_tool.py"
    assert mk is False


def test_legacy_runner_removed():
    cat, status, target, mk, _ = classify("scripts/dispatcher_adapter.py")
    assert cat == Category.LEGACY_INFRA
    assert status == MappingStatus.REMOVED_LEGACY
    assert mk is False


def test_temp_creative_ref_is_legacy():
    cat, _s, _t, mk, _ = classify(".creative_refs/tmp6ov9ek3f/chapter.0001.write/x.md")
    assert cat == Category.LEGACY_INFRA
    assert mk is False


def test_real_creative_ref_kept():
    cat, _s, target, mk, _ = classify(".creative_refs/ta_de_van_tam/bootstrap.world/creative_input_bundle.md")
    assert cat == Category.CREATIVE_KNOWLEDGE
    assert target.startswith("skills/novelkit-canon/creative_refs/")
    assert mk is True


def test_novels_data_out_of_scope():
    cat, status, _t, mk, _ = classify("novels/some_novel/chapters/0001.md")
    assert cat == Category.LEGACY_INFRA
    assert status == MappingStatus.REMOVED_LEGACY
    assert mk is False


def test_persona_skill_dedup_is_legacy():
    cat, _s, _t, mk, _ = classify("sub_agents_do_thi/bo_cuc/SKILL/self-improving-agent-3.0.11/SKILL.md")
    assert cat == Category.LEGACY_INFRA
    assert mk is False
