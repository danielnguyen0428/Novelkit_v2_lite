"""NovelKit context-engine plugin (single-select) for Hermes.

Phase 2 of the migration: this module **unifies** the legacy NovelKit retrieval
subsystem — ``rag_context.py`` (BM25/FTS over markdown), ``vector_db.py``
(Qdrant semantic search), ``reranker*.py`` (remote rerankers), ``rrf.py``
(reciprocal rank fusion) and ``adaptive_context.py`` (budget scaling) — into a
*single* context engine that implements the Hermes ``ContextEngine`` ABC.

Design references:
- design.md §"Components and Interfaces" #12 (``novelkit_context``).
- design.md §"Creative Asset Audit & Standardization" findings D3, D5, D8.
- design.md §"Correctness Properties" P5 (Canon authority).

What this consolidates
----------------------
- **D5 — multi-layer retrieval collapsed into one pipeline:**
  ``retrieve (BM25 + vector) → fuse (RRF) → rerank → budget``. graph retrieval
  stays an optional channel that can be plugged in, never a separate engine.
- **D3 — one vector store:** the Phase A ``.vector_db`` (canon/worldbuilding)
  and Phase B ``.mem0/qdrant`` (episodic) stores are merged into a single
  :class:`UnifiedVectorStore`; duplicate chunks are dropped on merge.
- **D8 — token resolution moved here:** ``@shared_canon`` /
  ``@shared_canon_secondary`` / ``@worldbuilding_guide`` / ``[genre]`` resolve
  in the context engine (and skill loader), not in the old control plane, while
  preserving CONTRACTS §5 semantics.

Authority invariant (P5)
------------------------
Canon (the file-first source of truth) always outranks derivative state
(RAG/vector indexes, runtime logs, templates, docs). No matter how high a
derivative chunk scores in retrieval/rerank, a canon chunk is placed above it
in the assembled context. This is enforced by sorting the final candidate set
by ``(authority_rank, -relevance)`` — authority dominates, relevance only
breaks ties *within* a tier.

The module is intentionally dependency-free (stdlib only) so the plugin is
verifiable in isolation. Real Hermes deployments inject concrete retrievers
(FTS5 / Qdrant) and a remote reranker; the in-memory defaults here mirror the
legacy algorithms faithfully enough to test the contract.
"""

from __future__ import annotations

import abc
import hashlib
import math
import re
import unicodedata
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import PurePosixPath
from typing import Iterable, Optional, Protocol, Sequence, runtime_checkable

# --------------------------------------------------------------------------- #
# Constants (ported from cp_constants.py / rag_context.py / adaptive_context.py)
# --------------------------------------------------------------------------- #

# Canon-token vocabulary (CONTRACTS §5). Kept byte-for-byte identical to the
# legacy values so existing PROJECT_DNA / task definitions keep resolving.
SHARED_CANON_TOKEN = "@shared_canon"
SHARED_CANON_SECONDARY_TOKEN = "@shared_canon_secondary"
SHARED_WORLDBUILDING_GUIDE_TOKEN = "@worldbuilding_guide"
GENRE_PLACEHOLDER = "[genre]"

# RRF fusion default (rrf.py).
RRF_K = 60

# Retrieval defaults (rag_context.py).
DEFAULT_TOP_K = 8
DEFAULT_MAX_CHARS = 16_000

# Adaptive budget base/caps (adaptive_context.py).
BASE_RAG_CHARS = 7_000
BASE_TOP_K = 8
MAX_RAG_CHARS = 16_000
MAX_TOP_K = 20

PHASE_MULTIPLIERS = {
    "1": 0.8,      # bootstrap
    "2": 1.0,      # outline
    "3": 1.2,      # write — needs most context for continuity
    "4": 1.0,      # review
    "sync": 0.6,   # sync — mostly writes metadata
}

# (max_chapter, multiplier) — story complexity grows with length.
COMPLEXITY_TIERS = (
    (10, 1.0),
    (30, 1.1),
    (60, 1.25),
    (100, 1.4),
    (200, 1.6),
    (999_999, 1.8),
)


# --------------------------------------------------------------------------- #
# Authority model (Property 5: canon > derivative)
# --------------------------------------------------------------------------- #


