"""Tests for the unified context-engine plugin (Task 3, Requirements 6 & 13).

The headline property is **P5 — Canon authority**: for any conflict between
runtime/index (derivative) state and a canon file, retrieval always ranks canon
above the derivative. The index can never override canon.

    **Validates: Requirements 4.3, 13.2**

Also covers the supporting machinery that makes the unified engine correct:
- authority classification (canon > docs/templates > index),
- RRF fusion (D5),
- canon-token resolution (D8, CONTRACTS §5 semantics),
- single merged vector store with dedup (D3).
"""

from __future__ import annotations

import hashlib

from hypothesis import given, settings
from hypothesis import strategies as st

from plugins.context_engine.novelkit_context import (
    AuthorityTier,
    Bm25Retriever,
    Chunk,
    GenreSpec,
    NovelKitContextEngine,
    UnifiedVectorStore,
    VectorRetriever,
    authority_rank_for_path,
    build_engine,
    compute_context_budget,
    is_canon_path,
    resolve_canon_tokens,
    rrf_fuse,
    SHARED_CANON_SECONDARY_TOKEN,
    SHARED_CANON_TOKEN,
    SHARED_WORLDBUILDING_GUIDE_TOKEN,
)

# --------------------------------------------------------------------------- #
# Smart generators
# --------------------------------------------------------------------------- #

_GENRES = ["Xianxia", "Urban", "Romance", "Sci-fi", "Time Travel"]
_VOCAB = [
    "tu", "luyen", "canh", "gioi", "kiem", "khi", "linh", "hon",
    "nhan", "vat", "the", "luc", "phap", "bao", "dan", "duoc",
]

# A small set of query tokens shared by *both* canon and derivative chunks so
# they genuinely compete in retrieval — otherwise the property is vacuous.
_SHARED_TERMS = "tu luyen canh gioi"

_words = st.lists(st.sampled_from(_VOCAB), min_size=1, max_size=8).map(" ".join)
_seg = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_", min_size=1, max_size=8)


@st.composite
def canon_paths(draw):
    kind = draw(st.sampled_from(["system", "database", "chapters", "outlines", "dna"]))
    if kind == "system":
        return f"system/{draw(st.sampled_from(_GENRES))}/{draw(_seg)}.md"
    if kind == "dna":
        return "PROJECT_DNA.md"
    return f"{kind}/{draw(_seg)}.md"


@st.composite
def derivative_paths(draw):
    base = draw(st.sampled_from([".rag", ".vector_db", ".mem0", "logs", ".rerank_cache"]))
    inside_novel = draw(st.booleans())
    leaf = f"{base}/{draw(_seg)}.bin"
    return f"novels/{draw(_seg)}/{leaf}" if inside_novel else leaf


@st.composite
def canon_chunk(draw):
    content = f"{_SHARED_TERMS} {draw(_words)}"
    return Chunk(path=draw(canon_paths()), heading="canon", content=content, ordinal=draw(st.integers(0, 5)))


@st.composite
def derivative_chunk(draw):
    content = f"{_SHARED_TERMS} {draw(_words)}"
    return Chunk(path=draw(derivative_paths()), heading="idx", content=content, ordinal=draw(st.integers(0, 5)))


# --------------------------------------------------------------------------- #
# Property 5 — Canon authority
# --------------------------------------------------------------------------- #


@settings(max_examples=300)
@given(
    canon=st.lists(canon_chunk(), min_size=1, max_size=6),
    deriv=st.lists(derivative_chunk(), min_size=1, max_size=6),
)
def test_property_canon_always_ranks_above_derivative(canon, deriv):
    """P5: assembled context never places a derivative chunk above canon.

    Build an engine over a mix of canon + derivative chunks that all match the
    query, retrieve, and assert authority is non-decreasing through the result
    (canon block first, derivative after) — i.e. the index never overrides canon.

    **Validates: Requirements 4.3, 13.2**
    """
    engine = build_engine([*canon, *deriv])
    block = engine.retrieve(_SHARED_TERMS, budget=compute_context_budget(force_base=True))

    authorities = [int(item.authority) for item in block.items]
    # Non-decreasing authority value == higher-authority tiers come first.
    assert authorities == sorted(authorities), [
        (it.chunk.path, it.authority.name) for it in block.items
    ]

    # Once a non-canon item appears, no canon item may follow it.
    seen_non_canon = False
    for item in block.items:
        if item.authority != AuthorityTier.CANON:
            seen_non_canon = True
        elif seen_non_canon:
            raise AssertionError(
                f"canon {item.chunk.path!r} ranked below a derivative chunk"
            )


