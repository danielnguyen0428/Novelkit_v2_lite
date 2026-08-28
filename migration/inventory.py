"""Phase 0 migration inventory scanner.

Walks ``_novelkit_source/`` and classifies every file into one of four
categories required by Requirement 1.2:

    - creative-knowledge   (the "brain": canon, personas, templates, docs)
    - creative-config      (tunable creative data: pattern/marker/whitelist json)
    - business-logic       (algorithms to extract into Hermes Custom Tools/plugins)
    - legacy-infra          (old tech skeleton + runtime data, removed)

Each record also carries a *mapping status* (kept / extracted / removed-legacy)
and, for everything that must survive the migration, a concrete **target
artifact** in the ``novelkit-hermes/`` package. Files classified as
creative-knowledge or creative-config are flagged ``must_keep`` and MUST map to
exactly one target (Requirement 1.3 / Property 10); a must-keep file without a
target is a blocking *orphan*.

The classification is rule based and intentionally transparent so the produced
``migration_inventory.json`` + markdown report are reviewable. The rules are
derived directly from design.md §"Creative Asset Audit & Standardization"
(tables A and B).

Run as a script to (re)generate the inventory artifacts::

    python -m migration.inventory            # writes json + md next to this file
    python -m migration.inventory --freeze   # also refresh the must-keep baseline
"""

from __future__ import annotations

import argparse
import dataclasses
import enum
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

_THIS = Path(__file__).resolve()
MIGRATION_DIR = _THIS.parent
PACKAGE_ROOT = MIGRATION_DIR.parent              # novelkit-hermes/
REPO_ROOT = PACKAGE_ROOT.parent                  # Novelkitv2/
DEFAULT_SOURCE_ROOT = REPO_ROOT / "_novelkit_source"

INVENTORY_JSON = MIGRATION_DIR / "migration_inventory.json"
INVENTORY_MD = MIGRATION_DIR / "migration_inventory.md"
BASELINE_JSON = MIGRATION_DIR / "must_keep_baseline.json"

# Files/dirs that are pure build noise and never inventoried.
_EXCLUDED_DIR_NAMES = {"__pycache__", ".git", ".DS_Store"}
_EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


# --------------------------------------------------------------------------- #
# Taxonomy
# --------------------------------------------------------------------------- #


class Category(str, enum.Enum):
    CREATIVE_KNOWLEDGE = "creative-knowledge"
    CREATIVE_CONFIG = "creative-config"
    BUSINESS_LOGIC = "business-logic"
    LEGACY_INFRA = "legacy-infra"


class MappingStatus(str, enum.Enum):
    KEPT = "kept"
    EXTRACTED = "extracted"
    REMOVED_LEGACY = "removed-legacy"


MUST_KEEP_CATEGORIES = {Category.CREATIVE_KNOWLEDGE, Category.CREATIVE_CONFIG}


@dataclasses.dataclass(frozen=True)
class FileRecord:
    """One inventoried source file and its migration verdict."""

    path: str                       # POSIX path relative to source root
    category: Category
    mapping_status: MappingStatus
    target: Optional[str]           # target artifact in novelkit-hermes/, or None
    must_keep: bool
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "category": self.category.value,
            "mapping_status": self.mapping_status.value,
            "target": self.target,
            "must_keep": self.must_keep,
            "note": self.note,
        }


# --------------------------------------------------------------------------- #
# Classification rules
# --------------------------------------------------------------------------- #

# Standard creative documents kept at workspace root (Requirement 4.2).
_KEEP_ROOT_DOCS = {
    "STYLE_GUIDE.md": "skills/novelkit-canon/docs/STYLE_GUIDE.md",
    "CONTRACTS.md": "skills/novelkit-canon/docs/CONTRACTS.md",
    "API.md": "skills/novelkit-canon/docs/API.md",
    "RUNBOOK.md": "skills/novelkit-canon/docs/RUNBOOK.md",
    "GLOSSARY.md": "skills/novelkit-canon/docs/GLOSSARY.md",
    "IDENTITY.md": "skills/novelkit-canon/docs/IDENTITY.md",
}

# Creative-config json kept/standardized under config/ (design §A).
_KEEP_CONFIG = {
    "config/ai_flavor_patterns.json": "config/ai_flavor_patterns.json",
    "config/cool_point_markers.json": "config/cool_point_markers.json",
    "config/strand_keywords.json": "config/strand_keywords.json",
    "config/genre_aliases.json": "config/genre_aliases.json",
    # D1: xianxia language guard becomes a profile of the unified guard.
    "config/xianxia_language_guard.json": "config/language_guard/xianxia.json",
}