class AuthorityTier(IntEnum):
    """Authority tiers. Lower value == higher authority.

    Canon is the file-first source of truth and always wins. Everything below
    it is derivative state that *describes* or *indexes* canon and must never
    override it (CONTRACTS §1 "disk beats chat", Requirement 13.2).
    """

    CANON = 0          # PROJECT_DNA, system/<genre>, database, chapters, outlines…
    CURATED = 1        # curated long-term memory (Memory.md / MEMORY.md)
    DOCS = 2           # standard reference docs (CONTRACTS, API, STYLE_GUIDE…)
    TEMPLATE = 3       # templates / scaffolds
    DERIVATIVE = 4     # runtime/index state: RAG, vector, logs, caches


# Index / runtime-generated state. These are derived from canon and may be
# stale; they are the lowest authority and can never beat a canon chunk.
_DERIVATIVE_PREFIXES = (
    ".rag/",
    ".rag.sqlite3",
    ".vector_db/",
    ".vector_db",
    ".mem0/",
    ".mem0",
    ".rerank_cache",
    ".controlplane",
    ".cp/",
    "logs/",
)

# File-first canon. The owner-of-truth for narrative state.
_CANON_PREFIXES = (
    "novels/",
    "system/",
    "database/",
    "memory/",
    "outlines/",
    "summaries/",
    "chapters/",
    "reviews/",
    "style_vault/",
)

_DOC_NAMES = frozenset(
    {
        "readme.md",
        "readme.vi.md",
        "architecture.md",
        "api.md",
        "contracts.md",
        "runbook.md",
        "glossary.md",
        "identity.md",
        "style_guide.md",
    }
)

_TEMPLATE_PREFIXES = ("templates/", "scripts/")


def _normalize_rel_path(path: str) -> str:
    """Lower-cased, forward-slashed, leading-``./`` stripped path."""
    return str(path).replace("\\", "/").lstrip("./").lower()


def authority_rank_for_path(path: str) -> AuthorityTier:
    """Classify a source path into an :class:`AuthorityTier`.

    Ordering of checks is most-specific-first. Unknown paths default to
    :data:`AuthorityTier.DERIVATIVE` so an unrecognised source can never be
    silently treated as authoritative canon (fail safe for P5).
    """
    normalized = _normalize_rel_path(path)
    name = PurePosixPath(normalized).name

    # PROJECT_DNA is the contract root — highest canon.
    if name == "project_dna.md":
        return AuthorityTier.CANON

    # Index / runtime state is checked before canon prefixes because some
    # derived stores live *inside* a novel dir (e.g. novels/x/.vector_db/...).
    if any(normalized.startswith(p) or f"/{p}" in normalized for p in _DERIVATIVE_PREFIXES):
        return AuthorityTier.DERIVATIVE

    # Canon prefixes are checked BEFORE the curated-memory name rule: a file
    # that lives under a canon prefix is canon whatever it is called. Matching
    # the bare name first demoted real canon (e.g. ``system/<Pack>/memory.md``)
    # to CURATED, letting derivative context outrank it in _assemble.
    if normalized.startswith(_CANON_PREFIXES):
        return AuthorityTier.CANON

    # Curated long-term memory note (a root-level Memory.md, distinct from both
    # the canon ``memory/`` dir and any canon-prefixed file named memory.md).
    if name == "memory.md":
        return AuthorityTier.CURATED

    if normalized.startswith(_TEMPLATE_PREFIXES):
        return AuthorityTier.TEMPLATE

    if name in _DOC_NAMES:
        return AuthorityTier.DOCS

    return AuthorityTier.DERIVATIVE


def is_canon_path(path: str) -> bool:
    """True when ``path`` is file-first canon (the source of truth)."""
    return authority_rank_for_path(path) == AuthorityTier.CANON


# --------------------------------------------------------------------------- #
# Reciprocal Rank Fusion (ported verbatim in behaviour from rrf.py)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class FusedHit:
    """A candidate after RRF fusion with its fused score."""

    candidate: object
    score: float


def rrf_fuse(
    ranked_lists: Sequence[Sequence[object]],
    k: int = RRF_K,
    top_n: Optional[int] = None,
) -> list[FusedHit]:
    """Combine multiple ranked lists using Reciprocal Rank Fusion.

    ``score(d) = sum over lists of 1 / (k + rank_in_list(d))`` with 1-indexed
    ranks. A candidate absent from a list contributes zero from that list.
    Ties break by rank in the first input list (lowest rank wins). Pure
    function — same input always yields the same output.
    """
    if not ranked_lists:
        return []

    scores: dict[object, float] = {}
    first_list_rank: dict[object, int] = {}

    for list_idx, ranked_list in enumerate(ranked_lists):
        for rank_0, candidate in enumerate(ranked_list):
            rank = rank_0 + 1
            scores[candidate] = scores.get(candidate, 0.0) + 1.0 / (k + rank)
            if list_idx == 0 and candidate not in first_list_rank:
                first_list_rank[candidate] = rank

    default_rank = (len(ranked_lists[0]) if ranked_lists else 0) + 1
    ordered = sorted(
        scores.items(),
        key=lambda item: (-item[1], first_list_rank.get(item[0], default_rank)),
    )
    if top_n is not None:
        ordered = ordered[:top_n]
    return [FusedHit(candidate=c, score=s) for c, s in ordered]