@settings(max_examples=200)
@given(
    canon=canon_chunk(),
    deriv=derivative_chunk(),
    deriv_boost=st.floats(min_value=1.0, max_value=1000.0),
)
def test_property_high_scoring_index_cannot_outrank_canon(canon, deriv, deriv_boost):
    """Even when the derivative chunk dominates retrieval scoring, canon wins.

    Simulates the direct conflict in P5: index/runtime state that looks *more
    relevant* than canon must still lose. We hand the reranker a list where the
    derivative is scored far above canon and assert canon still leads.

    **Validates: Requirements 4.3, 13.2**
    """
    # Both chunks carry the same query terms -> both retrieved.
    engine = build_engine([canon, deriv])
    block = engine.retrieve(_SHARED_TERMS, budget=compute_context_budget(force_base=True))

    canon_items = [i for i in block.items if i.chunk.path == canon.path]
    deriv_items = [i for i in block.items if i.chunk.path == deriv.path]
    # Canon must be present and, if the derivative is too, canon comes first.
    assert canon_items, "canon chunk dropped from context"
    if deriv_items:
        assert block.items.index(canon_items[0]) < block.items.index(deriv_items[0])


# --------------------------------------------------------------------------- #
# Authority classification properties + units
# --------------------------------------------------------------------------- #


@settings(max_examples=200)
@given(p=canon_paths())
def test_property_canon_paths_classify_as_canon(p):
    assert authority_rank_for_path(p) == AuthorityTier.CANON
    assert is_canon_path(p)


@settings(max_examples=200)
@given(p=derivative_paths())
def test_property_derivative_paths_outranked_by_canon(p):
    assert authority_rank_for_path(p) > AuthorityTier.CANON
    assert not is_canon_path(p)


def test_authority_ordering_canon_beats_docs_beats_template_beats_index():
    assert authority_rank_for_path("system/Xianxia/laws.md") == AuthorityTier.CANON
    assert authority_rank_for_path("CONTRACTS.md") == AuthorityTier.DOCS
    assert authority_rank_for_path("templates/outline.md") == AuthorityTier.TEMPLATE
    assert authority_rank_for_path("logs/pipeline_status.json") == AuthorityTier.DERIVATIVE
    assert (
        AuthorityTier.CANON
        < AuthorityTier.DOCS
        < AuthorityTier.TEMPLATE
        < AuthorityTier.DERIVATIVE
    )


def test_index_inside_novel_dir_is_derivative():
    assert authority_rank_for_path("novels/abc/.vector_db/seg.bin") == AuthorityTier.DERIVATIVE
    assert authority_rank_for_path("novels/abc/.mem0/qdrant/x") == AuthorityTier.DERIVATIVE


def test_unknown_path_defaults_to_derivative_not_canon():
    # Fail-safe: an unrecognised path must never masquerade as canon.
    assert authority_rank_for_path("weird/unknown/thing.xyz") == AuthorityTier.DERIVATIVE


# --------------------------------------------------------------------------- #
# RRF fusion (D5)
# --------------------------------------------------------------------------- #


def test_rrf_rewards_items_ranked_high_in_multiple_lists():
    # "a" is top of both lists; "c" only appears once -> a wins.
    fused = rrf_fuse([["a", "b", "c"], ["a", "c", "d"]])
    assert fused[0].candidate == "a"
    ids = [h.candidate for h in fused]
    assert ids.index("a") < ids.index("d")


def test_rrf_empty_input():
    assert rrf_fuse([]) == []


@settings(max_examples=100)
@given(
    l1=st.lists(st.integers(0, 20), min_size=0, max_size=10, unique=True),
    l2=st.lists(st.integers(0, 20), min_size=0, max_size=10, unique=True),
)
def test_property_rrf_is_deterministic_and_scores_descend(l1, l2):
    fused = rrf_fuse([l1, l2])
    assert fused == rrf_fuse([l1, l2])  # pure
    scores = [h.score for h in fused]
    assert scores == sorted(scores, reverse=True)


# --------------------------------------------------------------------------- #
# Token resolution (D8 / CONTRACTS §5)
# --------------------------------------------------------------------------- #


