"""Redacted diagnostics export for NovelKit Hermes runtime and creative state."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tools import registry
from tools.novelkit_rules_tool import current_rules_digest


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_entry(root: Path, path: Path) -> dict[str, Any]:
    rel = path.relative_to(root).as_posix()
    data = path.read_bytes()
    return {
        "path": rel,
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_count": len(data),
    }


def _safe_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _artifact_manifest(root: Path) -> list[dict[str, Any]]:
    patterns = (
        "PROJECT_DNA.md",
        "PROJECT_DNA.rules.json",
        "PLAN.md",
        "GOAL_TRACKER.md",
        "logs/**/*.json",
        "logs/**/*.jsonl",
        "chapters/*.md",
        "drafts/*.md",
        "drafts/*.json",
        "reviews/*.json",
        "reviews/*.md",
        ".commits/*.json",
        ".rag/*.json",
        "summaries/**/*.json",
    )
    seen: set[str] = set()
    entries: list[dict[str, Any]] = []
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            entries.append(_artifact_entry(root, path))
    return entries


def _state_status_alignment(root: Path) -> dict[str, Any]:
    state = _safe_json(root / "logs" / "pipeline_state.json")
    status = _safe_json(root / "logs" / "pipeline_status.json")
    state_digest = state.get("state_digest")
    source_state_digest = status.get("source_state_digest")
    return {
        "state_digest": state_digest,
        "source_state_digest": source_state_digest,
        "aligned": bool(state_digest and state_digest == source_state_digest),
    }


def _checkpoint_summary(root: Path) -> dict[str, Any]:
    path = root / "logs" / "checkpoints.jsonl"
    if not path.exists():
        return {"count": 0, "last_seq": None, "tail_valid": True}
    count = 0
    last_seq = None
    tail_valid = True
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            tail_valid = False
            continue
        count += 1
        last_seq = data.get("seq", last_seq)
    return {"count": count, "last_seq": last_seq, "tail_valid": tail_valid}


def _transaction_summary(root: Path) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for path in sorted((root / "logs" / "transactions").glob("*/manifest.json")):
        data = _safe_json(path)
        status = str(data.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return {"by_status": counts}


def _review_trend(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "reviews").glob("*_review.json")):
        data = _safe_json(path)
        if not data:
            continue
        issue_codes = []
        for issue in data.get("issues") or []:
            if isinstance(issue, dict) and issue.get("code"):
                issue_codes.append(str(issue["code"]))
        rows.append(
            {
                "chapter": data.get("chapter"),
                "review_id": data.get("review_id"),
                "overall_score": data.get("overall_score"),
                "gate_outcome": data.get("gate_outcome"),
                "issue_codes": issue_codes,
            }
        )
    return rows


def export_diagnostics(
    novel_path: str | Path,
    *,
    strict_private_rules: bool = True,
) -> dict[str, Any]:
    """Return runtime + creative diagnostics without raw prose or prompts."""
    root = Path(novel_path)
    return {
        "schema_version": 1,
        "redaction": {
            "raw_prose": "omitted",
            "raw_prompt": "omitted",
            "credentials": "omitted",
            "private_rule_text": "omitted" if strict_private_rules else "hash_only",
        },
        "runtime": {
            "artifact_manifest": _artifact_manifest(root),
            "state_status_alignment": _state_status_alignment(root),
            "checkpoints": _checkpoint_summary(root),
            "transactions": _transaction_summary(root),
        },
        "creative": {
            "rules_digest": current_rules_digest(root),
            "review_trend": _review_trend(root),
        },
    }


def diagnostics_tool(action: str, novel_path: str, **kwargs: Any) -> Any:
    if action == "export":
        return export_diagnostics(novel_path)
    if action == "diagnose":
        return diagnose(novel_path, redact=bool(kwargs.get("redact", False)))
    raise ValueError(f"unknown action {action!r}; expected export|diagnose")


registry.register(
    "novelkit_diagnostics",
    diagnostics_tool,
    schema={
        "name": "novelkit_diagnostics",
        "description": "Redacted runtime/creative diagnostics export + "
        "creative-health diagnose (process/quality/planning/context).",
        "input": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["export", "diagnose"]},
                "novel_path": {"type": "string"},
                "redact": {"type": "boolean"},
            },
            "required": ["action", "novel_path"],
        },
        "output": {"type": "object"},
    },
    module=__name__,
)


__all__ = ["diagnostics_tool", "export_diagnostics", "diagnose"]


# --------------------------------------------------------------------------- #
# Creative-health diagnostics (Req 10; Property P23) — read-only, 4 dimensions:
#   process · quality · planning · context
# --------------------------------------------------------------------------- #

import re as _re

_DIAG_RULES_PATH = Path(__file__).resolve().parent.parent / "config" / "diag_rules.json"
_CHAPTER_FILE_RE = _re.compile(r"chapter_(\d+)\.md$", _re.IGNORECASE)


def _diag_rules() -> dict[str, Any]:
    defaults = {
        "low_score": 85,
        "rewrite_rate_warn": 0.3,
        "min_reviews_for_rate": 3,
        "character_absence_chapters": 20,
        "foreshadow_overdue": True,
    }
    data = _safe_json(_DIAG_RULES_PATH)
    return {**defaults, **data}


def _finding(code, dimension, severity, evidence, suggestion) -> dict[str, Any]:
    return {
        "code": code,
        "dimension": dimension,
        "severity": severity,
        "evidence": evidence,
        "suggestion": suggestion,
    }


def _canon_chapter_numbers(root: Path) -> list[int]:
    nums: list[int] = []
    for path in (root / "chapters").glob("chapter_*.md"):
        m = _CHAPTER_FILE_RE.search(path.name)
        if m:
            nums.append(int(m.group(1)))
    return sorted(set(nums))


def _diag_process(root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    state = _safe_json(root / "logs" / "pipeline_state.json")
    breaker = state.get("breaker") or {}
    if breaker and (
        breaker.get("hard_fail_count", 0) >= breaker.get("max_hard_fail", 2)
        or breaker.get("soft_fail_count", 0) >= breaker.get("max_soft_fail", 3)
        or breaker.get("total_attempts", 0) >= breaker.get("max_total", 5)
    ):
        out.append(_finding(
            "breaker_open", "process", "error",
            {"breaker": breaker},
            "Sửa gốc lỗi của scope hiện tại rồi resume; xem novelkit_pipeline.resume.",
        ))
    chapters = _canon_chapter_numbers(root)
    if chapters:
        full = set(range(1, max(chapters) + 1))
        missing = sorted(full - set(chapters))
        if missing:
            out.append(_finding(
                "chapter_number_skip", "process", "warning",
                {"missing_chapters": missing[:10], "highest": max(chapters)},
                "Kiểm tra DAG/sync: có chương bị nhảy số chưa promote vào canon.",
            ))
    return out


def _diag_quality(root: Path, rules: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    reviews = []
    for path in sorted((root / "reviews").glob("*_review.json")):
        data = _safe_json(path)
        if data:
            reviews.append(data)
    if not reviews:
        return out
    low = [r for r in reviews if isinstance(r.get("overall_score"), (int, float))
           and r["overall_score"] < rules["low_score"]]
    if low:
        out.append(_finding(
            "review_score_low", "quality", "warning",
            {"count": len(low), "chapters": [r.get("chapter") for r in low][:10],
             "threshold": rules["low_score"]},
            "Các chương điểm thấp dai dẳng — soát lại rubric/độ dài/outline density.",
        ))
    if len(reviews) >= rules["min_reviews_for_rate"]:
        not_pass = sum(1 for r in reviews if r.get("gate_outcome") not in ("pass", None))
        rate = round(not_pass / len(reviews), 3)
        if rate >= rules["rewrite_rate_warn"]:
            out.append(_finding(
                "rewrite_rate_high", "quality", "warning",
                {"rewrite_rate": rate, "reviews": len(reviews)},
                "Tỉ lệ không-pass cao — kiểm tra prompt Prose Writer / outline contract.",
            ))
    return out


def _diag_planning(root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    # foreshadow stalled (overdue / orphan) via strand, at the highest chapter.
    # Gated by the ``foreshadow_overdue`` rule so operators can disable this
    # check via config (the key was previously defined but never consulted).
    rules = _diag_rules()
    chapters = _canon_chapter_numbers(root)
    current = chapters[-1] if chapters else 0
    if current and rules.get("foreshadow_overdue", True):
        try:
            from tools.novelkit_strand_tool import weave

            report = weave(root, current)
            overdue = [
                e for e in report.get("due_payoffs", [])
                if e.get("loop_deadline") is not None and e["loop_deadline"] < current
            ]
            if overdue:
                out.append(_finding(
                    "foreshadow_stalled", "planning", "warning",
                    {"overdue": len(overdue),
                     "examples": [e.get("event_id") for e in overdue][:5]},
                    "Trả payoff sắp tới, dời deadline có chủ đích, hoặc đóng loop.",
                ))
        except Exception:  # noqa: BLE001 — strand optional; never crash diag
            pass
    # compass missing/stale (compass mode in use when arc_map present).
    arc_map_path = root / "outlines" / "arc_map.json"
    compass_path = root / "outlines" / "compass.md"
    if arc_map_path.exists() and not compass_path.exists():
        out.append(_finding(
            "compass_missing", "planning", "warning",
            {"arc_map": "present", "compass": "absent"},
            "Chạy bootstrap.compass / update_compass để khôi phục la bàn truyện.",
        ))
    elif compass_path.exists() and current:
        from tools.novelkit_compass_tool import read_compass

        compass = read_compass(root) or {}
        est = (compass.get("scale_estimate") or {}).get("chapters")
        if isinstance(est, int) and est and current > est:
            out.append(_finding(
                "compass_stale", "planning", "warning",
                {"scale_estimate_chapters": est, "current_chapter": current},
                "Cập nhật Compass scale_estimate ở ranh giới Cuốn (đã vượt ước lượng).",
            ))
    # arc/volume summary coverage.
    try:
        from tools.novelkit_compass_tool import read_arc_map

        for arc in read_arc_map(root).arcs:
            if arc.status == "done" and not (
                root / "summaries" / f"arc_{arc.arc_id}.md"
            ).exists():
                out.append(_finding(
                    "summary_missing", "planning", "warning",
                    {"arc_id": arc.arc_id},
                    "Chạy task arc.<id>.summary trước khi khai triển Hồi kế.",
                ))
    except Exception:  # noqa: BLE001
        pass
    return out


def _diag_context(root: Path, rules: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    chapters = _canon_chapter_numbers(root)
    current = chapters[-1] if chapters else 0
    if not current:
        return out
    # Read-only (P23): never create the memory DB as a side effect of diagnosis.
    if not (root / "memory" / "items.sqlite3").exists():
        return out
    try:
        from plugins.memory.novelkit_memory import get_provider

        items = get_provider().store(root).query(
            category="character_state", status="active", limit=10_000
        )
    except Exception:  # noqa: BLE001
        return out
    last_seen: dict[str, int] = {}
    for it in items:
        ch = it.source_chapter
        if isinstance(ch, int):
            last_seen[it.subject] = max(last_seen.get(it.subject, 0), ch)
    threshold = rules["character_absence_chapters"]
    gone = sorted(
        s for s, ch in last_seen.items() if current - ch >= threshold
    )
    if gone:
        out.append(_finding(
            "character_disappeared", "context", "warning",
            {"characters": gone[:10], "since_chapters": threshold,
             "current_chapter": current},
            "Nhân vật vắng mặt dài — đưa trở lại hoặc giải thích on-page.",
        ))

    # Cast-intros sidecar enforcement: warn when recent chapters lack .cast.json
    # so minor_cast tracking stays fed (Req 18 / ARCHITECTURE §8 seam).
    if current >= 5:
        cast_missing_streak = 0
        for ch in range(current, max(current - 10, 0), -1):
            sidecar = root / "drafts" / f"chapter_{ch:04d}.cast.json"
            if not sidecar.exists():
                cast_missing_streak += 1
            else:
                break
        if cast_missing_streak >= 5:
            out.append(_finding(
                "cast_sidecar_missing", "context", "warning",
                {"missing_streak": cast_missing_streak,
                 "latest_chapter": current},
                "Writer không sinh cast sidecar (.cast.json) cho 5+ chương liên tiếp "
                "— minor_cast tracking bị mù. Đảm bảo Prose Writer output sidecar "
                "hoặc thêm cast_intros vào self_check contract.",
            ))

    return out


def _diag_consistency(root: Path) -> list[dict[str, Any]]:
    """Surface KG narrative contradictions as ``consistency`` findings (Req 4.3).

    Gated behind the ``graph`` feature flag: when it is off, the knowledge graph
    is not in play, so we return nothing. Read-only (P23/P28): it calls the pure
    ``detect_contradictions`` (loads the persisted graph or rebuilds it in-RAM,
    never mutating) and maps each tiered conflict into an actionable finding.
    The whole body is wrapped so a missing ``networkx``/graph can never crash a
    diagnose run — it degrades to an empty list instead.
    """
    try:
        from tools.novelkit_longform_config import flag_enabled

        if not flag_enabled("graph", root):
            return []
        from tools.novelkit_graph_tool import detect_contradictions

        report = detect_contradictions(root)
    except Exception:  # noqa: BLE001 — graph optional; diag must never crash
        return []

    out: list[dict[str, Any]] = []
    for c in report.get("hard", []):
        evidence = dict(c.get("evidence") or {})
        evidence["affected_chapters"] = c.get("affected_chapters", [])
        out.append(_finding(
            c.get("code", "kg_contradiction"), "consistency", "error",
            evidence,
            "Mâu thuẫn logic không thể sửa bằng câu chữ — đưa chương liên quan "
            "vào rewrite_queue (novelkit_graph.apply_contradictions).",
        ))
    for s in report.get("soft", []):
        evidence = dict(s.get("evidence") or {})
        if s.get("affected_chapters") is not None:
            evidence["affected_chapters"] = s.get("affected_chapters")
        out.append(_finding(
            s.get("code", "kg_soft_conflict"), "consistency", "warning",
            evidence,
            "Xung đột mềm giữa các dữ kiện — rà soát canon/memory để chốt giá trị đúng.",
        ))
    return out


def _diag_voice(root: Path) -> list[dict[str, Any]]:
    """Surface per-character voice drift findings."""
    out: list[dict[str, Any]] = []
    try:
        from tools.novelkit_ai_flavor_tool import detect_voice_drift
        violations = detect_voice_drift(root)
    except Exception:
        return out
    for v in violations:
        out.append(_finding(
            "voice_drift", "quality", "warning",
            {"excerpt": v.excerpt},
            v.fix_hint or "Kiểm tra voice consistency cho nhân vật này.",
        ))
    return out


def _diag_canon_system(root: Path) -> list[dict[str, Any]]:
    """Verify genre canon system files are accessible (skills/novelkit-canon/).

    The quality audit rubric and SOUL.md references rely on
    ``skills/novelkit-canon/canon/system/<genre>/`` existing at runtime. When the
    canon pack is missing, the Quality Auditor operates without its genre-specific
    rubric — degrading review quality silently. Read-only (P23).
    """
    out: list[dict[str, Any]] = []
    canon_root = Path(__file__).resolve().parent.parent / "skills" / "novelkit-canon" / "canon" / "system"
    if not canon_root.is_dir():
        out.append(_finding(
            "canon_system_missing", "process", "error",
            {"expected_path": str(canon_root)},
            "Genre canon system không tìm thấy tại skills/novelkit-canon/canon/system/. "
            "Quality Auditor không có rubric thể loại — review chỉ generic. "
            "Đảm bảo skills/novelkit-canon/ được mount/clone đúng vị trí.",
        ))
        return out
    # Check that at least one genre dir exists with content
    genre_dirs = [d for d in canon_root.iterdir() if d.is_dir()]
    if not genre_dirs:
        out.append(_finding(
            "canon_system_empty", "process", "warning",
            {"path": str(canon_root), "genre_count": 0},
            "Genre canon system tồn tại nhưng rỗng — cần ít nhất 1 thư mục thể loại.",
        ))
    return out


def diagnose(novel_path: str | Path, *, redact: bool = False) -> list[dict[str, Any]]:
    """Run all creative-health rules (read-only; deterministic — P23)."""
    root = Path(novel_path)
    rules = _diag_rules()
    findings: list[dict[str, Any]] = []
    findings += _diag_process(root)
    findings += _diag_quality(root, rules)
    findings += _diag_planning(root)
    findings += _diag_context(root, rules)
    findings += _diag_consistency(root)
    findings += _diag_voice(root)
    findings += _diag_canon_system(root)
    if redact:
        for f in findings:
            f["evidence"] = {"redacted": True, "keys": sorted(f["evidence"].keys())}
    return findings