# --------------------------------------------------------------------------- #
# Adaptive context budget (ported from adaptive_context.py)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ContextBudget:
    """Computed retrieval budget for a task. Higher chapters / busier stories
    get more room, capped to avoid context-window overflow."""

    max_chars: int = DEFAULT_MAX_CHARS
    top_k: int = DEFAULT_TOP_K
    effective_multiplier: float = 1.0
    reasoning: str = ""


def _chapter_multiplier(chapter: int) -> float:
    for max_ch, mult in COMPLEXITY_TIERS:
        if chapter <= max_ch:
            return mult
    return COMPLEXITY_TIERS[-1][1]


def compute_context_budget(
    chapter_number: int = 1,
    task_phase: str = "3",
    *,
    active_entities: int = 0,
    active_threads: int = 0,
    force_base: bool = False,
) -> ContextBudget:
    """Scale the retrieval budget by chapter complexity + phase + load.

    Mirrors ``adaptive_context.compute_context_budget`` but takes the
    complexity signals (entity/thread counts) as plain arguments so it stays
    pure and engine-agnostic; the host supplies them from the novel state.
    """
    if force_base:
        return ContextBudget(
            max_chars=BASE_RAG_CHARS,
            top_k=BASE_TOP_K,
            effective_multiplier=1.0,
            reasoning="force base budget (adaptive disabled)",
        )

    ch_mult = _chapter_multiplier(max(1, chapter_number))
    phase_mult = PHASE_MULTIPLIERS.get(str(task_phase), 1.0)

    if active_entities <= 3:
        ent_mult = 1.0
    elif active_entities <= 6:
        ent_mult = 1.1
    elif active_entities <= 10:
        ent_mult = 1.2
    elif active_entities <= 15:
        ent_mult = 1.3
    else:
        ent_mult = 1.4

    if active_threads <= 3:
        plt_mult = 1.0
    elif active_threads <= 6:
        plt_mult = 1.1
    elif active_threads <= 10:
        plt_mult = 1.2
    else:
        plt_mult = 1.3

    # Geometric mean of the four factors keeps scaling gentle; floor at 1.0
    # (never shrink below base). The geometric mean of N factors is the Nth
    # root of their product — with four factors that is ``** (1/4)``; the prior
    # ``** 0.5`` was a square root that systematically over-scaled the budget.
    effective = max(1.0, (ch_mult * phase_mult * ent_mult * plt_mult) ** 0.25)

    max_chars = min(MAX_RAG_CHARS, int(BASE_RAG_CHARS * effective))
    top_k = min(MAX_TOP_K, max(1, int(BASE_TOP_K * effective)))

    return ContextBudget(
        max_chars=max_chars,
        top_k=top_k,
        effective_multiplier=round(effective, 3),
        reasoning=(
            f"ch{chapter_number} x{ch_mult:.2f} | phase {task_phase} x{phase_mult:.2f} | "
            f"entities {active_entities} x{ent_mult:.2f} | threads {active_threads} "
            f"x{plt_mult:.2f} | effective x{effective:.2f}"
        ),
    )


# --------------------------------------------------------------------------- #
# Token resolution (D8 — ported from cp_genre.resolve_task_paths)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class GenreSpec:
    """Resolved genre configuration for a novel (canon folder names).

    ``primary`` is always set. ``secondary`` is populated for hybrid novels.
    ``worldbuilding_guides`` are workspace-relative guide paths selected for
    the novel (depth/style/worldbuilding); they back ``@worldbuilding_guide``.
    """

    primary: str
    secondary: Optional[str] = None
    ratio: Optional[str] = None
    worldbuilding_guides: tuple[str, ...] = ()

    @property
    def is_hybrid(self) -> bool:
        return self.secondary is not None