# Business-logic scripts -> extraction target (design §A / §B).
# Anything not listed here that lives under scripts/ falls through to the
# legacy/default rules below.
_BUSINESS_LOGIC_TARGETS = {
    # anti-AI-detection
    "scripts/ai_flavor_detector.py": "tools/novelkit_ai_flavor_tool.py",
    # cool point
    "scripts/cool_point_analyzer.py": "tools/novelkit_cool_point_tool.py",
    # strand weaver / open loops
    "scripts/strand_weaver.py": "tools/novelkit_strand_tool.py",
    "scripts/open_loops.py": "tools/novelkit_strand_tool.py",
    "scripts/migrate_plot_threads_to_loops.py": "tools/novelkit_strand_tool.py",
    # style coherence
    "scripts/style_coherence.py": "tools/novelkit_style_coherence_tool.py",
    # reference deconstructor
    "scripts/reference_deconstructor.py": "tools/novelkit_reference_tool.py",
    "scripts/reference_deconstructor_cli.py": "tools/novelkit_reference_tool.py",
    # gate registry (unify validators + gates + semantic_gates + gate_registry)
    "scripts/validators.py": "tools/novelkit_gate_tool.py",
    "scripts/gate_registry.py": "tools/novelkit_gate_tool.py",
    "scripts/feedback_loop.py": "tools/novelkit_gate_tool.py",
    "scripts/quality_feedback.py": "tools/novelkit_gate_tool.py",
    # language guard (D1 unify genre + xianxia guard)
    "scripts/genre_language_guard.py": "tools/novelkit_language_guard_tool.py",
    "scripts/xianxia_language_guard.py": "tools/novelkit_language_guard_tool.py",
    # DNA tool
    "scripts/enrich_dna.py": "tools/novelkit_dna_tool.py",
    "scripts/project_dna_metadata.py": "tools/novelkit_dna_tool.py",
    "scripts/generate_novel_from_prompt.py": "tools/novelkit_dna_tool.py",
    "scripts/bootstrap_planning_docs.py": "tools/novelkit_dna_tool.py",
    # pipeline DAG / breaker / rolling window / recovery (D2 - extract algorithm)
    "scripts/control_plane.py": "tools/novelkit_pipeline_tool.py",
    "scripts/cp_constants.py": "tools/novelkit_pipeline_tool.py",
    "scripts/cp_genre.py": "tools/novelkit_pipeline_tool.py",
    "scripts/cp_recovery.py": "tools/novelkit_pipeline_tool.py",
    "scripts/cp_status.py": "tools/novelkit_pipeline_tool.py",
    "scripts/cp_sync.py": "tools/novelkit_pipeline_tool.py",
    "scripts/cp_verify.py": "tools/novelkit_pipeline_tool.py",
    "scripts/recovery_orchestrator.py": "tools/novelkit_pipeline_tool.py",
    "scripts/task_output_contracts.py": "tools/novelkit_pipeline_tool.py",
    # sync / memory-commit + doctor
    "scripts/sync_stages.py": "tools/novelkit_sync_tool.py",
    "scripts/chapter_commit.py": "tools/novelkit_sync_tool.py",
    "scripts/chapter_diff.py": "tools/novelkit_sync_tool.py",
    # context-engine plugin (D5 unify retrieval)
    "scripts/rag_context.py": "plugins/context_engine/novelkit_context.py",
    "scripts/vector_db.py": "plugins/context_engine/novelkit_context.py",
    "scripts/graph_index.py": "plugins/context_engine/novelkit_context.py",
    "scripts/reranker.py": "plugins/context_engine/novelkit_context.py",
    "scripts/reranker_doctor.py": "plugins/context_engine/novelkit_context.py",
    "scripts/rrf.py": "plugins/context_engine/novelkit_context.py",
    "scripts/adaptive_context.py": "plugins/context_engine/novelkit_context.py",
    "scripts/rag_sanitizer.py": "plugins/context_engine/novelkit_context.py",
    # memory-provider plugin (D3/D4 unify memory)
    "scripts/agent_memory.py": "plugins/memory/novelkit_memory.py",
    "scripts/memory_bootstrap.py": "plugins/memory/novelkit_memory.py",
    "scripts/memory_compactor.py": "plugins/memory/novelkit_memory.py",
    "scripts/memory_importance.py": "plugins/memory/novelkit_memory.py",
    "scripts/memory_item.py": "plugins/memory/novelkit_memory.py",
    "scripts/memory_pack.py": "plugins/memory/novelkit_memory.py",
    "scripts/memory_render.py": "plugins/memory/novelkit_memory.py",
    "scripts/memory_resilience.py": "plugins/memory/novelkit_memory.py",
    "scripts/memory_rotation.py": "plugins/memory/novelkit_memory.py",
    "scripts/memory_store.py": "plugins/memory/novelkit_memory.py",
    "scripts/memory_writer_v2.py": "plugins/memory/novelkit_memory.py",
    # golden-test tooling -> ported into tests/ (design §A)
    "scripts/release_signoff.py": "tests/",
    "scripts/compare_signoff_golden.py": "tests/",
    "scripts/update_golden_baselines.py": "tests/",
}

