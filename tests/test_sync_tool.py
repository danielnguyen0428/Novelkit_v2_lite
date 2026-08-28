"""Tests for the sync / memory-commit + doctor tool (Task 10, Requirements 11/18).

Property-based tests cover the two headline correctness properties from
design.md §"Correctness Properties":

- **P11 — Idempotent sync**: running ``commit`` twice on the same state does not
  change canon (only derivative state refreshes). The second sync reports
  ``idempotent=True`` and every tracked canon/planning text file is byte-identical.
  **Validates: Requirements 11.1**
- **P5 — Canon authority through sync**: the reindex step never writes a canon
  file and the rebuilt context engine still ranks canon above derivative state.
  **Validates: Requirements 4.3, 13.2**

Plus unit tests for the review gate (block/allow), the 3-stage split, the
content-addressed commit, planning-doc upsert, provenance, the doctor's
blocking/report-only classification, rotation/style-audit cadence, the rolling
seed hand-off, and self-registration.
"""

from __future__ import annotations

import json
import hashlib
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from plugins.context_engine.novelkit_context import (
    AuthorityTier,
    Chunk,
    authority_rank_for_path,
)
from tools import registry
from tools.novelkit_gate_tool import derive_typed_review
from tools.novelkit_pipeline_tool import PipelineEngine
from tools.novelkit_rules_tool import current_rules_digest
from tools.novelkit_sync_tool import (
    RAG_INDEX_META_REL_PATH,
    ChapterCommit,
    Issue,
    ReviewGateFailed,
    SyncStageKind,
    accept_commit,
    build_commit,
    classify_blocking,
    commit,
    commit_episodic,
    health_check,
    reindex,
    recover_transactions,
    stamp_human_approval,
    sync_tool,
    update_planning_docs,
)

# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #

_PASSING_REVIEW = """# Review chapter

**Trạng thái:** PASS

| Logic Consistency | 14/15 |
| Character Integrity | 11/12 |
| Plot Advancement | 9/10 |
| Timeline & Continuity | 7/8 |
| Prose Fundamentals | 9/10 |
| Hook & Micro-payoff | 5/5 |
| Author Style | 36/40 |

**Điểm:** 91/100
"""

_FAILING_REVIEW = """# Review chapter

**Trạng thái:** HARD_FAIL

**Điểm:** 52/100
"""

_CHAPTER_TEXT = (
    "Hắn bước vào sảnh đường rộng lớn, ánh nến lập lòe trên những cây cột đá.\n\n"
    "Người gác cổng cúi đầu chào. Hắn gật đầu rồi sải bước về phía ngai vàng, "
    "lòng nặng trĩu một lời thề chưa trả.\n\n"
    "Bên ngoài, mưa bắt đầu rơi, gột rửa bụi đường trên vai áo bạc màu."
)


def _tmp() -> Path:
    return Path(tempfile.mkdtemp())


def _make_novel(
    *,
    chapters: dict[int, str] | None = None,
    reviews: dict[int, str] | None = None,
    name: str = "demo-novel",
    pipeline_status: dict | None = None,
) -> Path:
    """Create a minimal novel workspace with the required canon files."""
    novel = _tmp() / name
    (novel / "chapters").mkdir(parents=True)
    (novel / "reviews").mkdir(parents=True)
    (novel / "memory").mkdir(parents=True)
    (novel / "logs").mkdir(parents=True)

    (novel / "PROJECT_DNA.md").write_text(
        "---\ntitle: Demo\ngenre: xianxia\ntarget_chapters: 50\n---\n# Demo\n",
        encoding="utf-8",
    )
    (novel / "PLAN.md").write_text("# PLAN\n", encoding="utf-8")
    (novel / "GOAL_TRACKER.md").write_text("# GOAL TRACKER\n", encoding="utf-8")
    (novel / "memory" / "Memory.md").write_text("# Memory\n", encoding="utf-8")

    status = pipeline_status or {
        "novel": name,
        "status": "running",
        "circuit_breaker": {
            "hard_fail_count": 0,
            "soft_fail_count": 0,
            "total_attempts": 0,
            "max_hard_fail": 2,
            "max_soft_fail": 3,
            "max_total": 5,
        },
    }
    (novel / "logs" / "pipeline_status.json").write_text(
        json.dumps(status), encoding="utf-8"
    )

    chapters = chapters or {1: _CHAPTER_TEXT}
    reviews = reviews or {1: _PASSING_REVIEW}
    for ch, text in chapters.items():
        (novel / "chapters" / f"chapter_{ch:03d}.md").write_text(text, encoding="utf-8")
    for ch, text in reviews.items():
        (novel / "reviews" / f"chapter_{ch:03d}_review.md").write_text(
            text, encoding="utf-8"
        )
    return novel