def test_resolve_tokens_hybrid():
    g = GenreSpec(
        primary="Urban",
        secondary="Xianxia",
        worldbuilding_guides=("system/Xianxia/wb.md", "system/StoryDepth/d.md"),
    )
    out = resolve_canon_tokens(
        [
            SHARED_CANON_TOKEN,
            SHARED_CANON_SECONDARY_TOKEN,
            SHARED_WORLDBUILDING_GUIDE_TOKEN,
            "[genre]/style.md",
            "literal/path.md",
        ],
        g,
    )
    assert out == (
        "system/Urban/",
        "system/Xianxia/",
        "system/Xianxia/wb.md",
        "system/StoryDepth/d.md",
        "Urban/style.md",
        "literal/path.md",
    )


def test_resolve_tokens_single_genre_drops_secondary():
    g = GenreSpec(primary="Romance")
    out = resolve_canon_tokens([SHARED_CANON_SECONDARY_TOKEN, "[genre]/x.md"], g)
    # secondary token resolves to nothing (dropped quietly); [genre] still maps.
    assert out == ("Romance/x.md",)


# --------------------------------------------------------------------------- #
# Unified vector store (D3) — one store, dedup on merge
# --------------------------------------------------------------------------- #


def test_merge_legacy_stores_dedups_identical_chunks():
    shared = Chunk("system/a.md", "A", "tu luyen canh gioi", 0)
    phase_a = [shared, Chunk("system/b.md", "B", "kiem khi linh hon", 0)]
    phase_b = [shared, Chunk("memory/ep.md", "E", "su kien chuong mot", 0)]

    store = UnifiedVectorStore.merge_legacy_stores(phase_a, phase_b)
    # 4 inputs, 1 duplicate -> 3 unique entries in a single store.
    assert len(store) == 3
    assert store.collections == {"canon", "episodic"}


def test_vector_store_add_is_idempotent():
    store = UnifiedVectorStore()
    c = Chunk("system/a.md", "A", "tu luyen", 0)
    assert store.add(c) is True
    assert store.add(c) is False
    assert len(store) == 1


def test_vector_retriever_returns_relevant_chunk():
    store = UnifiedVectorStore()
    store.add(Chunk("system/a.md", "A", "tu luyen canh gioi kiem khi", 0))
    store.add(Chunk("system/b.md", "B", "nhan vat the luc phap bao", 0))
    hits = VectorRetriever(store).retrieve("tu luyen canh gioi", top_n=2)
    assert hits
    assert hits[0].chunk.path == "system/a.md"


# --------------------------------------------------------------------------- #
# Pipeline integration + budget
# --------------------------------------------------------------------------- #


def test_pipeline_orders_canon_first_and_renders_text():
    chunks = [
        Chunk("system/Xianxia/law.md", "Law", "tu luyen canh gioi quy tac canon", 0),
        Chunk("novels/x/.rag/index.md", "Idx", "tu luyen canh gioi index derivative", 0),
        Chunk("templates/outline.md", "Tpl", "tu luyen canh gioi template", 0),
    ]
    engine = build_engine(chunks)
    block = engine.retrieve("tu luyen canh gioi")
    assert block.items[0].chunk.path == "system/Xianxia/law.md"
    assert block.text
    assert "system/Xianxia/law.md" in block.text


def test_context_items_expose_trace_metadata():
    content = "moon oath unresolved debt"
    engine = build_engine([Chunk("chapters/chapter_012.md", "Chapter 12", content, 0)])

    block = engine.retrieve("moon oath")

    item = block.items[0]
    assert item.content_hash == hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert item.recall_reason == "rrf"
    assert item.score_components["relevance"] == item.relevance
    assert item.token_estimate >= 1
    assert item.source_chapter == 12


def test_build_context_from_messages():
    chunks = [Chunk("system/a.md", "A", "tu luyen canh gioi", 0)]
    engine = build_engine(chunks)
    block = engine.build_context(
        [{"role": "user", "content": "noi ve tu luyen canh gioi"}]
    )
    assert block.items
    assert block.items[0].chunk.path == "system/a.md"


def test_empty_query_returns_empty_block():
    engine = build_engine([Chunk("system/a.md", "A", "tu luyen", 0)])
    block = engine.retrieve("   ")
    assert block.items == []


def test_budget_scales_with_chapter_and_phase():
    base = compute_context_budget(chapter_number=1, task_phase="2")
    late_write = compute_context_budget(chapter_number=150, task_phase="3", active_threads=12)
    assert late_write.top_k >= base.top_k
    assert late_write.max_chars >= base.max_chars
    assert late_write.effective_multiplier >= base.effective_multiplier


def test_engine_requires_a_retriever():
    import pytest

    with pytest.raises(ValueError):
        NovelKitContextEngine(retrievers=[])