def resolve_canon_tokens(
    paths: Iterable[str],
    genre: GenreSpec,
) -> tuple[str, ...]:
    """Resolve canon tokens in ``paths`` against a :class:`GenreSpec`.

    Preserves CONTRACTS §5 semantics from ``cp_genre.resolve_task_paths``:

    - ``@shared_canon``           → ``system/<primary>/``
    - ``@shared_canon_secondary`` → ``system/<secondary>/`` (dropped if single-genre)
    - ``@worldbuilding_guide``    → the novel's selected guide paths
    - ``[genre]`` substring       → replaced with the primary canon folder

    A secondary token on a single-genre novel resolves to nothing (dropped
    quietly) so single-genre pipelines keep working — matching the legacy
    "token resolve fail → drop quietly" rule (design §Error Handling).
    """
    resolved: list[str] = []
    for path in paths:
        if path == SHARED_CANON_TOKEN:
            resolved.append(f"system/{genre.primary}/")
        elif path == SHARED_CANON_SECONDARY_TOKEN:
            if genre.secondary:
                resolved.append(f"system/{genre.secondary}/")
            # else: drop quietly (single-genre novel).
        elif path == SHARED_WORLDBUILDING_GUIDE_TOKEN:
            resolved.extend(genre.worldbuilding_guides)
        elif GENRE_PLACEHOLDER in path:
            resolved.append(path.replace(GENRE_PLACEHOLDER, genre.primary))
        else:
            resolved.append(path)
    return tuple(resolved)


# --------------------------------------------------------------------------- #
# Retrieval primitives
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Chunk:
    """An indexable unit of canon or derivative text.

    ``chunk_id`` is content-addressed so the *same* chunk indexed by two
    legacy stores collapses to one entry on merge (D3 dedup).
    """

    path: str
    heading: str
    content: str
    ordinal: int = 0

    @property
    def chunk_id(self) -> str:
        raw = f"{_normalize_rel_path(self.path)}:{self.ordinal}:{self.content}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @property
    def authority(self) -> AuthorityTier:
        return authority_rank_for_path(self.path)


#: Target size of one split chunk, in characters. Sized so a retrieval budget
#: of ~7-12K chars fits 6-10 distinct chunks: small enough that several
#: *different* sources survive the budget, large enough that a canon rule keeps
#: its surrounding context.
SPLIT_TARGET_CHARS = 1_200

#: Overlap carried from the previous slice when one section must be cut further.
#: Prevents a rule that straddles the cut from being lost from both halves.
SPLIT_OVERLAP_CHARS = 120

#: A section shorter than this is merged into the next one instead of being
#: indexed alone: a bare heading has no retrievable substance of its own.
SPLIT_MIN_CHARS = 200

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


def _split_oversized(text: str, target: int, overlap: int) -> list[str]:
    """Cut ``text`` into <= ``target`` slices on paragraph, then line, bounds.

    Only called for a single section that is already larger than ``target``.
    Splits on the last blank line before the limit so prose is not cut
    mid-sentence; falls back to the last newline, then to a hard cut when one
    "paragraph" is itself oversized (e.g. a long table).
    """
    slices: list[str] = []
    rest = text
    while len(rest) > target:
        window = rest[:target]
        cut = window.rfind("\n\n")
        if cut < target // 3:
            cut = window.rfind("\n")
        if cut < target // 3:
            cut = target
        slices.append(rest[:cut].strip())
        rest = rest[max(0, cut - overlap):].lstrip()
    if rest.strip():
        slices.append(rest.strip())
    return [s for s in slices if s]