def _write_typed_review(
    novel: Path,
    chapter: int,
    *,
    score: int = 91,
    gate: str = "pass",
    draft_rel: str | None = None,
    rules_digest: str | None = None,
) -> Path:
    draft_rel = draft_rel or f"drafts/chapter_{chapter:04d}.md"
    draft_sha = hashlib.sha256((novel / draft_rel).read_bytes()).hexdigest()
    dimensions = {
        "plot_progression": score,
        "character_consistency": score,
        "continuity": score,
        "prose_quality": score,
        "dialogue_voice": score,
        "world_consistency": score,
        "reader_momentum": score,
    }
    if gate == "polish":
        dimensions["reader_momentum"] = min(score, 75)
        dimensions["prose_quality"] = min(score, 75)
    elif gate == "rewrite":
        dimensions["continuity"] = min(score, 50)
    review = derive_typed_review(
        review_id=f"chapter_{chapter:04d}_attempt_01",
        chapter=chapter,
        attempt=1,
        draft_sha256=draft_sha,
        dimensions=dimensions,
        rules_digest=rules_digest,
        reviewer_model_fingerprint="test:model",
    )
    path = novel / "reviews" / f"chapter_{chapter:04d}_review.json"
    path.write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (novel / "reviews" / f"chapter_{chapter:04d}_review.md").write_text(
        "# Review projection\n\n**Trạng thái:** PASS\n\n**Điểm:** 99/100\n",
        encoding="utf-8",
    )
    return path


def _snapshot_text_files(novel: Path) -> dict[str, str]:
    """Snapshot every tracked canon/planning text file → content."""
    globs = (
        "PROJECT_DNA.md",
        "PLAN.md",
        "GOAL_TRACKER.md",
        "memory/Memory.md",
        "chapters/*.md",
        "reviews/*.md",
        "outlines/**/*.md",
        "database/**/*.md",
    )
    snapshot: dict[str, str] = {}
    for pattern in globs:
        for path in novel.glob(pattern):
            if path.is_file():
                snapshot[path.relative_to(novel).as_posix()] = path.read_text(
                    encoding="utf-8"
                )
    return snapshot


# --------------------------------------------------------------------------- #
# Property 11 — Idempotent sync
# --------------------------------------------------------------------------- #


@settings(max_examples=40, deadline=None)
@given(chapter=st.integers(min_value=1, max_value=12))
def test_property_idempotent_sync_does_not_change_canon(chapter):
    """P11: a second sync on the same state is a no-op on canon.

    **Validates: Requirements 11.1**
    """
    novel = _make_novel(
        chapters={chapter: _CHAPTER_TEXT}, reviews={chapter: _PASSING_REVIEW}
    )

    first = commit(novel, chapter)
    assert first.gate_passed is True
    assert first.idempotent is False

    before = _snapshot_text_files(novel)
    second = commit(novel, chapter)
    after = _snapshot_text_files(novel)

    # The repeated sync recognises the existing commit and changes no canon.
    assert second.idempotent is True
    assert second.commit_id == first.commit_id
    assert second.updated_docs == []
    assert before == after


def test_idempotent_sync_three_times_stable():
    """P11: canon + commit fingerprint stay stable across repeated syncs."""
    novel = _make_novel()
    commit(novel, 1)
    snap = _snapshot_text_files(novel)
    commit_json = (novel / ".commits" / "chapter_0001.commit.json").read_text(
        encoding="utf-8"
    )
    for _ in range(2):
        commit(novel, 1)
        assert _snapshot_text_files(novel) == snap
        assert (
            novel / ".commits" / "chapter_0001.commit.json"
        ).read_text(encoding="utf-8") == commit_json


# --------------------------------------------------------------------------- #
# Property 5 — Canon authority through sync
# --------------------------------------------------------------------------- #


def test_property_reindex_never_writes_canon():
    """P5: reindex only touches derivative paths, never a canon file.

    **Validates: Requirements 4.3, 13.2**
    """
    novel = _make_novel()
    before = _snapshot_text_files(novel)
    result = reindex(novel)
    after = _snapshot_text_files(novel)

    # No canon/planning text file changed; only the derivative index meta wrote.
    assert before == after
    assert (novel / RAG_INDEX_META_REL_PATH).exists()
    assert authority_rank_for_path(RAG_INDEX_META_REL_PATH) == AuthorityTier.DERIVATIVE
    assert result["canon_chunks"] >= 1