# Sub-directory prefixes under scripts/ that are extracted (unified) wholesale.
_BUSINESS_LOGIC_DIR_TARGETS = {
    "scripts/gates/": "tools/novelkit_gate_tool.py",
    "scripts/semantic_gates/": "tools/novelkit_gate_tool.py",
    "scripts/reranker_providers/": "plugins/context_engine/novelkit_context.py",
}


def _posix(rel: Path) -> str:
    return rel.as_posix()


def _is_soul(parts: tuple[str, ...], name: str) -> bool:
    return name == "SOUL.md"


def classify(rel_path: str) -> tuple[Category, MappingStatus, Optional[str], bool, str]:
    """Classify a single source file given its POSIX path relative to the root.

    Returns ``(category, mapping_status, target, must_keep, note)``.
    The order of checks is most-specific-first so explicit mappings win over
    broad directory rules, and the safe default (legacy-infra, flagged for
    review) catches anything unexpected without ever creating a silent
    must-keep orphan.
    """

    p = rel_path
    parts = tuple(p.split("/"))
    top = parts[0]
    name = parts[-1]

    # --- Persona souls (any depth): the 30 specialists + Orchestrator -------- #
    if _is_soul(parts, name):
        if top.startswith("sub_agents"):
            # sub_agents/<role>/SOUL.md  or  sub_agents_<squad>/<role>/SOUL.md
            squad = top
            role = parts[1] if len(parts) >= 3 else "_root"
            target = f"subagents/{squad}/{role}/SOUL.md"
            return (
                Category.CREATIVE_KNOWLEDGE,
                MappingStatus.KEPT,
                target,
                True,
                "Persona soul (system prompt for Hermes subagent).",
            )
        if len(parts) == 1:
            # Workspace-root SOUL.md == Orchestrator (Lãng Khách).
            return (
                Category.CREATIVE_KNOWLEDGE,
                MappingStatus.KEPT,
                "subagents/orchestrator/SOUL.md",
                True,
                "Orchestrator soul (Lãng Khách).",
            )

    # --- Genre canon: system/* (17 packs) + StoryDepth ----------------------- #
    if top == "system":
        return (
            Category.CREATIVE_KNOWLEDGE,
            MappingStatus.KEPT,
            f"skills/novelkit-canon/canon/{p}",
            True,
            "Genre canon / StoryDepth knowledge.",
        )

    # --- Templates ----------------------------------------------------------- #
    if top == "templates":
        return (
            Category.CREATIVE_KNOWLEDGE,
            MappingStatus.KEPT,
            f"skills/novelkit-canon/{p}",
            True,
            "Creative template.",
        )

    # --- Creative reference projects (.creative_refs) ------------------------ #
    if top == ".creative_refs":
        ref = parts[1] if len(parts) >= 2 else ""
        if ref.startswith("tmp"):
            return (
                Category.LEGACY_INFRA,
                MappingStatus.REMOVED_LEGACY,
                None,
                False,
                "Ephemeral scratch dir under .creative_refs (runtime temp).",
            )
        return (
            Category.CREATIVE_KNOWLEDGE,
            MappingStatus.KEPT,
            f"skills/novelkit-canon/creative_refs/{'/'.join(parts[1:])}",
            True,
            "Creative reference bundle.",
        )

    # --- Packaged skills at workspace root (SKILL/*) ------------------------- #
    if top == "SKILL":
        skill_name = parts[1] if len(parts) >= 2 else ""
        is_manifest = name in {"_meta.json", "SKILL.md"}
        category = Category.CREATIVE_CONFIG if is_manifest else Category.CREATIVE_KNOWLEDGE
        return (
            category,
            MappingStatus.KEPT,
            f"skills/{skill_name}/{'/'.join(parts[2:])}" if len(parts) > 2
            else f"skills/{skill_name}/{name}",
            True,
            "Packaged Hermes skill bundle.",
        )

    # --- Per-persona embedded copies (sub_agents*/.../SKILL, HEARTBEAT, TOOLS) #
    if top.startswith("sub_agents"):
        if "SKILL" in parts:
            return (
                Category.LEGACY_INFRA,
                MappingStatus.REMOVED_LEGACY,
                None,
                False,
                "Per-persona duplicate of root SKILL bundle (dedup; keep one copy).",
            )
        if name in {"HEARTBEAT.md", "TOOLS.md"}:
            return (
                Category.LEGACY_INFRA,
                MappingStatus.REMOVED_LEGACY,
                None,
                False,
                "Persona operational doc tied to old runtime (superseded by Hermes).",
            )
        # Any other persona knowledge file: keep alongside the soul.
        squad = top
        role = parts[1] if len(parts) >= 3 else "_root"
        return (
            Category.CREATIVE_KNOWLEDGE,
            MappingStatus.KEPT,
            f"subagents/{squad}/{'/'.join(parts[1:])}",
            True,
            "Persona knowledge file.",
        )

    # --- Standard creative docs at workspace root ---------------------------- #
    if len(parts) == 1 and name in _KEEP_ROOT_DOCS:
        return (
            Category.CREATIVE_KNOWLEDGE,
            MappingStatus.KEPT,
            _KEEP_ROOT_DOCS[name],
            True,
            "Standard creative document.",
        )

    # --- config/ ------------------------------------------------------------- #
    if top == "config":
        if p in _KEEP_CONFIG:
            note = (
                "Creative config (standardized into config/language_guard/)."
                if p.endswith("xianxia_language_guard.json")
                else "Creative config (kept)."
            )
            return (Category.CREATIVE_CONFIG, MappingStatus.KEPT, _KEEP_CONFIG[p], True, note)
        if name.startswith("account_tiers"):
            return (
                Category.LEGACY_INFRA,
                MappingStatus.REMOVED_LEGACY,
                None,
                False,
                "SaaS account tiering config (not a creative asset).",
            )
        # Unknown config file -> flag for review, do not silently keep.
        return (
            Category.CREATIVE_CONFIG,
            MappingStatus.KEPT,
            f"config/{'/'.join(parts[1:])}",
            True,
            "Config file not in known set - REVIEW classification.",
        )

    # --- scripts/ : business logic vs legacy infra --------------------------- #
    if top == "scripts":
        if p in _BUSINESS_LOGIC_TARGETS:
            return (
                Category.BUSINESS_LOGIC,
                MappingStatus.EXTRACTED,
                _BUSINESS_LOGIC_TARGETS[p],
                False,
                "Business logic extracted to Hermes tool/plugin.",
            )
        for prefix, target in _BUSINESS_LOGIC_DIR_TARGETS.items():
            if p.startswith(prefix):
                return (
                    Category.BUSINESS_LOGIC,
                    MappingStatus.EXTRACTED,
                    target,
                    False,
                    "Business logic (unified) extracted to Hermes tool/plugin.",
                )
        # Remaining scripts are legacy infra: runners, providers, CLIs,
        # observability, account_tiers, projections, control-plane SQLite, etc.
        return (
            Category.LEGACY_INFRA,
            MappingStatus.REMOVED_LEGACY,
            None,
            False,
            "Legacy runtime/infra script (replaced by Hermes loop/providers).",
        )

    # --- Runtime data, generated state, old tests, infra files --------------- #
    _LEGACY_DATA_TOPS = {
        "novels", "logs", "state", "database", "memory", "tests", "docs",
        ".rag", ".openclaw", ".test_artifacts",
    }
    if top in _LEGACY_DATA_TOPS:
        note = {
            "novels": "Personal novel data (out of migration scope per non-goals).",
            "tests": "Old test suite (golden baselines may be ported in Phase 6).",
        }.get(top, "Runtime/generated data (not part of the creative brain).")
        return (Category.LEGACY_INFRA, MappingStatus.REMOVED_LEGACY, None, False, note)

    # --- Known legacy root files --------------------------------------------- #
    _LEGACY_ROOT_FILES = {
        "app.js", "index.html", "styles.css", "docker-compose.yml", "Dockerfile",
        "requirements.txt", ".env.example", ".gitignore",
        "AGENTS.md", "ARCHITECTURE.md", "CHANGELOG.md", "DEPLOYMENT.md",
        "HEARTBEAT.md", "HUONG_DAN_SU_DUNG.md", "MIGRATION_OPENCLAW_TO_NOVELKIT.md",
        "PIPELINE.md", "README.md", "README.vi.md", "RELEASE_NOTES_P0_P2.md",
        "RELEASE_SIGNOFF.md", "RUNBOOK_ACCOUNT_TIERS.md", "TOOLS.md",
        "UPGRADE_PLAN.md", "USER.md", "MEMORY.md",
    }
    if len(parts) == 1 and name in _LEGACY_ROOT_FILES:
        return (
            Category.LEGACY_INFRA,
            MappingStatus.REMOVED_LEGACY,
            None,
            False,
            "Legacy infra / project doc (replaced by Hermes surface).",
        )

    # --- Safe default: never silently treat as creative --------------------- #
    return (
        Category.LEGACY_INFRA,
        MappingStatus.REMOVED_LEGACY,
        None,
        False,
        "Unclassified - defaulted to legacy-infra; REVIEW.",
    )


