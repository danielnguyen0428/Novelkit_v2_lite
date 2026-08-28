"""Tests for the unified memory-provider plugin (Task 4, Requirements 13, 14).

Covers the two correctness properties owned by the memory provider:

* **Property 7 — Memory isolation** (Requirement 13.3): a memory operation on
  novel A never changes novel B's store.
    **Validates: Requirements 13.3**

* **Property 8 — Rotation invariant** (Requirements 11.3, 13.1): after rotate,
  active memory ≤ MEMORY_ACTIVE_MAX_WORDS and resolved state is preserved by
  moving it to the archive (total information conserved).
    **Validates: Requirements 11.3, 13.1**

Includes Hypothesis property tests over smart generators plus concrete unit
tests for the data model, episodic commit path, and five-layer authority.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from plugins.memory.novelkit_memory import (
    MEMORY_ACTIVE_MAX_WORDS,
    Category,
    DERIVATIVE_LAYERS,
    MemoryItem,
    MemoryLayer,
    NovelKitMemoryProvider,
    Status,
    dedupe_key,
    importance_score,
    normalize_relationship_subject,
    truncate_evidence,
    word_count,
)

_CATEGORIES = list(Category)
_RESOLVED = (Status.OUTDATED, Status.CONTRADICTED)
_LIVE = (Status.ACTIVE, Status.TENTATIVE)


# --------------------------------------------------------------------------- #
# Smart generators
# --------------------------------------------------------------------------- #

# A "word" for value bodies: keeps word_count() predictable and non-empty.
_word = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6)
_value_words = st.lists(_word, min_size=1, max_size=8).map(" ".join)


@st.composite
def item_specs(draw, *, min_size=1, max_size=20):
    """Generate a list of (category, status, value) specs.

    Subjects are made unique per index by the builder so every item has a
    distinct dedupe key (no accidental dedupe collapse), which keeps the
    information-conservation assertions exact.
    """
    n = draw(st.integers(min_value=min_size, max_value=max_size))
    cats = draw(st.lists(st.sampled_from(_CATEGORIES), min_size=n, max_size=n))
    statuses = draw(
        st.lists(st.sampled_from(list(Status)), min_size=n, max_size=n)
    )
    values = draw(st.lists(_value_words, min_size=n, max_size=n))
    return list(zip(cats, statuses, values))


def _build_items(specs) -> list[MemoryItem]:
    items: list[MemoryItem] = []
    for i, (category, status, value) in enumerate(specs):
        items.append(
            MemoryItem(
                id=f"id{i:04d}",
                category=category,
                subject=f"subj{i:04d}",
                field=f"f{i:04d}",
                value=value,
                payload={},
                status=status,
                source_chapter=i,
                source_commit_id=f"c{i}",
                evidence="",
            )
        )
    return items


# --------------------------------------------------------------------------- #
# Property 7 — Memory isolation between novels
# --------------------------------------------------------------------------- #


def _snapshot(store) -> tuple:
    live = sorted((i.id, i.value, i.status.value) for i in store.all_items())
    arch = sorted((i.id, i.value) for i in store.archived_items())
    return (tuple(live), tuple(arch))


@settings(max_examples=60, deadline=None)
@given(seed_b=item_specs(min_size=1, max_size=12), ops_a=item_specs(min_size=1, max_size=12))
def test_property_memory_isolation(seed_b, ops_a):
    """P7: operations on novel A never mutate novel B's store.

    **Validates: Requirements 13.3**
    """
    with tempfile.TemporaryDirectory() as root:
        base = Path(root)
        novel_a = base / "novelA"
        novel_b = base / "novelB"
        provider = NovelKitMemoryProvider()

        # Seed B and snapshot it.
        provider.store(novel_b).upsert_many(_build_items(seed_b))
        before_b = _snapshot(provider.store(novel_b))

        # Drive a varied workload against A only — reusing B's subjects on
        # purpose to prove names don't bleed across novels.
        a_items = _build_items(ops_a)
        for item in a_items:
            provider.add(item, scope=novel_a)
        provider.commit_episodic(
            scope=novel_a,
            memory_facts=[{"category": "story_facts", "subject": "x", "field": "y", "value": "z"}],
            chapter=1,
        )
        provider.search("subj", scope=novel_a)
        provider.build_context("subj0000", scope=novel_a, max_tokens=50)
        provider.rotate(scope=novel_a, max_words=1)

        # B must be byte-for-byte identical.
        after_b = _snapshot(provider.store(novel_b))
        assert after_b == before_b

        # And the two novels resolve to different store files.
        assert provider.store(novel_a).db_path != provider.store(novel_b).db_path


def test_isolation_distinct_store_files():
    """Two novels never share a store file (structural isolation)."""
    with tempfile.TemporaryDirectory() as root:
        provider = NovelKitMemoryProvider()
        a = provider.store(Path(root) / "a")
        b = provider.store(Path(root) / "b")
        assert a.db_path != b.db_path
        assert a.db_path.exists() and b.db_path.exists()


# --------------------------------------------------------------------------- #
# Property 8 — Rotation invariant
# --------------------------------------------------------------------------- #


@settings(max_examples=100, deadline=None)
@given(specs=item_specs(min_size=1, max_size=25), max_words=st.integers(min_value=0, max_value=60))
def test_property_rotation_invariant(specs, max_words):
    """P8: after rotate, active ≤ max_words and no information is lost.

    **Validates: Requirements 11.3, 13.1**
    """
    with tempfile.TemporaryDirectory() as root:
        provider = NovelKitMemoryProvider()
        novel = Path(root) / "novel"
        store = provider.store(novel)

        items = _build_items(specs)
        store.upsert_many(items)

        before_live_ids = {i.id for i in store.all_items()}
        resolved_before = {i.id for i in store.all_items() if i.status in _RESOLVED}
        words_before = store.active_word_count()

        report = provider.rotate(scope=novel, max_words=max_words)

        live_after = {i.id for i in store.all_items()}
        archive_after = {i.id for i in store.archived_items()}
        words_after = store.active_word_count()

        if words_before <= max_words:
            # Nothing to do: store untouched.
            assert report.rotated is False
            assert live_after == before_live_ids
            assert archive_after == set()
        else:
            assert report.rotated is True
            # 1) Active memory respects the word cap.
            assert words_after <= max_words
            # 2) Total information conserved: nothing dropped on the floor.
            assert live_after | archive_after == before_live_ids
            assert live_after & archive_after == set()
            # 3) Resolved state is always moved to the archive.
            assert resolved_before <= archive_after
            # 4) Report counts are consistent with what moved.
            assert report.archived_total == len(archive_after)


@settings(max_examples=50, deadline=None)
@given(specs=item_specs(min_size=0, max_size=15))
def test_property_rotation_default_threshold_is_noop_for_small_stores(specs):
    """Below the 3500-word default cap, rotation is a no-op.

    **Validates: Requirements 11.3, 13.1**
    """
    with tempfile.TemporaryDirectory() as root:
        provider = NovelKitMemoryProvider()
        novel = Path(root) / "novel"
        store = provider.store(novel)
        if specs:
            store.upsert_many(_build_items(specs))
        before = {i.id for i in store.all_items()}
        report = provider.rotate(scope=novel)  # default MEMORY_ACTIVE_MAX_WORDS
        assert report.rotated is False
        assert {i.id for i in store.all_items()} == before
        assert store.archived_items() == []


def test_rotation_preserves_resolved_state_unit():
    """Concrete rotation: resolved items archived, active trimmed, no loss."""
    with tempfile.TemporaryDirectory() as root:
        provider = NovelKitMemoryProvider()
        novel = Path(root) / "novel"
        store = provider.store(novel)

        items = [
            MemoryItem(id="a", category=Category.STORY_FACTS, subject="s1",
                       field="f", value="one two three", status=Status.ACTIVE),
            MemoryItem(id="b", category=Category.STORY_FACTS, subject="s2",
                       field="f", value="four five six", status=Status.OUTDATED),
            MemoryItem(id="c", category=Category.STORY_FACTS, subject="s3",
                       field="f", value="seven eight", status=Status.CONTRADICTED),
        ]
        store.upsert_many(items)
        before_ids = {i.id for i in store.all_items()}

        report = provider.rotate(scope=novel, max_words=4)

        assert report.rotated is True
        archive_ids = {i.id for i in store.archived_items()}
        live_ids = {i.id for i in store.all_items()}
        # Resolved (b, c) must be in the archive.
        assert {"b", "c"} <= archive_ids
        # Nothing lost.
        assert live_ids | archive_ids == before_ids
        assert store.active_word_count() <= 4


# --------------------------------------------------------------------------- #
# Unit tests: data model + helpers
# --------------------------------------------------------------------------- #


def test_dedupe_key_subject_field_vs_subject_only():
    sf = MemoryItem(id="1", category=Category.CHARACTER_STATE, subject="Han",
                    field="realm", value="x")
    so = MemoryItem(id="2", category=Category.OPEN_LOOPS, subject="debt",
                    field="ignored", value="y")
    assert dedupe_key(sf) == "character_state:Han:realm"
    assert dedupe_key(so) == "open_loops:debt"


def test_normalize_relationship_subject_is_order_independent():
    assert normalize_relationship_subject("B", "a") == normalize_relationship_subject("a", "B")


def test_truncate_evidence_hashes_overflow():
    short, patch = truncate_evidence("ok")
    assert short == "ok" and patch is None
    long_text = "x" * 400
    trimmed, patch = truncate_evidence(long_text)
    assert len(trimmed) == 280
    assert patch and "evidence_ref" in patch


def test_word_count_unicode():
    assert word_count("Hàn Lập đột phá cảnh giới") == 6


# --------------------------------------------------------------------------- #
# Unit tests: upsert / dedupe / contradiction semantics
# --------------------------------------------------------------------------- #


def test_add_is_idempotent_for_identical_value():
    with tempfile.TemporaryDirectory() as root:
        provider = NovelKitMemoryProvider()
        novel = Path(root) / "n"
        fact = {"category": "character_state", "subject": "Han", "field": "realm",
                "value": "Foundation"}
        provider.add(fact, scope=novel)
        provider.add(fact, scope=novel)
        active = provider.store(novel).iter_active()
        assert len(active) == 1


def test_contradiction_when_both_high_confidence():
    with tempfile.TemporaryDirectory() as root:
        provider = NovelKitMemoryProvider()
        novel = Path(root) / "n"
        provider.add({"category": "world_rules", "subject": "qi", "field": "law",
                      "value": "A", "confidence": 0.9}, scope=novel)
        res = provider.add({"category": "world_rules", "subject": "qi", "field": "law",
                            "value": "B", "confidence": 0.9}, scope=novel)
        assert res.contradicted == 2
        statuses = {i.status for i in provider.store(novel).all_items()}
        assert Status.CONTRADICTED in statuses


def test_low_confidence_outdates_existing():
    with tempfile.TemporaryDirectory() as root:
        provider = NovelKitMemoryProvider()
        novel = Path(root) / "n"
        provider.add({"category": "character_state", "subject": "Han", "field": "mood",
                      "value": "calm"}, scope=novel)
        res = provider.add({"category": "character_state", "subject": "Han", "field": "mood",
                            "value": "angry"}, scope=novel)
        assert res.outdated == 1 and res.updated == 1
        active = provider.store(novel).iter_active()
        assert len(active) == 1 and active[0].value == "angry"


# --------------------------------------------------------------------------- #
# Unit tests: episodic commit (writer_v2 path) + five-layer authority
# --------------------------------------------------------------------------- #


def test_commit_episodic_facts_and_state_deltas():
    with tempfile.TemporaryDirectory() as root:
        provider = NovelKitMemoryProvider()
        novel = Path(root) / "n"
        res = provider.commit_episodic(
            scope=novel,
            memory_facts=[
                {"category": "story_facts", "subject": "battle", "field": "outcome",
                 "value": "won"},
            ],
            state_deltas={
                "character_state": [
                    {"subject": "Han", "field": "hp", "value": "low"},
                ],
                "timeline": {"subject": "day", "event": "duel"},
            },
            chapter=7,
        )
        assert res.inserted == 3
        items = provider.store(novel).all_items()
        assert all(i.source_chapter == 7 for i in items)


def test_commit_episodic_skips_invalid_facts():
    with tempfile.TemporaryDirectory() as root:
        provider = NovelKitMemoryProvider()
        novel = Path(root) / "n"
        res = provider.commit_episodic(
            scope=novel,
            memory_facts=[
                {"category": "bogus", "subject": "x", "field": "y", "value": "z"},
                {"category": "story_facts", "subject": "", "field": "y", "value": "z"},
            ],
            chapter=1,
        )
        assert res.inserted == 0


def test_canon_layer_is_authoritative_others_derivative():
    """Layer A (canon) is source of truth; B-E are derivative (P5/Req 13.2)."""
    provider = NovelKitMemoryProvider()
    assert provider.can_override_canon(MemoryLayer.A_CANON) is True
    for layer in (MemoryLayer.B_RAG, MemoryLayer.C_VECTOR, MemoryLayer.D_EPISODIC,
                  MemoryLayer.E_CURATED):
        assert provider.is_derivative(layer) is True
        assert provider.can_override_canon(layer) is False
    assert MemoryLayer.A_CANON not in DERIVATIVE_LAYERS


def test_importance_score_prefers_callbacks_and_durable_categories():
    callback = MemoryItem(id="1", category=Category.OPEN_LOOPS, subject="debt",
                          field="status", value="lời thề chưa trả nợ")
    trivial = MemoryItem(id="2", category=Category.STORY_FACTS, subject="weather",
                         field="note", value="sunny")
    assert importance_score(callback) > importance_score(trivial)


def test_build_context_respects_token_budget_and_constraints():
    with tempfile.TemporaryDirectory() as root:
        provider = NovelKitMemoryProvider()
        novel = Path(root) / "n"
        provider.add({"category": "world_rules", "subject": "qi", "field": "law",
                      "value": "qi flows downward"}, scope=novel)
        provider.add({"category": "character_state", "subject": "Han", "field": "realm",
                      "value": "Foundation stage cultivation"}, scope=novel)
        pack = provider.build_context("Han cultivation", scope=novel, max_tokens=3)
        # Constraints (world rules) are always present.
        assert len(pack.active_constraints) == 1
        # Semantic slice obeys the small budget.
        sem_tokens = sum(len((d["value"]).split()) for d in pack.semantic_memory)
        assert sem_tokens <= 3