def split_markdown(
    path: str,
    text: str,
    *,
    target: int = SPLIT_TARGET_CHARS,
    overlap: int = SPLIT_OVERLAP_CHARS,
    min_chars: int = SPLIT_MIN_CHARS,
) -> list[Chunk]:
    """Split one markdown document into retrievable :class:`Chunk` units.

    Indexing a whole file as a single chunk makes the retrieval budget
    meaningless: one 74K-char consistency-rules file either consumes the entire
    budget or is dropped whole, so a query can never surface *the* relevant
    section. Splitting on markdown headings gives retrieval something the size
    of an actual answer.

    Each chunk keeps its heading trail (``Parent > Child``) as ``heading`` so the
    assembled context still says where the text came from, and a monotonic
    ``ordinal`` so two identical sections in one file stay distinct chunks
    (``Chunk.chunk_id`` mixes ``ordinal`` in).

    Returns a single chunk for short or heading-less documents, so plain-text
    sources behave exactly as before.
    """
    body = (text or "").strip()
    if not body:
        return []
    stem = PurePosixPath(str(path)).stem
    if len(body) <= target:
        return [Chunk(path=str(path), heading=stem, content=body)]

    # Build (heading_trail, section_text) pairs from the heading structure.
    matches = list(_HEADING_RE.finditer(body))
    sections: list[tuple[str, str]] = []
    if not matches or matches[0].start() > 0:
        preamble = body[: matches[0].start()] if matches else body
        if preamble.strip():
            sections.append((stem, preamble.strip()))
    trail: list[str] = []
    for i, m in enumerate(matches):
        level = len(m.group(1))
        title = m.group(2).strip()
        del trail[level - 1:]
        trail.append(title)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        section = body[m.start():end].strip()
        if section:
            sections.append((" > ".join(t for t in trail if t) or stem, section))

    # Merge runs of tiny sections so a bare heading is never indexed alone.
    merged: list[tuple[str, str]] = []
    for heading, section in sections:
        if (
            merged
            and len(merged[-1][1]) < min_chars
            and len(merged[-1][1]) + len(section) <= target
        ):
            prev_heading, prev_section = merged[-1]
            merged[-1] = (prev_heading, f"{prev_section}\n\n{section}")
        else:
            merged.append((heading, section))

    chunks: list[Chunk] = []
    ordinal = 0
    for heading, section in merged:
        pieces = (
            [section]
            if len(section) <= target
            else _split_oversized(section, target, overlap)
        )
        for piece in pieces:
            chunks.append(
                Chunk(
                    path=str(path),
                    heading=f"{stem} — {heading}" if heading != stem else stem,
                    content=piece,
                    ordinal=ordinal,
                )
            )
            ordinal += 1
    return chunks or [Chunk(path=str(path), heading=stem, content=body)]


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk returned by a retrieval channel with a per-channel score.

    Higher ``score`` == more relevant within that channel.
    """

    chunk: Chunk
    score: float
    channel: str


@dataclass(frozen=True)
class ContextItem:
    """One assembled context entry after fuse + rerank + authority ranking."""

    chunk: Chunk
    relevance: float          # fused/reranked relevance (higher = better)
    authority: AuthorityTier
    content_hash: str = ""
    recall_reason: str = ""
    score_components: dict[str, float] = field(default_factory=dict)
    token_estimate: int = 0
    source_chapter: Optional[int] = None

    @property
    def is_canon(self) -> bool:
        return self.authority == AuthorityTier.CANON


@dataclass
class ContextBlock:
    """The assembled context returned by :meth:`ContextEngine.build_context`.

    ``items`` are ordered by authority first (canon leads), then relevance.
    ``text`` is the rendered prompt-ready block; ``used_chars`` reflects the
    budget actually consumed.
    """

    items: list[ContextItem] = field(default_factory=list)
    text: str = ""
    used_chars: int = 0
    budget: Optional[ContextBudget] = None

    @property
    def paths(self) -> list[str]:
        return [item.chunk.path for item in self.items]


# --------------------------------------------------------------------------- #
# Unified vector store (D3 — one store, episodic becomes a collection)
# --------------------------------------------------------------------------- #


def _tokenize(text: str) -> list[str]:
    """Diacritic-folding word tokenizer (mirrors rag_context.build_fts_query)."""
    folded = "".join(
        ch
        for ch in unicodedata.normalize("NFKD", text.lower())
        if not unicodedata.combining(ch)
    )
    return [t for t in re.findall(r"\w+", folded, flags=re.UNICODE) if len(t) > 1]


def _chapter_from_path(path: str) -> Optional[int]:
    match = re.search(r"chapter_(\d+)", path)
    return int(match.group(1)) if match else None


def _embed(text: str, dims: int = 64) -> list[float]:
    """Deterministic dependency-free embedding: hashed bag-of-tokens.

    Stands in for the provider embeddings used by the real vector layer. It is
    stable and good enough for semantic-ish nearest-neighbour in tests; Hermes
    injects the real embedder in production.
    """
    vec = [0.0] * dims
    for token in _tokenize(text):
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        vec[h % dims] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm:
        vec = [v / norm for v in vec]
    return vec


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class UnifiedVectorStore:
    """A single semantic store replacing the two legacy Qdrant stores (D3).

    Phase A ``.vector_db`` (canon/worldbuilding/style) and Phase B
    ``.mem0/qdrant`` (episodic) used to be physically separate, which
    duplicated infra and let the two indexes drift. Here they are one store
    keyed by content-addressed ``chunk_id``; ``collection`` is just a label
    (e.g. ``"canon"`` vs ``"episodic"``) on the same physical index. Adding a
    chunk that already exists is a no-op, so merging the legacy stores drops
    duplicates automatically.
    """

    def __init__(self, dims: int = 64) -> None:
        self._dims = dims
        self._vectors: dict[str, list[float]] = {}
        self._chunks: dict[str, Chunk] = {}
        self._collection: dict[str, str] = {}

    def __len__(self) -> int:
        return len(self._chunks)

    @property
    def collections(self) -> set[str]:
        return set(self._collection.values())

    def add(self, chunk: Chunk, *, collection: str = "canon") -> bool:
        """Index ``chunk``. Returns False if it was already present (deduped)."""
        cid = chunk.chunk_id
        if cid in self._chunks:
            return False
        self._chunks[cid] = chunk
        self._vectors[cid] = _embed(chunk.content, self._dims)
        self._collection[cid] = collection
        return True

    def add_many(self, chunks: Iterable[Chunk], *, collection: str = "canon") -> int:
        return sum(1 for c in chunks if self.add(c, collection=collection))

    def search(self, query: str, top_n: int = DEFAULT_TOP_K) -> list[RetrievedChunk]:
        if not self._chunks:
            return []
        q = _embed(query, self._dims)
        scored = [
            RetrievedChunk(chunk=self._chunks[cid], score=_cosine(q, vec), channel="vector")
            for cid, vec in self._vectors.items()
        ]
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_n]

    @classmethod
    def merge_legacy_stores(
        cls,
        phase_a_chunks: Iterable[Chunk],
        phase_b_chunks: Iterable[Chunk],
        *,
        dims: int = 64,
    ) -> "UnifiedVectorStore":
        """Fold the two legacy stores into one, dropping duplicate chunks (D3).

        ``phase_a_chunks`` come from the old ``.vector_db`` (canon/worldbuilding)
        and ``phase_b_chunks`` from ``.mem0/qdrant`` (episodic). Chunks present
        in both collapse to a single entry via content-addressed ids.
        """
        store = cls(dims=dims)
        store.add_many(phase_a_chunks, collection="canon")
        store.add_many(phase_b_chunks, collection="episodic")
        return store


# --------------------------------------------------------------------------- #
# Retrieval channels
# --------------------------------------------------------------------------- #


@runtime_checkable
class Retriever(Protocol):
    """A retrieval channel (BM25, vector, graph, …)."""

    channel: str

    def retrieve(self, query: str, top_n: int) -> list[RetrievedChunk]: ...


class Bm25Retriever:
    """Lightweight lexical channel mirroring the FTS5/BM25 stage of
    ``rag_context.search_chunks_filtered`` (token overlap + idf weighting)."""

    channel = "bm25"

    def __init__(self, chunks: Iterable[Chunk]) -> None:
        self._chunks = list(chunks)
        self._doc_tokens = [set(_tokenize(c.content + " " + c.heading)) for c in self._chunks]
        n = len(self._chunks) or 1
        df: dict[str, int] = {}
        for toks in self._doc_tokens:
            for t in toks:
                df[t] = df.get(t, 0) + 1
        self._idf = {t: math.log(1 + n / (1 + c)) for t, c in df.items()}

    def retrieve(self, query: str, top_n: int) -> list[RetrievedChunk]:
        q_tokens = set(_tokenize(query))
        results: list[RetrievedChunk] = []
        for chunk, toks in zip(self._chunks, self._doc_tokens):
            overlap = q_tokens & toks
            if not overlap:
                continue
            score = sum(self._idf.get(t, 0.0) for t in overlap)
            results.append(RetrievedChunk(chunk=chunk, score=score, channel=self.channel))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_n]


class VectorRetriever:
    """Semantic channel backed by the :class:`UnifiedVectorStore`."""

    channel = "vector"

    def __init__(self, store: UnifiedVectorStore) -> None:
        self._store = store

    def retrieve(self, query: str, top_n: int) -> list[RetrievedChunk]:
        return self._store.search(query, top_n=top_n)


@runtime_checkable
class Reranker(Protocol):
    """Optional rerank stage between fusion and budgeting."""

    def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]: ...


class IdentityReranker:
    """Default no-op reranker: preserves fused order (reranker.py fallback)."""

    def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        return candidates[:top_k]


# --------------------------------------------------------------------------- #
# ContextEngine ABC + NovelKit implementation
# --------------------------------------------------------------------------- #


class ContextEngine(abc.ABC):
    """Hermes context-engine ABC (single-select plugin contract).

    Concrete engines assemble a :class:`ContextBlock` from the running
    conversation and a retrieval budget.
    """

    @abc.abstractmethod
    def build_context(
        self,
        messages: Sequence[object],
        budget: Optional[ContextBudget] = None,
    ) -> ContextBlock:
        """Assemble retrieval context for the current ``messages``."""
        raise NotImplementedError


def _query_from_messages(messages: Sequence[object]) -> str:
    """Derive a retrieval query from chat messages.

    Accepts dict-shaped messages (``{"role", "content"}``) or plain strings;
    concatenates the most recent user turns.
    """
    parts: list[str] = []
    for msg in messages:
        if isinstance(msg, str):
            parts.append(msg)
        elif isinstance(msg, dict):
            content = msg.get("content")
            if isinstance(content, str):
                parts.append(content)
    return "\n".join(parts[-4:])


class NovelKitContextEngine(ContextEngine):
    """Unified retrieval pipeline: ``retrieve → fuse(RRF) → rerank → budget``.

    Channels (BM25 + vector by default; graph optional) each return a ranked
    list. Lists are fused with RRF, optionally reranked, then ordered by
    **authority first** so canon always precedes derivative state (P5), and
    finally trimmed to the budget.
    """

    def __init__(
        self,
        retrievers: Sequence[Retriever],
        *,
        reranker: Optional[Reranker] = None,
        rrf_k: int = RRF_K,
        genre: Optional[GenreSpec] = None,
    ) -> None:
        if not retrievers:
            raise ValueError("NovelKitContextEngine needs at least one retriever")
        self._retrievers = list(retrievers)
        self._reranker = reranker or IdentityReranker()
        self._rrf_k = rrf_k
        self._genre = genre

    # -- public API -------------------------------------------------------- #

    def build_context(
        self,
        messages: Sequence[object],
        budget: Optional[ContextBudget] = None,
    ) -> ContextBlock:
        query = _query_from_messages(messages)
        return self.retrieve(query, budget=budget)

    def retrieve(
        self,
        query: str,
        budget: Optional[ContextBudget] = None,
    ) -> ContextBlock:
        budget = budget or compute_context_budget()
        if not query.strip():
            return ContextBlock(budget=budget)

        # --- Step 1: gather candidates per channel ------------------------ #
        candidate_limit = max(budget.top_k * 8, budget.top_k)
        ranked_lists: list[list[Chunk]] = []
        score_by_chunk: dict[str, float] = {}
        chunk_by_id: dict[str, Chunk] = {}

        for retriever in self._retrievers:
            hits = retriever.retrieve(query, candidate_limit)
            ranked_lists.append([h.chunk for h in hits])
            for h in hits:
                cid = h.chunk.chunk_id
                chunk_by_id.setdefault(cid, h.chunk)
                # Keep the strongest single-channel score for tie context.
                score_by_chunk[cid] = max(score_by_chunk.get(cid, 0.0), h.score)

        # --- Step 2: fuse with RRF ---------------------------------------- #
        fused = rrf_fuse(
            [[c.chunk_id for c in lst] for lst in ranked_lists],
            k=self._rrf_k,
        )
        fused_order = [
            RetrievedChunk(
                chunk=chunk_by_id[hit.candidate],
                score=hit.score,
                channel="rrf",
            )
            for hit in fused
            if hit.candidate in chunk_by_id
        ]

        # --- Step 3: rerank (semantic relevance; never reorders authority) - #
        reranked = self._reranker.rerank(query, fused_order, candidate_limit)

        # --- Step 4: authority-first ordering (P5) + budget --------------- #
        return self._assemble(reranked, budget)

    # -- internals --------------------------------------------------------- #

    def _assemble(
        self,
        ranked: list[RetrievedChunk],
        budget: ContextBudget,
    ) -> ContextBlock:
        """Order by ``(authority, -relevance)`` then trim to budget.

        Sorting by authority *first* is what guarantees P5: a canon chunk is
        always placed above any derivative chunk, regardless of relevance. The
        budget trim drops from the tail, so derivative chunks are shed before
        canon — the index can never push canon out of the context.
        """
        # Relevance preserved from the (stable) reranked order.
        relevance_rank = {rc.chunk.chunk_id: i for i, rc in enumerate(ranked)}

        items = [
            ContextItem(
                chunk=rc.chunk,
                relevance=rc.score,
                authority=rc.chunk.authority,
                content_hash=hashlib.sha256(
                    rc.chunk.content.encode("utf-8")
                ).hexdigest(),
                recall_reason=rc.channel,
                score_components={"relevance": rc.score},
                token_estimate=len(_tokenize(rc.chunk.content)),
                source_chapter=_chapter_from_path(rc.chunk.path),
            )
            for rc in ranked
        ]
        items.sort(
            key=lambda it: (int(it.authority), relevance_rank[it.chunk.chunk_id])
        )

        # Trim to top_k and max_chars, preserving authority order.
        #
        # Every emitted piece is counted against ``max_chars`` — no item is
        # exempt. Sources are split into bounded chunks before indexing (see
        # :func:`split_markdown`), so a single oversized document can no longer
        # consume the whole block. The one remaining edge case is a lone chunk
        # that still exceeds the budget (a heading-less wall of text): it is
        # truncated to fit rather than dropped, so the block is never empty
        # just because the top hit was large.
        block = ContextBlock(budget=budget)
        separator = "\n\n---\n\n"
        pieces: list[str] = []
        used = 0
        for item in items[: budget.top_k]:
            header = (
                f"<!-- source: {item.chunk.path} | heading: {item.chunk.heading} "
                f"| authority: {item.authority.name} -->"
            )
            body = item.chunk.content.strip()
            piece = f"{header}\n{body}"
            # Account for the joining separator in the guard as well as the
            # running total, otherwise the separators silently push the real
            # budget below max_chars (the guard undercounts what it will emit).
            overhead = len(separator) if block.items else 0
            if used + len(piece) + overhead > budget.max_chars:
                if block.items:
                    break
                # Nothing emitted yet: keep a truncated head so the caller still
                # gets the most relevant material instead of an empty block.
                keep = budget.max_chars - len(header) - 1
                if keep <= 0:
                    break
                piece = f"{header}\n{body[:keep]}"
            block.items.append(item)
            pieces.append(piece)
            used += len(piece) + overhead

        block.text = separator.join(pieces)
        block.used_chars = len(block.text)
        return block


# --------------------------------------------------------------------------- #
# Plugin factory / registration
# --------------------------------------------------------------------------- #


def build_engine(
    chunks: Iterable[Chunk],
    *,
    genre: Optional[GenreSpec] = None,
    reranker: Optional[Reranker] = None,
    dims: int = 64,
) -> NovelKitContextEngine:
    """Convenience builder wiring BM25 + a unified vector store over ``chunks``.

    This is the single retrieval entry point for the migrated system: one
    engine, one vector store, BM25 + vector channels fused by RRF.
    """
    chunk_list = list(chunks)
    store = UnifiedVectorStore(dims=dims)
    store.add_many(chunk_list, collection="canon")
    return NovelKitContextEngine(
        retrievers=[Bm25Retriever(chunk_list), VectorRetriever(store)],
        reranker=reranker,
        genre=genre,
    )


# Single-select context-engine registration. Importing the module registers the
# plugin under the stable name Hermes selects it by.
CONTEXT_ENGINE_NAME = "novelkit-context"

try:  # pragma: no cover - registry is an optional host dependency
    from tools.registry import register as _register

    _register(
        CONTEXT_ENGINE_NAME,
        build_engine,
        schema={"kind": "context-engine", "single_select": True},
        module=__name__,
    )
except Exception:  # noqa: BLE001 - never block import if the host registry differs
    pass


__all__ = [
    "AuthorityTier",
    "authority_rank_for_path",
    "is_canon_path",
    "FusedHit",
    "rrf_fuse",
    "ContextBudget",
    "compute_context_budget",
    "GenreSpec",
    "resolve_canon_tokens",
    "SHARED_CANON_TOKEN",
    "SHARED_CANON_SECONDARY_TOKEN",
    "SHARED_WORLDBUILDING_GUIDE_TOKEN",
    "GENRE_PLACEHOLDER",
    "Chunk",
    "split_markdown",
    "SPLIT_TARGET_CHARS",
    "SPLIT_OVERLAP_CHARS",
    "RetrievedChunk",
    "ContextItem",
    "ContextBlock",
    "UnifiedVectorStore",
    "Retriever",
    "Bm25Retriever",
    "VectorRetriever",
    "Reranker",
    "IdentityReranker",
    "ContextEngine",
    "NovelKitContextEngine",
    "build_engine",
    "CONTEXT_ENGINE_NAME",
]