def test_reindex_includes_rules_snapshot_and_summaries():
    novel = _make_novel()
    (novel / "PROJECT_DNA.rules.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "revision": 1,
                "rules": [],
                "updated_at": "2026-06-29T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    (novel / "summaries").mkdir()
    (novel / "summaries" / "chapter_0001.summary.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "chapter": 1,
                "source_commit_ids": ["commit-a"],
                "source_digests": {"chapters/chapter_001.md": "a" * 64},
                "event": "moon oath unresolved debt",
            }
        ),
        encoding="utf-8",
    )

    reindex(novel)

    meta = json.loads((novel / RAG_INDEX_META_REL_PATH).read_text(encoding="utf-8"))
    assert "PROJECT_DNA.rules.json" in meta["file_manifest"]
    assert "summaries/chapter_0001.summary.json" in meta["file_manifest"]


@settings(max_examples=40, deadline=None)
@given(
    canon_score=st.integers(min_value=0, max_value=100),
    deriv_score=st.integers(min_value=0, max_value=100),
)
def test_property_canon_outranks_derivative_after_sync(canon_score, deriv_score):
    """P5: after sync, canon always ranks above derivative regardless of score.

    A canon chunk and a derivative (index) chunk are ordered by authority first;
    the derivative state can never override canon (Requirement 13.2).

    **Validates: Requirements 4.3, 13.2**
    """
    canon = Chunk(path="chapters/chapter_001.md", heading="c", content="x")
    deriv = Chunk(path=".rag/index_meta.json", heading="d", content="y")
    # Authority dominates no matter the (hypothetical) relevance scores.
    assert authority_rank_for_path(canon.path) < authority_rank_for_path(deriv.path)
    ranked = sorted(
        [(deriv, deriv_score), (canon, canon_score)],
        key=lambda pair: (int(authority_rank_for_path(pair[0].path)), -pair[1]),
    )
    assert ranked[0][0] is canon


def test_doctor_flags_canon_index_incoherence():
    """P5 corollary: if a chapter changes after commit, the doctor flags the
    stale index/commit as blocking — canon wins, derivative must rebuild."""
    novel = _make_novel()
    commit(novel, 1)
    # Mutate the canon chapter after the commit.
    (novel / "chapters" / "chapter_001.md").write_text(
        _CHAPTER_TEXT + "\n\nMột dòng mới được thêm vào.", encoding="utf-8"
    )
    issues = health_check(novel)
    codes = {i.code for i in issues}
    assert "canon_index_incoherent" in codes or "rag_index_stale" in codes
    assert classify_blocking(issues)  # the incoherence blocks


# --------------------------------------------------------------------------- #
# Unit tests — review gate (Requirement 11.1)
# --------------------------------------------------------------------------- #


def test_review_gate_blocks_hard_fail():
    novel = _make_novel(reviews={1: _FAILING_REVIEW})
    report = commit(novel, 1)
    assert report.gate_passed is False
    assert report.blocked is True
    assert report.commit_id is None
    assert report.stages[0].stage == SyncStageKind.COMMIT_LEDGER.value
    assert report.stages[0].success is False


def test_review_gate_allows_pass():
    novel = _make_novel()
    report = commit(novel, 1)
    assert report.gate_passed is True
    assert report.commit_id is not None


def test_build_commit_raises_on_failed_gate():
    novel = _make_novel(reviews={1: _FAILING_REVIEW})
    try:
        build_commit(novel, 1)
        assert False, "expected ReviewGateFailed"
    except ReviewGateFailed as exc:
        assert exc.chapter == 1


def test_build_commit_rescans_xianxia_register_before_canon_promotion():
    novel = _make_novel(
        chapters={
            1: (
                "— Trụ ơi, tối rồi về ăn cơm với tao! "
                "Giọng A Mãnh, thằng bạn từ nhỏ, lẫn trong tiếng gió. "
                "— Sao mày không nói sớm?"
            )
        }
    )

    with pytest.raises(ReviewGateFailed) as exc_info:
        build_commit(novel, 1)

    assert exc_info.value.outcome == "language_guard"