# --------------------------------------------------------------------------- #
# Scanning
# --------------------------------------------------------------------------- #


def _iter_source_files(source_root: Path) -> Iterable[Path]:
    """Yield regular (non-symlink) files under ``source_root``, skipping noise."""
    for path in sorted(source_root.rglob("*")):
        if path.is_symlink():
            continue
        if not path.is_file():
            continue
        rel_parts = path.relative_to(source_root).parts
        if any(part in _EXCLUDED_DIR_NAMES for part in rel_parts):
            continue
        if path.suffix in _EXCLUDED_SUFFIXES:
            continue
        yield path


def scan(source_root: Path = DEFAULT_SOURCE_ROOT) -> list[FileRecord]:
    """Scan ``source_root`` and return one :class:`FileRecord` per file."""
    source_root = Path(source_root)
    if not source_root.exists():
        raise FileNotFoundError(f"Source root not found: {source_root}")

    records: list[FileRecord] = []
    for path in _iter_source_files(source_root):
        rel = _posix(path.relative_to(source_root))
        category, status, target, must_keep, note = classify(rel)
        records.append(
            FileRecord(
                path=rel,
                category=category,
                mapping_status=status,
                target=target,
                must_keep=must_keep,
                note=note,
            )
        )
    return records


def find_orphans(records: Iterable[FileRecord]) -> list[FileRecord]:
    """Must-keep files lacking a target artifact (blocking errors, Req 1.4)."""
    return [r for r in records if r.must_keep and not r.target]