def test_build_commit_blocks_strict_xianxia_profile_warning_before_promotion():
    novel = _make_novel(
        chapters={1: "Hắn mở hồ sơ, cân nhắc logic của vụ việc."}
    )

    with pytest.raises(ReviewGateFailed) as exc_info:
        build_commit(novel, 1)

    assert exc_info.value.outcome == "language_guard"


def test_score_only_review_passes_when_above_threshold():
    novel = _make_novel(reviews={1: "Đánh giá nhanh.\n\n**Điểm:** 88/100\n"})
    report = commit(novel, 1)
    assert report.gate_passed is True


def test_score_only_review_blocks_below_threshold():
    novel = _make_novel(reviews={1: "Đánh giá.\n\n**Điểm:** 80/100\n"})
    report = commit(novel, 1)
    assert report.gate_passed is False


def test_commit_promotes_draft_with_typed_review_and_writes_manifest():
    novel = _make_novel()
    (novel / "chapters" / "chapter_001.md").unlink()
    (novel / "drafts").mkdir()
    draft_path = novel / "drafts" / "chapter_0001.md"
    draft_path.write_text(_CHAPTER_TEXT + "\n\nBản draft mới.", encoding="utf-8")
    (novel / "drafts" / "chapter_0001.check.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "chapter": 1,
                "attempt": 1,
                "checks": {"format_integrity": "met"},
                "misses": [],
                "warnings": [],
            }
        ),
        encoding="utf-8",
    )
    _write_typed_review(novel, 1)

    report = commit(novel, 1)

    assert report.gate_passed is True
    assert report.blocked is False
    assert (novel / "chapters" / "chapter_001.md").read_text(encoding="utf-8") == (
        draft_path.read_text(encoding="utf-8")
    )
    manifest_path = (
        novel / "logs" / "transactions" / "chapter_0001_attempt_01" / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["source_draft"]["path"] == "drafts/chapter_0001.md"
    assert manifest["review"]["path"] == "reviews/chapter_0001_review.json"
    assert manifest["expected_canon_path"] == "chapters/chapter_001.md"
    assert manifest["status"] == "sync_completed"
    assert "canon_promoted" in manifest["completed_substeps"]
    assert "sync_completed" in manifest["completed_substeps"]
    assert "reviews/chapter_0001_review.json" in report.provenance


def test_typed_review_blocks_promotion_even_when_markdown_projection_passes():
    novel = _make_novel()
    (novel / "chapters" / "chapter_001.md").unlink()
    (novel / "drafts").mkdir()
    (novel / "drafts" / "chapter_0001.md").write_text(
        _CHAPTER_TEXT,
        encoding="utf-8",
    )
    _write_typed_review(novel, 1, gate="rewrite")

    report = commit(novel, 1)

    assert report.gate_passed is False
    assert report.blocked is True
    assert report.commit_id is None
    assert not (novel / "chapters" / "chapter_001.md").exists()


def test_human_approved_typed_review_promotes_despite_subbar_gate():
    """A ``human_approved`` stamp on the typed review lets a sub-bar chapter
    (gate_outcome=rewrite) promote to canon — the manual-approval valve."""
    novel = _make_novel()
    (novel / "chapters" / "chapter_001.md").unlink()
    (novel / "drafts").mkdir()
    (novel / "drafts" / "chapter_0001.md").write_text(_CHAPTER_TEXT, encoding="utf-8")
    (novel / "drafts" / "chapter_0001.check.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "chapter": 1,
                "attempt": 1,
                "checks": {"format_integrity": "met"},
                "misses": [],
                "warnings": [],
            }
        ),
        encoding="utf-8",
    )
    review_path = _write_typed_review(novel, 1, gate="rewrite")

    # Without approval the gate blocks.
    assert commit(novel, 1).blocked is True

    # Stamp human approval and re-run: the same draft now promotes.
    data = json.loads(review_path.read_text(encoding="utf-8"))
    data["human_approved"] = True
    review_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    report = commit(novel, 1)
    assert report.gate_passed is True
    assert report.blocked is False
    assert (novel / "chapters" / "chapter_001.md").exists()