def must_keep_records(records: Iterable[FileRecord]) -> list[FileRecord]:
    return [r for r in records if r.must_keep]


# --------------------------------------------------------------------------- #
# Inventory assembly + reporting
# --------------------------------------------------------------------------- #


def build_inventory(source_root: Path = DEFAULT_SOURCE_ROOT) -> dict:
    """Build the full inventory document (records + summary + coverage)."""
    records = scan(source_root)
    orphans = find_orphans(records)
    must_keep = must_keep_records(records)

    by_category: dict[str, int] = {c.value: 0 for c in Category}
    by_status: dict[str, int] = {s.value: 0 for s in MappingStatus}
    review_flags: list[str] = []
    for r in records:
        by_category[r.category.value] += 1
        by_status[r.mapping_status.value] += 1
        if "REVIEW" in r.note:
            review_flags.append(r.path)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(Path(source_root)),
        "summary": {
            "total_files": len(records),
            "by_category": by_category,
            "by_status": by_status,
            "must_keep_count": len(must_keep),
            "orphan_count": len(orphans),
            "coverage_complete": len(orphans) == 0,
            "review_flag_count": len(review_flags),
        },
        "orphans": [r.to_dict() for r in orphans],
        "review_flags": review_flags,
        "records": [r.to_dict() for r in records],
    }