def test_typed_review_blocks_when_rules_digest_changed_before_sync():
    novel = _make_novel()
    (novel / "chapters" / "chapter_001.md").unlink()
    (novel / "drafts").mkdir()
    (novel / "drafts" / "chapter_0001.md").write_text(
        _CHAPTER_TEXT,
        encoding="utf-8",
    )
    (novel / "PROJECT_DNA.rules.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "revision": 1,
                "rules": [
                    {
                        "rule_id": "user_0001",
                        "scope": "global",
                        "kind": "prohibition",
                        "text": "không dùng cấp bậc chữ cái",
                        "normalized": {
                            "target": "world_rank_naming",
                            "operator": "forbid",
                            "value": "letter_grade",
                        },
                        "enforcement": "hard",
                        "source": "runtime_user_update",
                        "created_at": "2026-06-29T00:00:00Z",
                    }
                ],
                "updated_at": "2026-06-29T00:00:00Z",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    original_digest = current_rules_digest(novel)
    _write_typed_review(novel, 1, rules_digest=original_digest)
    (novel / "PROJECT_DNA.rules.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "revision": 2,
                "rules": [
                    {
                        "rule_id": "user_0001",
                        "scope": "global",
                        "kind": "prohibition",
                        "text": "không dùng cấp bậc chữ cái",
                        "normalized": {
                            "target": "world_rank_naming",
                            "operator": "forbid",
                            "value": "letter_grade",
                        },
                        "enforcement": "hard",
                        "source": "runtime_user_update",
                        "created_at": "2026-06-29T00:00:00Z",
                    },
                    {
                        "rule_id": "user_0002",
                        "scope": "style",
                        "kind": "preference",
                        "text": "ưu tiên đối thoại ngắn",
                        "normalized": {
                            "target": "dialogue_style",
                            "operator": "prefer",
                            "value": "short_lines",
                        },
                        "enforcement": "preference",
                        "source": "runtime_user_update",
                        "created_at": "2026-06-29T01:00:00Z",
                    },
                ],
                "supersedes_revision": 1,
                "updated_at": "2026-06-29T01:00:00Z",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = commit(novel, 1)

    assert report.gate_passed is False
    assert report.blocked is True
    assert report.error == "typed review rules_digest does not match current rules"
    assert not (novel / "chapters" / "chapter_001.md").exists()


def test_recover_transaction_completes_ledger_after_canon_promoted():
    novel = _make_novel()
    (novel / "chapters" / "chapter_001.md").unlink()
    (novel / "drafts").mkdir()
    draft_path = novel / "drafts" / "chapter_0001.md"
    draft_path.write_text(_CHAPTER_TEXT + "\n\nBản draft recover.", encoding="utf-8")
    _write_typed_review(novel, 1)
    built = build_commit(novel, 1)
    canon_path = novel / "chapters" / "chapter_001.md"
    canon_path.write_text(draft_path.read_text(encoding="utf-8"), encoding="utf-8")
    manifest_path = (
        novel / "logs" / "transactions" / "chapter_0001_attempt_01" / "manifest.json"
    )
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "chapter": 1,
                "attempt": 1,
                "scope": "chapter_0001_attempt_01",
                "source_draft": {
                    "path": "drafts/chapter_0001.md",
                    "sha256": built.chapter_sha256,
                },
                "review": {
                    "path": "reviews/chapter_0001_review.json",
                    "sha256": built.review_sha256,
                },
                "expected_canon_path": "chapters/chapter_001.md",
                "expected_pre_write_hashes": {"chapters/chapter_001.md": None},
                "staged_output_hashes": {
                    "chapters/chapter_001.md": built.chapter_sha256
                },
                "commit_id": built.commit_id,
                "completed_substeps": ["validated", "canon_promoted"],
                "status": "running",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    report = recover_transactions(novel)

    commit_data = json.loads(
        (novel / ".commits" / "chapter_0001.commit.json").read_text(
            encoding="utf-8"
        )
    )
    recovered_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert report["recovered"] == ["chapter_0001_attempt_01"]
    assert commit_data["commit_id"] == built.commit_id
    assert recovered_manifest["status"] == "sync_completed"
    assert "commit_ledger_written" in recovered_manifest["completed_substeps"]
    assert "sync_completed" in recovered_manifest["completed_substeps"]


def test_recover_transaction_requires_user_resolution_on_canon_hash_mismatch():
    novel = _make_novel()
    (novel / "chapters" / "chapter_001.md").unlink()
    (novel / "drafts").mkdir()
    draft_path = novel / "drafts" / "chapter_0001.md"
    draft_path.write_text(_CHAPTER_TEXT + "\n\nBản draft recover.", encoding="utf-8")
    _write_typed_review(novel, 1)
    built = build_commit(novel, 1)
    canon_path = novel / "chapters" / "chapter_001.md"
    canon_path.write_text("Nội dung canon đã bị sửa ngoài transaction.", encoding="utf-8")
    manifest_path = (
        novel / "logs" / "transactions" / "chapter_0001_attempt_01" / "manifest.json"
    )
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "chapter": 1,
                "attempt": 1,
                "scope": "chapter_0001_attempt_01",
                "source_draft": {
                    "path": "drafts/chapter_0001.md",
                    "sha256": built.chapter_sha256,
                },
                "review": {
                    "path": "reviews/chapter_0001_review.json",
                    "sha256": built.review_sha256,
                },
                "expected_canon_path": "chapters/chapter_001.md",
                "expected_pre_write_hashes": {"chapters/chapter_001.md": None},
                "staged_output_hashes": {
                    "chapters/chapter_001.md": built.chapter_sha256
                },
                "commit_id": built.commit_id,
                "completed_substeps": ["validated", "canon_promoted"],
                "status": "running",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    report = recover_transactions(novel)

    recovered_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert report["recovered"] == []
    assert report["needs_user_resolution"] == [
        {
            "scope": "chapter_0001_attempt_01",
            "reason": "canon hash differs from transaction manifest",
        }
    ]
    assert recovered_manifest["status"] == "needs_user_resolution"
    assert recovered_manifest["resolution_reason"] == (
        "canon hash differs from transaction manifest"
    )
    assert not (novel / ".commits" / "chapter_0001.commit.json").exists()


# --------------------------------------------------------------------------- #
# Unit tests — commit lifecycle + 3-stage split
# --------------------------------------------------------------------------- #


def test_commit_runs_three_stages_in_order():
    novel = _make_novel()
    report = commit(novel, 1)
    stages = [s.stage for s in report.stages]
    # graph flag defaults ON now, so a 4th best-effort commit_graph stage
    # follows the original 3-stage split.
    assert stages == [
        SyncStageKind.COMMIT_LEDGER.value,
        SyncStageKind.COMMIT_INDEXES.value,
        SyncStageKind.COMMIT_AUDIT.value,
        "commit_graph",
    ]
    # Only stage 1 is blocking.
    assert report.stages[0].blocking is True
    assert report.stages[1].blocking is False
    assert report.stages[2].blocking is False
    assert report.stages[3].blocking is False


def test_accept_commit_is_content_addressed_idempotent():
    novel = _make_novel()
    built = build_commit(novel, 1)
    first, created1 = accept_commit(novel, built)
    second, created2 = accept_commit(novel, built)
    assert created1 is True
    assert created2 is False
    assert first.commit_id == second.commit_id


def test_planning_docs_upsert_is_idempotent():
    novel = _make_novel()
    built = build_commit(novel, 1)
    changed_first = update_planning_docs(novel, built)
    assert set(changed_first) == {"PLAN.md", "GOAL_TRACKER.md", "memory/Memory.md"}
    plan_after_first = (novel / "PLAN.md").read_text(encoding="utf-8")
    changed_second = update_planning_docs(novel, built)
    assert changed_second == []
    assert (novel / "PLAN.md").read_text(encoding="utf-8") == plan_after_first


def test_episodic_commit_records_chapter_fact():
    novel = _make_novel()
    built = build_commit(novel, 1)
    result = commit_episodic(novel, built)
    assert result["inserted"] >= 1
    # Re-committing the same fact is a no-op (idempotent layer-D write).
    again = commit_episodic(novel, built)
    assert again["inserted"] == 0


# --------------------------------------------------------------------------- #
# Unit tests — provenance (Requirement 11.5)
# --------------------------------------------------------------------------- #


def test_provenance_fingerprints_recorded_on_commit():
    novel = _make_novel()
    report = commit(novel, 1)
    assert report.provenance  # non-empty
    assert "chapters/chapter_001.md" in report.provenance
    stored = json.loads(
        (novel / ".commits" / "chapter_0001.commit.json").read_text(encoding="utf-8")
    )
    assert stored["provenance"]
    assert stored["provenance"]["chapters/chapter_001.md"] == report.provenance[
        "chapters/chapter_001.md"
    ]


# --------------------------------------------------------------------------- #
# Unit tests — doctor health-check (Requirement 18.3)
# --------------------------------------------------------------------------- #


def test_doctor_clean_novel_has_no_blocking_issues():
    novel = _make_novel()
    commit(novel, 1)
    issues = health_check(novel)
    assert classify_blocking(issues) == []


def test_doctor_flags_missing_required_path():
    novel = _make_novel()
    (novel / "PLAN.md").unlink()
    issues = health_check(novel)
    codes = {i.code for i in issues}
    assert "missing_path" in codes
    assert any(i.severity == "error" for i in classify_blocking(issues))


def test_doctor_flags_invalid_pipeline_status():
    novel = _make_novel()
    (novel / "logs" / "pipeline_status.json").write_text("{}", encoding="utf-8")
    issues = health_check(novel)
    assert "invalid_pipeline_status" in {i.code for i in issues}


def test_doctor_flags_blocked_status():
    novel = _make_novel(pipeline_status={"status": "blocked"})
    issues = health_check(novel)
    assert "blocked_tasks_present" in {i.code for i in issues}
    assert classify_blocking(issues)


def test_doctor_flags_open_breaker():
    novel = _make_novel(
        pipeline_status={
            "status": "running",
            "circuit_breaker": {
                "hard_fail_count": 2,
                "max_hard_fail": 2,
                "soft_fail_count": 0,
                "max_soft_fail": 3,
                "total_attempts": 2,
                "max_total": 5,
            },
        }
    )
    issues = health_check(novel)
    assert "breaker_open" in {i.code for i in issues}


def test_commit_blocks_when_doctor_blocking():
    """Requirement 11.2: sync blocks when the doctor still has a blocking issue."""
    novel = _make_novel(pipeline_status={"status": "blocked"})
    report = commit(novel, 1)
    assert report.gate_passed is True  # gate itself passed
    assert report.blocked is True  # but doctor blocks the sync
    assert report.blocking_issues


# --------------------------------------------------------------------------- #
# Unit tests — audit cadence + rotation + rolling seed
# --------------------------------------------------------------------------- #


def test_style_audit_runs_on_tenth_chapter():
    chapters = {ch: _CHAPTER_TEXT for ch in range(1, 11)}
    reviews = {ch: _PASSING_REVIEW for ch in range(1, 11)}
    novel = _make_novel(chapters=chapters, reviews=reviews)
    report = commit(novel, 10)
    assert report.style_audit is not None


def test_style_audit_skipped_off_cadence():
    novel = _make_novel()
    report = commit(novel, 1)
    assert report.style_audit is None


def test_rotation_runs_and_reports():
    novel = _make_novel()
    report = commit(novel, 1)
    assert report.rotation is not None
    assert report.rotation["rotated"] in (True, False)


def test_rolling_seed_handoff_when_state_supplied():
    chapters = {ch: _CHAPTER_TEXT for ch in range(1, 7)}
    reviews = {ch: _PASSING_REVIEW for ch in range(1, 7)}
    novel = _make_novel(chapters=chapters, reviews=reviews)
    engine = PipelineEngine.create(target_chapters=20, arc_size=50)
    report = commit(novel, 1, pipeline_state=engine.state.to_dict())
    assert report.seed is not None
    assert "state" in report.seed


# --------------------------------------------------------------------------- #
# Unit tests — tool entrypoint + self-registration
# --------------------------------------------------------------------------- #


def test_tool_is_self_registered():
    assert "novelkit_sync" in registry.list_tools()
    entry = registry.get("novelkit_sync")
    assert entry.fn is sync_tool
    assert entry.schema is not None


def test_sync_tool_commit_action():
    novel = _make_novel()
    out = sync_tool("commit", str(novel), chapter=1)
    assert out["gate_passed"] is True
    assert out["chapter"] == 1


def test_sync_tool_doctor_action():
    novel = _make_novel()
    commit(novel, 1)
    out = sync_tool("doctor", str(novel))
    assert "issues" in out
    assert "blocking_issues" in out


def test_sync_tool_unknown_action_raises():
    import pytest

    with pytest.raises(ValueError):
        sync_tool("nope", "/tmp/whatever")


def test_sync_tool_commit_requires_chapter():
    import pytest

    novel = _make_novel()
    with pytest.raises(ValueError):
        sync_tool("commit", str(novel))


# --------------------------------------------------------------------------- #
# Long-range continuity (open-loop payoff) doctor check
# --------------------------------------------------------------------------- #


def test_doctor_flags_overdue_payoff_as_nonblocking_warning():
    """An open loop whose deadline passed before the latest synced chapter is
    surfaced as a report-only warning (continuity drift the chapter gate can't
    see), never as a blocker."""
    from tools.novelkit_strand_tool import OpenLoopEvent, record_loop_event

    novel = _make_novel(
        chapters={1: _CHAPTER_TEXT, 2: _CHAPTER_TEXT},
        reviews={1: _PASSING_REVIEW, 2: _PASSING_REVIEW},
    )
    commit(novel, 1)
    commit(novel, 2)

    # A vow planted in ch1, promised payoff by ch2, but ch2 is the latest synced
    # chapter and the loop was never closed → overdue.
    record_loop_event(
        novel,
        OpenLoopEvent(
            event_id="loop-vow-1",
            event_type="open_loop_created",
            subject="lời thề chưa trả",
            chapter_planted=1,
            content="Hắn thề sẽ trả mối hận này.",
            loop_type="vow",
            urgency="high",
            expected_payoff=2,
            loop_deadline=1,
        ),
    )

    issues = health_check(novel)
    codes = {i.code for i in issues}
    assert "payoff_overdue" in codes
    # Continuity drift is advisory: it must not block the pipeline.
    assert all(i.code != "payoff_overdue" for i in classify_blocking(issues))


def test_doctor_clean_novel_has_no_payoff_warning():
    novel = _make_novel()
    commit(novel, 1)
    issues = health_check(novel)
    assert "payoff_overdue" not in {i.code for i in issues}


def test_doctor_flags_style_staleness_as_nonblocking_warning():
    """A style audit report carrying repetition flags surfaces a report-only
    'mòn văn phong' warning in the doctor — never a blocker."""
    import json as _json

    novel = _make_novel()
    commit(novel, 1)
    audit_dir = novel / "reviews" / "style_coherence"
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / "chapter_010_style_audit.json").write_text(
        _json.dumps(
            {
                "status": "warning",
                "chapter": 10,
                "repetition": {
                    "status": "warning",
                    "flags": {
                        "repeated_opening_line": {"current_opening": "Hắn mở mắt."}
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    issues = health_check(novel)
    codes = {i.code for i in issues}
    assert "style_staleness" in codes


# --------------------------------------------------------------------------- #
# stamp_human_approval — the "Duyệt tay" valve works at ANY blocking gate
# --------------------------------------------------------------------------- #


def test_stamp_human_approval_stamps_existing_review_json():
    """When a typed review already exists (chapter blocked at review/sync),
    the flag is stamped in place so the sync gate passes."""
    novel = _make_novel()
    (novel / "drafts").mkdir()
    (novel / "drafts" / "chapter_0001.md").write_text(_CHAPTER_TEXT, encoding="utf-8")
    review_path = _write_typed_review(novel, 1, gate="rewrite")

    result = stamp_human_approval(novel, 1, approver="tester@example.com")

    assert result == {"created": False, "stamped": True}
    data = json.loads(review_path.read_text(encoding="utf-8"))
    assert data["human_approved"] is True
    assert data["human_approved_by"] == "tester@example.com"


def test_stamp_human_approval_synthesises_review_when_missing():
    """When the chapter is blocked at self_check (before review ever ran) there
    is no review JSON — synthesise a valid, human-approved one bound to the
    current draft so sync can promote it. This is the self_check-block fix."""
    novel = _make_novel()
    (novel / "drafts").mkdir()
    (novel / "drafts" / "chapter_0001.md").write_text(_CHAPTER_TEXT, encoding="utf-8")
    review_file = novel / "reviews" / "chapter_0001_review.json"
    assert not review_file.exists()

    result = stamp_human_approval(novel, 1)

    assert result == {"created": True, "stamped": True}
    data = json.loads(review_file.read_text(encoding="utf-8"))
    assert data["human_approved"] is True
    # Bound to the exact draft + current rules so sync validation still passes.
    expected_sha = hashlib.sha256(
        (novel / "drafts" / "chapter_0001.md").read_bytes()
    ).hexdigest()
    assert data["draft_sha256"] == expected_sha
    assert data["rules_digest"] == current_rules_digest(novel)

    # The synthesised review actually lets the sync gate promote the chapter.
    (novel / "chapters" / "chapter_001.md").unlink()
    (novel / "drafts" / "chapter_0001.check.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "chapter": 1,
                "attempt": 1,
                "checks": {"format_integrity": "met"},
                "misses": [],
                "warnings": [],
            }
        ),
        encoding="utf-8",
    )
    report = commit(novel, 1)
    assert report.gate_passed is True
    assert report.blocked is False
    assert (novel / "chapters" / "chapter_001.md").exists()