def write_json(inventory: dict, path: Path = INVENTORY_JSON) -> Path:
    path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _md_table(rows: list[tuple[str, ...]], headers: tuple[str, ...]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def write_markdown(inventory: dict, path: Path = INVENTORY_MD) -> Path:
    s = inventory["summary"]
    lines: list[str] = []
    lines.append("# Migration Inventory — Phase 0")
    lines.append("")
    lines.append(f"> Sinh tự động bởi `migration/inventory.py` lúc {inventory['generated_at']}.")
    lines.append(f"> Nguồn: `{inventory['source_root']}`")
    lines.append("")
    lines.append("## Tổng quan")
    lines.append("")
    lines.append(f"- Tổng số file kiểm kê: **{s['total_files']}**")
    lines.append(f"- Số file **bắt buộc-giữ** (creative-knowledge + creative-config): **{s['must_keep_count']}**")
    lines.append(f"- File mồ côi (must-keep thiếu đích): **{s['orphan_count']}**")
    cov = "✅ ĐẠT 100%" if s["coverage_complete"] else "❌ CHƯA ĐẠT"
    lines.append(f"- Độ phủ ánh xạ must-keep: **{cov}**")
    lines.append(f"- Mục cần review thủ công: **{s['review_flag_count']}**")
    lines.append("")
    lines.append("### Phân loại theo category")
    lines.append("")
    lines.append(_md_table(
        [(k, str(v)) for k, v in s["by_category"].items()],
        ("category", "số file"),
    ))
    lines.append("")
    lines.append("### Phân loại theo mapping status")
    lines.append("")
    lines.append(_md_table(
        [(k, str(v)) for k, v in s["by_status"].items()],
        ("mapping status", "số file"),
    ))
    lines.append("")

    if inventory["orphans"]:
        lines.append("## ⚠️ Orphans (lỗi blocking — Req 1.4)")
        lines.append("")
        lines.append(_md_table(
            [(o["path"], o["category"], o["note"]) for o in inventory["orphans"]],
            ("path", "category", "note"),
        ))
        lines.append("")

    if inventory["review_flags"]:
        lines.append("## 🔎 Cần review thủ công")
        lines.append("")
        for pth in inventory["review_flags"]:
            lines.append(f"- `{pth}`")
        lines.append("")

    lines.append("## Danh sách bắt buộc-giữ (must-keep → đích)")
    lines.append("")
    mk = [r for r in inventory["records"] if r["must_keep"]]
    lines.append(_md_table(
        [(r["path"], r["category"], r["target"] or "—") for r in mk],
        ("source", "category", "target"),
    ))
    lines.append("")

    lines.append("## Toàn bộ kiểm kê")
    lines.append("")
    lines.append(_md_table(
        [(r["path"], r["category"], r["mapping_status"], r["target"] or "—")
         for r in inventory["records"]],
        ("source", "category", "status", "target"),
    ))
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# Freeze (baseline) — Task 1.2
# --------------------------------------------------------------------------- #


def build_baseline(source_root: Path = DEFAULT_SOURCE_ROOT) -> dict:
    """Build the frozen must-keep baseline (the migration contract)."""
    records = scan(source_root)
    mk = must_keep_records(records)
    return {
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(Path(source_root)),
        "must_keep_count": len(mk),
        "must_keep": [r.to_dict() for r in mk],
    }


def write_baseline(source_root: Path = DEFAULT_SOURCE_ROOT, path: Path = BASELINE_JSON) -> Path:
    baseline = build_baseline(source_root)
    path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_baseline(path: Path = BASELINE_JSON) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="NovelKit migration inventory scanner")
    parser.add_argument(
        "--source", type=Path, default=DEFAULT_SOURCE_ROOT,
        help="Source root to scan (default: _novelkit_source/)",
    )
    parser.add_argument(
        "--freeze", action="store_true",
        help="Also (re)write the frozen must-keep baseline.",
    )
    args = parser.parse_args(argv)

    inventory = build_inventory(args.source)
    write_json(inventory)
    write_markdown(inventory)

    s = inventory["summary"]
    print(f"Scanned {s['total_files']} files -> {INVENTORY_JSON.name}, {INVENTORY_MD.name}")
    print(f"  must-keep: {s['must_keep_count']}  orphans: {s['orphan_count']}  "
          f"review-flags: {s['review_flag_count']}")
    for cat, n in s["by_category"].items():
        print(f"    {cat}: {n}")

    if args.freeze:
        write_baseline(args.source)
        print(f"Froze must-keep baseline -> {BASELINE_JSON.name}")

    if not s["coverage_complete"]:
        print("BLOCKING: must-keep files without a target (orphans) detected.")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
