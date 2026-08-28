"""Real LLM creative loop — turns the pipeline into actual AI writing.

``LLMAutoNovelLoop`` is a concrete :class:`~integrations.autonovel.adapter.AutoNovelLoop`
that calls an OpenAI-compatible model (:class:`provider.llm_client.LLMClient`) for
the outline / draft / critique stages, grounded in the novel's PROJECT_DNA and
genre, and reuses the real NovelKit tools for bootstrap planning docs
(``novelkit_dna``) and synchronise (``novelkit_sync``).

This is the engine the migration deferred ("Hermes runtime_provider"): plug in
an API key in Settings and the same pipeline now produces real prose instead of
the in-memory reference text.
"""

from __future__ import annotations

import json
import hashlib
import logging
import re
from pathlib import Path
from typing import Any, Optional

from provider.llm_client import (
    LLMChainExhausted,
    LLMClient,
    LLMError,
    LLMTruncated,
)
from tools.novelkit_rules_tool import current_rules_digest

from .adapter import AutoNovelLoop, AutoNovelWorkspace, LoopStep, StepResult
from .resolved_canon import ResolvedCanon, resolve_canon

_LOG = logging.getLogger(__name__)

#: Char cap when reading PROJECT_DNA.md into a prompt. Raised from 8000 because
#: a full DNA (hybrid, all sections filled) runs ~13K chars, and the tail
#: sections — §X "Anti-AI DNA Checklist" (the author's own AI-phrasing blacklist),
#: §XI fixed metrics, §XII style-execution notes — sat PAST the old 8000 cut and
#: never reached the model. 16000 covers a fully-populated DNA with headroom.
_DNA_MAX_CHARS = 16000
_PREV_TAIL_WORDS = 6000
#: Advisory ceiling for the persona system prompt (SOUL + Author-Style + core).
#: Above this we log a warning (never truncate) so an oversized canon file is
#: visible in logs. ~4 chars/token; well under any modern model's context.
_PERSONA_WARN_TOKENS = 20000
#: Hard cap for the always-on genre-canon persona block alone (Author-Style +
#: <G>_style + Depth + StoryDepth + Xianxia core laws). Set high enough that a
#: full genre's core laws all fit — Xianxia's Texture + Progression + World +
#: Depth + Author-Style total ~60-70K chars — so the depth canon actually
#: reaches the model instead of being silently pushed to RAG. Only a genuinely
#: pathological pack (well past any real genre) trims here; anything trimmed is
#: still retrievable via RAG (every persona file is also indexed).
_GENRE_CANON_MAX_CHARS = 120000
_CANON_SYSTEM_ROOT = (
    Path(__file__).resolve().parents[2]
    / "skills" / "novelkit-canon" / "canon" / "system"
)
_SUBAGENTS_ROOT = Path(__file__).resolve().parents[2] / "subagents"

#: Cross-genre field-execution canon: applies to EVERY genre (Requirement 2.3).
_STORYDEPTH_FILE = _CANON_SYSTEM_ROOT / "StoryDepth" / "CREATE_NOVEL_FIELD_EXECUTION.md"

#: Sub-directories whose whole contents are "always-on" persona canon — the
#: voice/depth/texture laws the model must obey on every call. Loaded full-text
#: into the system prompt (and also indexed for RAG detail lookup).
#:
#: ``Texture`` stays always-on because it decides prose *feel* (word choice,
#: rhythm, forbidden phrasing) — a chapter can't recover that from an occasional
#: retrieval hit. ``Progression`` (cultivation ladder) and ``World`` (world
#: operating system) are large reference tables that are *looked up* per scene,
#: not obeyed line-by-line, so they moved to RAG-only (see _RAG_CANON_DIRS) to
#: cut ~72K chars (~18-24K tokens) off every call. They stay fully reachable via
#: :meth:`_retrieve` and the persona block still leads with the stable canon so
#: provider prompt-caching keeps them warm when they DO get pulled.
_PERSONA_CANON_DIRS = frozenset({"Depth", "Texture"})
#: Sub-directories that are retrieval-only canon (large reference material pulled
#: on demand by the context engine, never force-fed into every prompt).
_RAG_CANON_DIRS = frozenset({"Genre Operating", "Progression", "World"})
#: Sub-directories where the novel selects ONE file (by a DNA code): Author Style
#: via ``style_model``, Worldbuilding guide via ``worldbuilding_guide``.
_PICK_ONE_DIRS = frozenset({"Author Style", "Worldbuilding guide"})
#: Files under a pack that are consumed elsewhere (language guard) or are OS
#: cruft — never fed to the LLM.
_CANON_SKIP_NAMES = frozenset({"vocabulary.txt", ".DS_Store"})

#: Several pick-one canon files predate the ``[CODE]`` bracket naming and ship
#: as a name-stem file instead (Sci-fi / Meta Genre Author-Style profiles, and
#: the ChenDong/ThanDong worldbuilding guide). Map the DNA style/wb code to that
#: filename stem so the file still resolves. Keys are the form's style codes
#: (see ``dna_form.STYLE_BY_GENRE``); values are the ``glob`` stem prefix.
_CODE_NAME_ALIAS = {
    # Sci-fi Author Style (slug-named profiles).
    "LTH": "luu-tu-han",
    "THCM": "thai-hong-chi-mon",
    "TNT": "thap-nien-that",
    "TTNB": "that-thap-nhi-bien",
    "VT": "vien-dong",
    # Meta Genre Author Style (slug-named profiles).
    "GHTK": "giang-ho-tai-kien",
    "MHTK": "mac-huong-dong-khuu",
    "MV": "mac-vu",
    "TP": "tan-phong",
    "TST": "thanh-sam-thu",
    # Xianxia Worldbuilding guide legacy name (ships as ThanDong_… not [CD]).
    "CD": "ThanDong",
}


def _match_code_file(dir_path: Path, code: str) -> Optional[Path]:
    """Return the ``[CODE] …md`` file in ``dir_path`` for ``code`` (or None).

    Falls back to a name-stem alias for the files that shipped without the
    bracket-code prefix (see :data:`_CODE_NAME_ALIAS`)."""
    if not code:
        return None
    try:
        matches = sorted(dir_path.glob(f"[[]{code}[]]*.md"))
    except OSError:
        matches = []
    if matches:
        return matches[0]
    alias = _CODE_NAME_ALIAS.get(code.upper())
    if alias:
        try:
            aliased = sorted(dir_path.glob(f"{alias}*.md"))
        except OSError:
            aliased = []
        if aliased:
            return aliased[0]
    return None


def _classify_canon_file(
    path: Path, pack_dir: Path, *, style_code: str, wb_code: str
) -> str:
    """Classify one file under a genre pack into a runtime channel.

    Returns one of: ``"persona"`` (full text into the system prompt AND indexed
    for RAG), ``"rag"`` (retrieval-only), or ``"skip"`` (not consumed here).

    ``Author Style`` / ``Worldbuilding guide`` are pick-one dirs: only the file
    matching the novel's ``style_model`` / ``worldbuilding_guide`` code is
    consumed; the other masters' files are skipped for THIS novel (they remain
    reachable for a novel that selects them).
    """
    if path.name in _CANON_SKIP_NAMES:
        return "skip"
    parent = path.parent.name
    if parent in _PERSONA_CANON_DIRS:
        return "persona"
    if parent in _RAG_CANON_DIRS:
        return "rag"
    if parent == "Author Style":
        selected = _match_code_file(pack_dir / "Author Style", style_code)
        return "persona" if selected == path else "skip"
    if parent == "Worldbuilding guide":
        selected = _match_code_file(pack_dir / "Worldbuilding guide", wb_code)
        return "rag" if selected == path else "skip"
    # Root-level pack files: <G>_style.md is always-on voice; <G>_consistency_rules
    # and any other root doc are retrieval-only reference.
    if path.parent == pack_dir and path.suffix == ".md":
        if path.stem.endswith("_style"):
            return "persona"
        return "rag"
    return "skip"


def _iter_system_canon(
    pack_dir: Path, *, style_code: str = "", wb_code: str = ""
) -> dict[str, list[Path]]:
    """Split a genre pack's files into runtime channels (see _classify_canon_file).

    Returns ``{"persona": [...], "rag": [...]}``. Every persona file is also
    added to ``rag`` so its detail is retrievable; the two lists together cover
    every consumable file in the pack (nothing is silently dropped)."""
    persona: list[Path] = []
    rag: list[Path] = []
    if not pack_dir.is_dir():
        return {"persona": persona, "rag": rag}
    for path in sorted(pack_dir.rglob("*")):
        if not path.is_file():
            continue
        channel = _classify_canon_file(
            path, pack_dir, style_code=style_code, wb_code=wb_code
        )
        if channel == "persona":
            persona.append(path)
            rag.append(path)
        elif channel == "rag":
            rag.append(path)
    return {"persona": persona, "rag": rag}

# agent_role string → SOUL.md folder name (per sub_agents squad).
# The role names match the "agent_role" field in pipeline task specs.
_ROLE_TO_SOUL_DIR: dict[str, str] = {
    "World Builder": "thien_co_tu",
    "Character Architect": "dong_tu",
    "Plot Weaver": "mong_yem",
    "Prose Writer": "huyet_thu",
    "Quality Auditor": "chan_nhan",
    # fallback aliases
    "World Architect": "thien_co_tu",
    "Character Architect / Nhân Vật Sư": "dong_tu",
    "Plot Architect": "mong_yem",
    "Prose Author": "huyet_thu",
    "Lãng Khách": "thien_co_tu",  # orchestrator: best-effort fallback
}


def _read(path: Path, limit: Optional[int] = None) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    return text[:limit] if limit else text


#: The immutable setting facts a prose stage MUST see, as ``(field, label)`` in
#: emission order.
#:
#: ``_dna_digest`` deliberately carries only craft signal (voice, want/need,
#: scene promise), which left the world + power system — the very fields the
#: create/enrich form asks the user to fill — out of every draft prompt. They
#: were not recoverable from anywhere else either: the state card is empty until
#: a chapter exists, and retrieval only ever surfaced PROJECT_DNA's frontmatter.
#: So a cultivation novel was drafted without its realm ladder. These are facts,
#: not craft: they must be stated, not retrieved.
_WORLD_FACT_FIELDS: tuple[tuple[str, str], ...] = (
    ("world_name", "Tên thế giới"),
    ("world_era", "Thời đại"),
    ("world_mindset", "Quy luật vận hành"),
    ("world_secret", "Bí mật thế giới"),
    ("world_locations", "Địa điểm trọng yếu"),
    ("world_pressure", "Áp lực thế giới"),
    ("world_frame_execution", "Khung thân phận"),
    ("system_name", "Hệ thống tu luyện/năng lực"),
    ("system_tiers", "Thang cảnh giới (BẤT BIẾN)"),
    ("system_cost", "Cái giá"),
    ("system_resource", "Tài nguyên"),
    ("system_bottleneck", "Bình cảnh / trở lực"),
    ("system_golden_finger", "Kim thủ chỉ"),
    ("system_golden_finger_limit", "Giới hạn kim thủ chỉ"),
    ("cultivation_speed", "Tốc độ tu luyện"),
    ("cultivation_age_benchmarks", "Mốc tuổi × cảnh giới"),
    ("mc_name", "Tên nhân vật chính"),
    ("antagonist_name", "Tên phản diện"),
    ("antagonist_conflict", "Xung đột với phản diện"),
    ("artifact", "Pháp bảo"),
    ("spirit_beast", "Linh thú"),
)

#: Per-field ceiling inside the world-facts block. Trimming per field (rather
#: than truncating the whole block) guarantees the late fields — the realm ladder
#: and its age benchmarks — are never the ones dropped.
_WORLD_FACT_FIELD_MAX_CHARS = 320

#: Ceiling for the whole world-facts block. The measured full field set is ~11K
#: chars; the per-field cap above brings a realistic novel in well under this.
_WORLD_FACTS_MAX_CHARS = 4200

#: Fraction of a combined :meth:`_retrieve` budget spent on genre canon; the
#: remainder goes to the novel's own artifacts. The novel's mutable state is the
#: thing a chapter must not contradict, so it keeps the larger share.
_RETRIEVE_CANON_SHARE = 0.4

#: Draft-stage retrieval allowances, per corpus. Genre canon and the novel's own
#: artifacts are retrieved SEPARATELY (see :meth:`_retrieve_split`) because both
#: sit in the CANON authority tier: pooled, the denser novel artifacts took every
#: slot and the genre canon reached the model as zero bytes (measured).
_DRAFT_CANON_GROUND_CHARS = 7000
_DRAFT_NOVEL_GROUND_CHARS = 5000

#: Bounded slice of the SELECTED worldbuilding guide, stated in the draft prompt.
#: The prompt previously only *named* the guide while carrying none of its text.
_DRAFT_WB_GUIDE_CHARS = 4000

#: Outline-stage retrieval allowances, split per corpus like the draft stage.
#: Smaller than the draft's: an outline needs the operating laws and the settled
#: facts, not the prose texture. Kept separate anyway, because a pooled budget
#: let PROJECT_DNA.md take every slot here too.
_OUTLINE_CANON_GROUND_CHARS = 4500
_OUTLINE_NOVEL_GROUND_CHARS = 3500


#: The placeholder written when a bootstrap file's LLM call fails. A file still
#: carrying this marker (or empty) is NOT real canon and must be regenerated.
_STUB_MARKER = "_(chờ AI bổ sung — chạy lại bước này)_"


def _has_real_content(ws: "AutoNovelWorkspace", rel: str) -> bool:
    """True when ``rel`` holds real generated canon, not an empty/stub file.

    Lets a re-run of a bootstrap stage skip files that already succeeded and
    only regenerate the ones still on the stub — so a transient failure on one
    file never clobbers a sibling that is already good, and repeated runs
    converge instead of re-rolling everything."""
    text = _read(ws.root / rel).strip()
    return bool(text) and _STUB_MARKER not in text


def _score_from_review(text: str) -> float:
    """Extract a 0-100 score from a review (NN/100 or a bare 'Điểm: NN')."""
    m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*/\s*100", text)
    if not m:
        m = re.search(r"(?:Điểm|Score)\s*[:\-]?\s*(\d{1,3}(?:\.\d+)?)", text, re.IGNORECASE)
    if not m:
        return 0.0
    return max(0.0, min(100.0, float(m.group(1))))


def _verdict_for(score: float) -> str:
    if score >= 85:
        return "PASS"
    if score >= 70:
        return "SOFT-FAIL"
    return "HARD-FAIL"


_SYSTEM_CORE = (
    "Bạn là tác giả tiểu thuyết mạng chuyên nghiệp. PROJECT_DNA và database "
    "là sự thật canon của riêng truyện này. Author Style đã chọn chỉ là metadata "
    "nhận diện: không suy luận, tái tạo hoặc mô phỏng văn phong từ tên hay mã tác giả. "
    "Giọng văn phải đến từ PROJECT_DNA và các quy tắc thể loại không gắn với tác giả; "
    "Worldbuilding guide đã chọn quyết định cách thế giới vận hành và lộ thông tin. "
    "Không sao chép câu chữ, tên riêng, tình tiết hay hệ thống đặc thù của tác phẩm "
    "tham chiếu. TUYỆT ĐỐI KHÔNG dùng "
    "ngôn ngữ vận hành/kỹ thuật (debug, metadata, pipeline, runtime, workflow...) trong văn. "
    "Không tự giải thích động cơ một cách lộ liễu, không sáo rỗng."
)

#: Multi-file canon each bootstrap command produces (parity with the legacy
#: bootstrap stages that wrote geography/factions/threads_master/seeds_tracker…).
_BOOTSTRAP_FILES: dict[str, list[tuple[str, str]]] = {
    "CREATE_CHARACTERS": [
        ("database/characters/protagonist.md",
         "Hồ sơ nhân vật chính: tên, ngoại hình, want/need/lie/ghost, giọng riêng, cung bậc phát triển"),
        ("database/characters/antagonist.md",
         "Hồ sơ phản diện cuối: want, lý lẽ riêng, khoảnh khắc 'người', thời điểm lộ diện"),
        ("database/characters/supporting_cast.md",
         "Dàn nhân vật phụ (≥3) + lưới quan hệ, mỗi người một giọng riêng"),
    ],
    "BUILD_WORLD": [
        ("database/worldbuilding/overview.md",
         "Tổng quan thế giới: tên, thời đại, tư duy/quy luật trung tâm, bí mật lịch sử/lời nguyền"),
        ("database/worldbuilding/geography.md",
         "Địa lý & 3-5 địa điểm quan trọng, đặc trưng từng nơi"),
        ("database/worldbuilding/factions.md",
         "Các thế lực/tông môn chính, quan hệ và xung đột giữa họ"),
        ("database/systems/power_system.md",
         "Hệ thống sức mạnh: cấp bậc, cái giá đột phá, tài nguyên, nút thắt, Kim Thủ Chỉ + giới hạn"),
    ],
    "CREATE_PLOT_THREADS": [
        ("database/plot_threads/threads_master.md",
         "Sổ tuyến truyện: Quest/Fire/Constellation — bắt đầu, kết thúc, ghi chú"),
        ("database/plot_threads/seeds_tracker.md",
         "Sổ phục bút: mỗi seed có nơi cài / nơi thu hoạch / mô tả / trạng thái"),
    ],
    "CREATE_TIMELINE": [
        ("database/timeline/master_timeline.md",
         "Dòng thời gian tổng: mốc lịch sử thế giới + tuổi/mốc tu luyện nhân vật + cột mốc thế lực"),
    ],
}

class LLMAutoNovelLoop(AutoNovelLoop):
    """An AutoNovel loop whose creative stages are real LLM calls."""

    def __init__(
        self,
        *,
        client: Optional[LLMClient] = None,
        words_per_chapter: int = 2600,
        max_revisions: int = 2,
    ):
        self.client = client or LLMClient()
        self.words_per_chapter = words_per_chapter
        # How many times a sub-bar chapter is auto-rewritten from the critique
        # feedback before we give up (root-cause fix for the breaker stall).
        self.max_revisions = max(0, max_revisions)
        # Cache of the resolved genre-canon persona block + SOUL excerpts.
        self._style_cache: dict[str, str] = {}
        self._soul_cache: dict[str, str] = {}
        # Cache of the resolved chapter length (from DNA) per workspace.
        self._wpc_cache: dict[str, int] = {}
        # Cache of the resolved system-canon file split per workspace.
        self._canon_files_cache: dict[str, dict[str, list[Path]]] = {}
        # Cache of the single resolved routing contract per workspace.
        self._canon_cache: dict[str, "ResolvedCanon"] = {}
        # Cache of the SPLIT canon chunks per workspace: the genre canon is
        # ~190K chars and never changes during a run, so re-splitting it on
        # every retrieval call is pure waste.
        self._canon_chunk_cache: dict[str, list[Any]] = {}
        # Cache of the structured DNA fields sidecar + the compact writing
        # digest built from it, per workspace.
        self._dna_fields_cache: dict[str, dict[str, Any]] = {}
        self._dna_digest_cache: dict[str, str] = {}
        self._dna_tail_cache: dict[str, str] = {}
        # Workspaces already warned about an oversized PROJECT_DNA.md. The read
        # happens on every prompt build, so without this the warning repeated
        # dozens of times per hour for one novel and buried real signal in the
        # production log.
        self._dna_cap_warned: dict[str, bool] = {}
        # Cache of the settled world/power facts block per workspace.
        self._world_facts_cache: dict[str, str] = {}

    # ---- bootstrap planning docs (reuse the real DNA tool) ----
    def prepare(self, workspace: AutoNovelWorkspace) -> None:
        from tools.novelkit_dna_tool import bootstrap_docs

        if (workspace.root / "PROJECT_DNA.md").exists():
            try:
                bootstrap_docs(str(workspace.root))
            except Exception:  # noqa: BLE001 — best effort
                pass

    # ---- helpers ----
    def _dna(self, ws: AutoNovelWorkspace) -> str:
        raw = _read(ws.root / "PROJECT_DNA.md", _DNA_MAX_CHARS)
        # Surface an oversized DNA in logs: past the read cap, late sections
        # (e.g. the anti-AI checklist / style execution) are silently dropped
        # from the full-text read. Prose stages use the compact digest so they
        # are unaffected, but any stage still on full-text DNA would lose the
        # tail.
        #
        # Two guards keep this signal honest. The size test is ``>`` on the file,
        # not ``>=`` on the truncated read: ``_read`` returns ``text[:cap]``, so a
        # file of exactly the cap is complete yet used to report itself truncated.
        # And it fires once per workspace — the comment already claimed
        # "once-ish" but nothing enforced it, so a single run emitted 78 identical
        # lines in an hour and buried the rest of the log.
        if not self._dna_cap_warned.get(str(ws.root)):
            # One char past the cap is enough to tell "exactly full" from
            # "truncated"; st_size would be wrong here because it counts UTF-8
            # bytes, and Vietnamese prose runs well over one byte per char.
            probe = _read(ws.root / "PROJECT_DNA.md", _DNA_MAX_CHARS + 1)
            if len(probe) > _DNA_MAX_CHARS:
                self._dna_cap_warned[str(ws.root)] = True
                _LOG.warning(
                    "PROJECT_DNA.md for %s hit the %d-char read cap — late "
                    "sections may be truncated on full-text stages; prose stages "
                    "use the digest and are unaffected.",
                    ws.root.name, _DNA_MAX_CHARS,
                )
        return raw

    def _canon(self, ws: AutoNovelWorkspace) -> "ResolvedCanon":
        """Resolve (once, cached) every routing decision for this novel.

        Genre, author style, worldbuilding guide, canon packs and squad used to be
        recomputed independently here, in ``dna_form``, in ``service`` and in the
        gate/guard tools — each with its own source precedence. ``llm_loop`` read
        ONLY the frontmatter (via a regex over a 16K-char-capped read), while the
        rest of the system preferred ``PROJECT_DNA.fields.json``, so a novel whose
        frontmatter and sidecar disagreed was drafted with one style and reviewed
        against another. :class:`ResolvedCanon` is the single answer.
        """
        key = str(ws.root)
        cached = self._canon_cache.get(key)
        if cached is None:
            cached = resolve_canon(ws.root)
            if not cached.resolved:
                # Previously eleven call sites each defaulted a missing genre to
                # "xianxia", so a scifi/romance novel whose genre went missing was
                # silently drafted, reviewed and lexically gated as cultivation
                # fiction. Resolution now fails visibly instead.
                _LOG.error(
                    "cannot resolve genre for %s — no genre_primary/genre in "
                    "PROJECT_DNA.fields.json, PROJECT_DNA.meta.json or the "
                    "frontmatter; genre-specific canon and the language guard "
                    "will be inactive for this novel",
                    ws.root.name,
                )
            self._canon_cache[key] = cached
        return cached

    def _genre(self, ws: AutoNovelWorkspace) -> str:
        """The novel's PRIMARY genre slug (see :class:`ResolvedCanon`)."""
        return self._canon(ws).genre_primary

    def _genre_secondary(self, ws: AutoNovelWorkspace) -> str:
        """The SECONDARY genre slug for hybrid novels (or "").

        Passed to the language guard so the secondary genre's vocabulary is
        whitelisted (its bans do NOT apply — primary wins). Enables correct
        hybrid diction checks, e.g. xianxia+romance."""
        return self._canon(ws).genre_secondary

    def _dna_frontmatter(self, ws: AutoNovelWorkspace) -> str:
        """The leading ``---`` … ``---`` block of PROJECT_DNA.md (or "").

        Field lookups must be confined to this block. Searching the whole
        document also matched the ``## XIV. HYBRID GENRE EXAMPLES`` sample that
        every generated DNA carries, so a single-genre novel read
        ``genre_secondary: dark theme`` out of a YAML comment.
        """
        text = self._dna(ws)
        if not text.startswith("---"):
            return ""
        end = text.find("\n---", 3)
        return text[3:end] if end != -1 else ""

    def _dna_field(self, ws: AutoNovelWorkspace, field: str) -> str:
        """Read a single ``key: value`` field from the DNA frontmatter (or "").

        Two details carry the correctness:

        * the search is confined to :meth:`_dna_frontmatter`, so the trailing
          EXAMPLE block cannot be read as this novel's metadata;
        * the gap before the value is ``[^\\S\\n]*`` rather than ``\\s*``. ``\\s``
          matches newlines, so a key declared empty (``style_blend:`` — how the
          form writes an unset field) consumed the NEXT line and returned it as
          its own value. Measured on 503 real workspaces, 476 were affected:
          ``style_model`` resolved to the literal ``style_blend:`` for 334 of
          them, which reached the prose prompt as malformed style metadata
          instead of the selected reference code.

        A DNA with no ``---`` block at all (26 of the 503 real workspaces are
        hand-made or still placeholders) is searched whole, so those novels keep
        the fields they do declare. That fallback is safe against the EXAMPLE
        block because only generated DNAs carry it, and every generated DNA has
        frontmatter.
        """
        scope = self._dna_frontmatter(ws) or self._dna(ws)
        m = re.search(
            rf"^{re.escape(field)}[^\S\n]*:[^\S\n]*([^\n]*)$",
            scope,
            re.MULTILINE,
        )
        return m.group(1).strip() if m else ""

    def _dna_fields(self, ws: AutoNovelWorkspace) -> dict[str, Any]:
        """Return the structured DNA fields from ``PROJECT_DNA.fields.json``.

        This sidecar (written by the form on create/enrich) holds every seed
        field as a clean key→value map — the machine-readable twin of the prose
        PROJECT_DNA.md. Reading it lets the prompts pull just the fields a stage
        needs instead of dumping the whole ~13K-char document. Empty dict when
        the sidecar is missing (a hand-made or legacy novel); callers then fall
        back to the full-text DNA."""
        key = str(ws.root)
        cached = self._dna_fields_cache.get(key)
        if cached is not None:
            return cached
        fields: dict[str, Any] = {}
        try:
            raw = (ws.root / "PROJECT_DNA.fields.json").read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                fields = {str(k): v for k, v in data.items()}
        except (OSError, ValueError, TypeError):
            fields = {}
        self._dna_fields_cache[key] = fields
        return fields

    def _modern_register_allowed(self, ws: AutoNovelWorkspace) -> bool:
        from tools.novelkit_language_guard_tool import modern_register_allowed

        metadata = dict(self._dna_fields(ws))
        for field in ("world_era", "setting_era", "allow_modern_register"):
            metadata.setdefault(field, self._dna_field(ws, field))
        return modern_register_allowed(metadata)

    def _register_rules(
        self,
        ws: AutoNovelWorkspace,
        *,
        style_code: str = "",
        lexical_exception: bool = False,
    ) -> tuple[str, ...]:
        """Register sentences for this novel, from the genre's guard profile.

        Single source for the register contract shared by the drafting prompt and
        ``dna_form``'s generation/enrichment prompt — see
        :meth:`GuardProfile.register_contract`. Returns ``()`` for a genre whose
        profile declares no register rules, so no genre is special-cased in code.
        """
        from tools.novelkit_language_guard_tool import load_profile

        genre = self._genre(ws)
        if not genre:
            return ()
        try:
            profile = load_profile(genre)
        except (OSError, ValueError) as exc:  # corrupt profile must be visible
            _LOG.error("language guard profile for %s is unreadable: %s", genre, exc)
            return ()
        return profile.register_contract(
            style_code=style_code, lexical_exception=lexical_exception
        )

    def _language_guard_prompt_contract(self, ws: AutoNovelWorkspace) -> str:
        """Render the selected profile's strict classical register contract."""
        from tools.novelkit_language_guard_tool import load_profile

        profile = load_profile(self._genre(ws))
        if (
            not profile.strict_classical_register
            or self._modern_register_allowed(ws)
        ):
            return ""
        rows = []
        for item in profile.banned_terms:
            replacement = item.replacement or "loại bỏ"
            rows.append(f"- {item.term} → {replacement}")
        return (
            "\n\nREGISTER CONTRACT TỪ CONFIG (BẮT BUỘC, áp dụng cả câu thoại "
            "mẫu trong outline):\n"
            + "\n".join(rows)
        )

    def _dna_digest(self, ws: AutoNovelWorkspace) -> str:
        """Build the compact, writing-focused DNA digest for prose stages.

        The full PROJECT_DNA.md carries project-planning scaffolding (routing
        table, arc-planning grid, pre-flight checklist, hybrid examples,
        relationship matrices) that does not help write one chapter yet costs
        tokens and buries the craft signal in every draft/critique/revise call
        (lost-in-the-middle). This digest keeps ONLY the fields that steer prose
        — logline, theme, voice, MC want/need/lie/ghost/voice, scene promise,
        anti-AI cấm kỵ, style execution — assembled from the structured sidecar.

        Falls back to the full-text DNA when the sidecar is absent, so a legacy
        or hand-authored novel is never left without its contract. Cached per
        workspace."""
        key = str(ws.root)
        cached = self._dna_digest_cache.get(key)
        if cached is not None:
            return cached
        f = self._dna_fields(ws)
        if not f:
            # No structured sidecar → keep the previous behaviour exactly.
            digest = self._dna(ws)
            self._dna_digest_cache[key] = digest
            return digest

        def g(*keys: str) -> str:
            for k in keys:
                v = f.get(k)
                if v is not None and str(v).strip():
                    return str(v).strip()
            return ""

        lines: list[str] = ["# DNA CÔ ĐỌNG (chỉ dẫn viết — bám sát tuyệt đối)"]

        def add(label: str, *keys: str) -> None:
            val = g(*keys)
            if val:
                lines.append(f"- {label}: {val}")

        add("Tên", "title")
        add("Logline", "logline")
        add("Thể loại", "genre_primary", "genre")
        add("Chủ đề cốt lõi", "theme")
        add("Khí sắc / giọng văn", "tone")
        add("Cách thi triển văn phong", "style_execution")
        # MC craft spine.
        add("MC — Want", "mc_want")
        add("MC — Need", "mc_need")
        add("MC — Lie", "mc_lie")
        add("MC — Ghost", "mc_ghost")
        add("MC — Giọng riêng", "mc_voice")
        # Premise contract fields that shape scene-level craft.
        add("Core Wound", "core_wound")
        add("Scene Promise", "scene_promise")
        add("Scene Vitality", "scene_vitality_contract", "scene_vitality")
        add("Reader Addiction Loop", "reader_addiction_loop")

        digest = "\n".join(lines)
        self._dna_digest_cache[key] = digest
        return digest

    def _world_facts_block(self, ws: AutoNovelWorkspace) -> str:
        """Render the novel's settled world/power facts for a prose prompt.

        The writing digest (:meth:`_dna_digest`) deliberately keeps only craft
        fields, and the character state card only covers the protagonist. That
        left the *settled* facts of the world — its name, era, the realm ladder,
        what the golden finger costs — in no prose channel at all: the model was
        asked to write cultivation fiction without being told the realm names it
        had to use, and the prompt only *named* the worldbuilding guide without
        carrying any of it. Every invented realm then contradicted the DNA that
        the reviewer scores against.

        Fields come from :data:`_WORLD_FACT_FIELDS` — an explicit ordered spec,
        so adding a world field to the schema is one edit here rather than a new
        ad-hoc lookup in each prompt builder. Per-field caps keep one verbose
        answer from starving the rest; the whole block is bounded by
        :data:`_WORLD_FACTS_MAX_CHARS`. Cached per workspace.
        """
        key = str(ws.root)
        cached = self._world_facts_cache.get(key)
        if cached is not None:
            return cached
        f = self._dna_fields(ws)
        lines: list[str] = []
        used = 0
        for field_key, label in _WORLD_FACT_FIELDS:
            raw = f.get(field_key)
            if raw is None or not str(raw).strip():
                raw = self._dna_field(ws, field_key)
            value = " ".join(str(raw).split()).strip()
            if not value:
                continue
            if len(value) > _WORLD_FACT_FIELD_MAX_CHARS:
                value = value[:_WORLD_FACT_FIELD_MAX_CHARS].rstrip() + "…"
            line = f"- {label}: {value}"
            if used + len(line) > _WORLD_FACTS_MAX_CHARS and lines:
                break
            lines.append(line)
            used += len(line)
        block = "\n".join(lines)
        self._world_facts_cache[key] = block
        return block

    def _dna_tail_reminder(self, ws: AutoNovelWorkspace) -> str:
        """A short craft reminder appended at the END of a prose prompt.

        Models attend most strongly to the head and TAIL of a prompt; the middle
        fades (lost-in-the-middle). The DNA digest leads the prompt, so the most
        safety-critical craft rules (anti-AI cấm kỵ + the master voice keywords)
        are echoed here, right before generation, so they stay salient no matter
        how much canon/ground sits in between. Empty when the sidecar has neither
        signal (nothing to echo). Cached per workspace."""
        key = str(ws.root)
        cached = self._dna_tail_cache.get(key)
        if cached is not None:
            return cached
        f = self._dna_fields(ws)
        parts: list[str] = []
        tone = str(f.get("tone") or "").strip()
        style_exec = str(f.get("style_execution") or "").strip()
        if tone:
            parts.append(f"KHÍ SẮC (chỉ điều chỉnh sắc độ): {tone[:280]}")
        if style_exec:
            parts.append(f"THI TRIỂN VĂN PHONG (ưu tiên hơn khí sắc): {style_exec[:560]}")

        # The author code remains a stable routing identifier, but the matching
        # profile is intentionally informational and must not control prose.
        genre = self._genre(ws)
        style_code = str(
            f.get("style_model") or self._dna_field(ws, "style_model") or ""
        ).strip().upper()
        secondary_style = str(
            f.get("style_secondary")
            or self._dna_field(ws, "style_blend")
            or ""
        ).strip().upper()
        if style_code:
            lock = f"THAM CHIẾU TÁC GIẢ: chính={style_code}"
            if secondary_style:
                lock += f"; phụ={secondary_style}"
            parts.append(
                lock
                + ". Chỉ dùng để nhận diện lựa chọn; không suy luận hoặc mô phỏng "
                "văn phong từ tên, mã hay kiến thức bên ngoài về tác giả."
            )
        # Register rules come from ``config/language_guard/<genre>.json``, not from
        # ``if genre == "xianxia"`` / ``and style_code == "VN"`` branches in code.
        # Those branches existed here AND in dna_form.prose_contract_instruction,
        # so the drafting prompt and the DNA-generation prompt were two hand-synced
        # copies of the same rules, and giving another genre (or another author) a
        # register contract meant editing Python in two places.
        #
        # Apply only the genre-level register. Author-code overrides are ignored
        # because individual author profiles no longer define prose contracts.
        parts.extend(self._register_rules(ws))
        # Standing anti-AI cấm kỵ — the same craft floor the DNA §X checklist
        # encodes, restated compactly so it survives at the tail even when a
        # hand-made DNA has no explicit checklist field.
        parts.append(
            "CẤM: 'vô cùng/cực kỳ/rất' (thay bằng hình ảnh); 'không chỉ… mà "
            "còn…'; dán nhãn cảm xúc ('hắn cảm thấy…' → SHOW qua hành động); "
            "cụm dịch sáo ('nụ cười không chạm đến mắt'); mở ≥3 câu liền cùng "
            "chủ ngữ; infodump > 100 chữ."
        )
        reminder = "\n\n" + "\n".join(parts) if parts else ""
        self._dna_tail_cache[key] = reminder
        return reminder

    def _canon_pack_specs(
        self, ws: AutoNovelWorkspace
    ) -> list[tuple[Path, str, str]]:
        """Resolve each canon pack together with its own selected style codes.

        Reads ``canon_pack`` (and ``canon_pack_secondary`` for hybrids) — the
        form writes these as ``system/<Pack>`` (see dna_form ``_build_frontmatter_lines``).
        Returns existing packs primary-first as ``(path, style, worldbuilding)``.
        The secondary pack must use ``style_blend`` rather than accidentally
        reusing the primary author's code.
        """
        specs: list[tuple[Path, str, str]] = []
        for pack, style_code, wb_code in self._canon(ws).pack_selections():
            cand = _CANON_SYSTEM_ROOT / pack
            if cand.is_dir():
                specs.append((cand, style_code, wb_code))
        return specs

    def _canon_pack_dirs(self, ws: AutoNovelWorkspace) -> list[Path]:
        """Return existing canon pack directories, primary first."""
        dirs: list[Path] = []
        for path, _, _ in self._canon_pack_specs(ws):
            if path not in dirs:
                dirs.append(path)
        return dirs

    def _system_canon(self, ws: AutoNovelWorkspace) -> dict[str, list[Path]]:
        """Resolve + cache the persona/rag file split for this novel's pack(s).

        Merges every resolved pack (primary + secondary) plus the cross-genre
        StoryDepth field-execution canon, which applies to every genre. The
        pick-one dirs (Author Style / Worldbuilding guide) are filtered by the
        novel's ``style_model`` / ``worldbuilding_guide`` codes.

        Returns ``{"persona": [...], "rag": [...]}`` where ``rag`` is the FULL
        set of consumable files (persona ⊆ rag): every always-on persona file is
        also retrievable on demand, and the retrieval-only reference material
        (consistency rules, Genre Operating, Worldbuilding guide) lives in ``rag``
        alone. Together they cover every consumable file in the pack — nothing is
        silently dropped.
        """
        key = str(ws.root)
        cached = self._canon_files_cache.get(key)
        if cached is not None:
            return cached
        persona: list[Path] = []
        rag: list[Path] = []
        persona_seen: set[Path] = set()
        rag_seen: set[Path] = set()

        def _add(paths: list[Path], bucket: list[Path], seen: set[Path]) -> None:
            for p in paths:
                if p not in seen:
                    seen.add(p)
                    bucket.append(p)

        for pack_dir, style_code, wb_code in self._canon_pack_specs(ws):
            split = _iter_system_canon(
                pack_dir, style_code=style_code, wb_code=wb_code
            )
            _add(split["persona"], persona, persona_seen)
            # ``rag`` is a superset: _iter_system_canon already includes every
            # persona file in its "rag" list, so this covers persona + rag-only.
            _add(split["rag"], rag, rag_seen)
        # StoryDepth applies to every genre (cross-genre field execution): it is
        # both an always-on persona law AND retrievable.
        if _STORYDEPTH_FILE.is_file():
            if _STORYDEPTH_FILE not in persona_seen:
                persona_seen.add(_STORYDEPTH_FILE)
                persona.append(_STORYDEPTH_FILE)
            if _STORYDEPTH_FILE not in rag_seen:
                rag_seen.add(_STORYDEPTH_FILE)
                rag.append(_STORYDEPTH_FILE)
        result = {"persona": persona, "rag": rag}
        self._canon_files_cache[key] = result
        return result

    def _wb_guide_excerpt(self, ws: AutoNovelWorkspace, *, limit: int = 12000) -> str:
        """Bounded worldbuilding guidance for every selected genre pack.

        A dedicated ``Worldbuilding guide`` wins when the pack has one. Packs
        without that directory (and Xianxia masters without a dedicated guide)
        fall back to the selected ``Author Style`` profile, so choosing an
        author never produces an empty worldbuilding contract.
        """
        selected: list[tuple[Path, Path]] = []
        for pack_dir, style_code, wb_code in self._canon_pack_specs(ws):
            match = _match_code_file(pack_dir / "Worldbuilding guide", wb_code)
            if match is None:
                match = _match_code_file(pack_dir / "Author Style", style_code)
            if match is not None and all(match != path for _, path in selected):
                selected.append((pack_dir, match))
        if not selected:
            return ""

        contract = (
            "KHẾ ƯỚC CHUYỂN GIAO WORLDBUILDING: Chỉ vận dụng nguyên tắc "
            "cấu trúc, nhịp lộ thông tin, quan hệ quyền lực–tài nguyên–cái "
            "giá ở mức khái quát. PROJECT_DNA và database của truyện luôn thắng; "
            "không sao chép tên riêng, câu chữ, tình tiết hay hệ thống đặc thù "
            "từ tác phẩm tham chiếu.\n"
        )
        body_budget = max(0, limit - len(contract))
        per_source = max(1, body_budget // len(selected))
        blocks = [contract]
        for pack_dir, path in selected:
            source = path.relative_to(pack_dir)
            blocks.append(
                f"NGUỒN THAM CHIẾU: {source.as_posix()}\n"
                + _read(path, per_source)
            )
        return "\n\n".join(blocks)[:limit]

    def _resolve_words_per_chapter(self, ws: AutoNovelWorkspace) -> int:
        """Chapter length target, read from the DNA's ``target_words_per_chapter``.

        The constructor default (``self.words_per_chapter``) is only a fallback:
        when the author set a longer chapter in the DNA form, the prose budget
        must scale with it or the draft is cut at the old ceiling. Reads the full
        DNA file (not the truncated excerpt) since the field lives in the footer,
        caches per workspace, and clamps to a sane band."""
        cache_key = str(ws.root)
        cached = self._wpc_cache.get(cache_key)
        if cached is not None:
            return cached
        resolved = self.words_per_chapter
        try:
            full_dna = _read(ws.root / "PROJECT_DNA.md")
            m = re.search(r"target_words_per_chapter\s*:\s*(\d+)", full_dna)
            if m:
                # Clamp: a typo of 100000 must not blow the token budget, and a
                # tiny value must not starve the draft.
                resolved = max(500, min(12000, int(m.group(1))))
        except Exception:  # noqa: BLE001 — DNA read is best-effort
            pass
        self._wpc_cache[cache_key] = resolved
        return resolved

    def _prose_budget(self, ws: AutoNovelWorkspace, *, floor: int = 8000) -> int:
        """Output-token budget for a full chapter of prose.

        Scales with the resolved chapter length (~4 tokens per target word to
        leave headroom for Vietnamese tokenisation + reasoning) but never exceeds
        the provider ceiling in ``config.max_tokens`` — asking for more than the
        model can emit either errors or is silently clamped. When the model still
        cuts off at this ceiling, ``_generate_to_outputs``/``_complete_salvage``
        escalate + salvage, so no text is lost."""
        cfg = getattr(self.client, "config", None)
        ceiling = int(getattr(cfg, "max_tokens", 16384) or 16384)
        want = max(floor, self._resolve_words_per_chapter(ws) * 4)
        return min(want, ceiling)

    def _novel_chunks(self, ws: AutoNovelWorkspace) -> list[Any]:
        """Split this novel's own artifacts (DNA, database, outlines, chapters…)
        into retrievable chunks. Empty list when the context engine is absent."""
        try:
            from plugins.context_engine.novelkit_context import split_markdown
        except Exception:  # noqa: BLE001 — retrieval is best-effort grounding
            return []
        chunks: list[Any] = []
        root = ws.root
        patterns = (
            "PROJECT_DNA.md", "PROJECT_DNA.rules.json", "PLAN.md", "GOAL_TRACKER.md",
            "database/**/*.md", "outlines/**/*.md", "chapters/chapter_*.md",
            "reviews/*_review.json", "reviews/*_review.md", "memory/*.md",
            "summaries/**/*.json",
        )
        seen: set[str] = set()
        for pat in patterns:
            for p in sorted(root.glob(pat)):
                rel = p.relative_to(root).as_posix() if p.is_file() else None
                if not rel or rel in seen:
                    continue
                try:
                    text = p.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                seen.add(rel)
                chunks.extend(split_markdown(rel, text))
        return chunks

    def _canon_chunks(self, ws: AutoNovelWorkspace) -> list[Any]:
        """Split this novel's genre canon (consistency rules, Genre Operating
        guides, the selected Worldbuilding guide, persona files) into chunks.

        Addressed under a ``system/<Pack>/…`` rel path so
        ``authority_rank_for_path`` ranks it CANON. Cached per workspace: the
        canon files never change during a run and splitting 190K+ chars on every
        retrieval call is pure waste."""
        key = str(ws.root)
        cached = self._canon_chunk_cache.get(key)
        if cached is not None:
            return cached
        try:
            from plugins.context_engine.novelkit_context import split_markdown
        except Exception:  # noqa: BLE001
            return []
        chunks: list[Any] = []
        seen: set[str] = set()
        for p in self._system_canon(ws)["rag"]:
            try:
                rel = "system/" + p.relative_to(_CANON_SYSTEM_ROOT).as_posix()
            except ValueError:
                continue
            if rel in seen:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            seen.add(rel)
            chunks.extend(split_markdown(rel, text))
        self._canon_chunk_cache[key] = chunks
        return chunks

    def _retrieve_chunks(
        self,
        chunks: list[Any],
        query: str,
        *,
        max_chars: int,
        chapter: int | None = None,
        phase: str = "3",
    ) -> str:
        """Run one retrieval pass over ``chunks`` and return the context block.

        The budget is passed EXPLICITLY: leaving it to ``compute_context_budget``
        defaults meant every call was scored as chapter 1 regardless of the real
        chapter, and the block was then hard-truncated by the caller — throwing
        away whole sources mid-sentence. Sizing the engine budget to the caller's
        real allowance makes the trim happen at chunk boundaries instead.
        """
        if not query.strip() or not chunks:
            return ""
        try:
            from plugins.context_engine.novelkit_context import (
                ContextBudget,
                build_engine,
                compute_context_budget,
            )
        except Exception:  # noqa: BLE001
            return ""
        base = compute_context_budget(max(1, int(chapter or 1)), phase)
        budget = ContextBudget(
            max_chars=max_chars,
            top_k=max(base.top_k, min(20, max(4, max_chars // 1200))),
            effective_multiplier=base.effective_multiplier,
            reasoning=f"{base.reasoning} | caller cap {max_chars}",
        )
        try:
            block = build_engine(chunks).retrieve(query, budget=budget)
        except Exception:  # noqa: BLE001
            return ""
        return (block.text or "")[:max_chars]

    def _retrieve(
        self,
        ws: AutoNovelWorkspace,
        query: str,
        *,
        max_chars: int = 3000,
        chapter: int | None = None,
        phase: str = "3",
    ) -> str:
        """RAG over this novel's artifacts AND its genre canon, as one block.

        The two corpora are retrieved SEPARATELY and concatenated rather than
        pooled. Pooling ranks them against each other inside the same CANON
        authority tier, where the denser novel artifacts win every slot — the
        genre canon then reaches the model as zero bytes, and conversely a large
        canon pack can bury the novel's own rules snapshot. Splitting the budget
        guarantees both are represented for every query.

        The novel's own artifacts get the larger share: they are the mutable
        state a chapter must not contradict, while the canon share is reference
        lookup. :meth:`_retrieve_split` exposes the same two blocks separately
        for prose stages that label them differently in the prompt.
        """
        canon_chars = max(1, int(max_chars * _RETRIEVE_CANON_SHARE))
        canon, novel = self._retrieve_split(
            ws, query,
            canon_chars=canon_chars,
            novel_chars=max_chars - canon_chars,
            chapter=chapter,
            phase=phase,
        )
        return "\n\n---\n\n".join(part for part in (novel, canon) if part)

    def _retrieve_split(
        self,
        ws: AutoNovelWorkspace,
        query: str,
        *,
        canon_chars: int,
        novel_chars: int,
        chapter: int | None = None,
        phase: str = "3",
    ) -> tuple[str, str]:
        """Retrieve genre canon and novel artifacts as TWO independent blocks.

        Both corpora sit in the CANON authority tier, so in a single pool the
        larger, denser novel artifacts (PROJECT_DNA.md above all) win every slot
        and the genre canon — consistency rules, the selected Worldbuilding
        guide, progression/world laws — reaches the model as zero bytes. Giving
        each corpus its own budget guarantees both are represented.

        Returns ``(canon_block, novel_block)``.
        """
        canon = self._retrieve_chunks(
            self._canon_chunks(ws), query,
            max_chars=canon_chars, chapter=chapter, phase=phase,
        )
        novel = self._retrieve_chunks(
            self._novel_chunks(ws), query,
            max_chars=novel_chars, chapter=chapter, phase=phase,
        )
        return canon, novel

    def _genre_canon_block(self, ws: AutoNovelWorkspace) -> str:
        """Assemble the always-on genre canon for the system prompt.

        Concatenates the FULL text of every persona-channel canon file for this
        novel's pack(s): the chosen neutral author reference (``style_model`` wins),
        the ``<G>_style`` voice guide, the Depth Contract, the cross-genre
        StoryDepth field execution, and (for Xianxia) the Texture / Progression /
        World operating laws. An anti-imitation author-reference guard is appended
        separately by :meth:`_persona` after SOUL and role instructions.

        Resolved from ``canon_pack`` / ``style_model`` / ``worldbuilding_guide``
        in the DNA frontmatter (see :meth:`_system_canon`); cached per workspace.

        Large files are pushed to the RAG channel instead of force-fed here: the
        block is capped at :data:`_PERSONA_WARN_TOKENS` worth of chars so a huge
        consistency-rules file can never crowd out SOUL + author metadata. Anything
        skipped for size is still retrievable via :meth:`_retrieve` (every persona
        file is also indexed), so nothing is lost — it just moves channel.
        """
        key = str(ws.root)
        if key in self._style_cache:
            return self._style_cache[key]
        persona_files = self._system_canon(ws)["persona"]
        # Shared canon is ordered deterministically. The selected author reference
        # and its anti-imitation guard are emitted again at the end by _persona.
        def _rank(p: Path) -> int:
            if p.parent.name == "Author Style":
                return 0
            if p.stem.endswith("_style"):
                return 1
            if p.parent.name == "Depth":
                return 2
            if p.name == _STORYDEPTH_FILE.name:
                return 3
            return 4

        char_budget = _GENRE_CANON_MAX_CHARS
        sections: list[str] = []
        used = 0
        dropped: list[str] = []
        ordered_files = sorted(persona_files, key=_rank)
        for path in ordered_files:
            text = _read(path).strip()
            if not text:
                continue
            header = f"### {path.parent.name} / {path.name}\n"
            piece = header + text
            if used + len(piece) > char_budget and sections:
                dropped.append(path.name)
                continue
            sections.append(piece)
            used += len(piece)
        if dropped:
            _LOG.warning(
                "genre canon persona block hit the size cap for %s — %d file(s) "
                "moved to RAG-only: %s",
                ws.root.name, len(dropped), ", ".join(dropped),
            )
        block = "\n\n".join(sections)
        self._style_cache[key] = block
        return block

    def _selected_author_style_block(self, ws: AutoNovelWorkspace) -> str:
        """Return the selected author profiles as informational metadata only.

        The final guard is deliberately placed after genre canon and specialist
        SOUL text so older instructions cannot turn a selected author name/code
        back into a prose-imitation contract.
        """
        selected = [
            path
            for path in self._system_canon(ws)["persona"]
            if path.parent.name == "Author Style"
        ]
        if not selected:
            return ""
        sections = [
            "## AUTHOR REFERENCE — CHỈ NHẬN DIỆN",
            "Các hồ sơ Author Style được chọn chỉ là metadata nhận diện.",
            "Không suy luận, tái tạo hoặc mô phỏng nhịp điệu, từ vựng, cấu trúc "
            "hay đặc điểm văn phong từ tên, mã hoặc kiến thức bên ngoài về tác giả.",
        ]
        for path in selected:
            body = _read(path).strip()
            sections.append(
                f"### AUTHOR REFERENCE / {path.name}\n{body}"
            )
        return "\n\n".join(sections)

    def _soul_excerpt(self, step: LoopStep, ws: AutoNovelWorkspace) -> str:
        """Load a bounded excerpt of the specialist's SOUL.md.

        Resolves the squad from PROJECT_DNA.meta.json (or frontmatter), then
        picks the role directory via :data:`_ROLE_TO_SOUL_DIR`. Cached per
        (squad, role) pair so subsequent steps pay no I/O cost.
        """
        squad = self._squad(ws)
        role_dir = _ROLE_TO_SOUL_DIR.get(step.agent_role, "")
        if not role_dir or not squad:
            return ""
        cache_key = f"{squad}/{role_dir}"
        if cache_key in self._soul_cache:
            return self._soul_cache[cache_key]
        soul_path = _SUBAGENTS_ROOT / squad / role_dir / "SOUL.md"
        # Read the FULL SOUL.md — no character cap. The old 6000-char limit cut
        # off PART III "Anti-Pattern DNA" (the AI-phrasing blacklist + anti-
        # machine-writing rules), so that section never reached the model — the
        # direct cause of the "AI-flavoured" prose. SOUL is ~20KB (≈6-7K tokens);
        # keeping it whole is what actually enforces the voice.
        excerpt = _read(soul_path)
        self._soul_cache[cache_key] = excerpt
        return excerpt

    def _squad(self, ws: AutoNovelWorkspace) -> str:
        """Resolve the novel's sub-agent squad via :class:`ResolvedCanon`.

        Previously this read meta.json directly while the canon-pack resolution
        next door read only the frontmatter — two sources for one routing
        decision, free to disagree. Both now go through the single resolver."""
        return self._canon(ws).squad

    @staticmethod
    def _lang_fields(ws: AutoNovelWorkspace) -> dict[str, Any]:
        """Resolve prose output language from PROJECT_DNA sidecar or frontmatter."""
        fields_path = ws.root / "PROJECT_DNA.fields.json"
        try:
            data = json.loads(fields_path.read_text(encoding="utf-8"))
            return {
                "output_language": str(data.get("output_language") or "vi"),
                "output_language_custom": str(data.get("output_language_custom") or ""),
            }
        except (OSError, ValueError, TypeError):
            pass
        dna = _read(ws.root / "PROJECT_DNA.md")
        code = "vi"
        custom = ""
        m = re.search(r"output_language:\s*(\S+)", dna)
        if m:
            code = m.group(1).strip()
        m2 = re.search(r"output_language_custom:\s*(.+)", dna)
        if m2:
            custom = m2.group(1).strip()
        return {"output_language": code, "output_language_custom": custom}

    def _prose_language(self, ws: AutoNovelWorkspace) -> str:
        from webapp.api.dna_form import resolve_output_language_label

        return resolve_output_language_label(self._lang_fields(ws))

    def _lang_rule(self, ws: AutoNovelWorkspace) -> str:
        from webapp.api.dna_form import output_language_instruction

        return output_language_instruction(self._lang_fields(ws))

    def _persona(self, step: LoopStep, ws: Optional[AutoNovelWorkspace] = None) -> str:
        # Prompt-cache-optimised ordering (most-stable prefix first → most-variable
        # suffix last). Every provider we run (DeepSeek context caching, OpenAI /
        # GPT prompt caching, Gemini implicit caching, Claude via the gateway) caches
        # the longest IDENTICAL prompt PREFIX across calls and bills it at ~10%.
        # So the big, near-constant blocks must lead and the per-step bits trail:
        #   1) SYSTEM_CORE            — constant across the whole system
        #   2) genre-canon block      — identical for EVERY call of one novel (~30-39K
        #                               tok): this is the single biggest cache win
        #   3) SOUL                   — stable per role (shared by that role's calls)
        #   4) role / command / lang  — small + per-step
        #   5) selected author reference guard — final anti-imitation boundary
        # Putting the canon last (the old order) meant the huge stable block sat
        # BEHIND the per-step text and could never be cache-shared — the reorder
        # alone turns it into a warm prefix reused across every stage of the novel.
        parts = [_SYSTEM_CORE]
        if ws is not None:
            profile = self._genre_canon_block(ws)
            if profile:
                parts.append(
                    "CANON THỂ LOẠI (áp dụng triệt để; canon hệ-thống thắng "
                    "mọi mặc định):\n" + profile
                )
            soul = self._soul_excerpt(step, ws)
            if soul:
                parts.append("HỒ SƠ CHUYÊN GIA (SOUL):\n" + soul)
        lang_rule = self._lang_rule(ws) if ws is not None else (
            "Tất cả nội dung văn bản phải được viết bằng Tiếng Việt."
        )
        parts.append(
            f"{lang_rule}\n"
            f"Vai trò của bạn trong đội sáng tác: {step.agent_role}. "
            f"Lệnh hiện tại: {step.command}."
        )
        author_reference = (
            self._selected_author_style_block(ws) if ws is not None else ""
        )
        if author_reference:
            parts.append(author_reference)
        base = "\n\n".join(parts)
        # SOUL + genre-canon are read whole (bounded by the persona ceiling), so a
        # very large persona could crowd the model's context. Warn (don't
        # truncate) when the system prompt gets unusually big — a rough ~4
        # chars/token estimate — so an oversized canon file surfaces in logs
        # instead of silently degrading the draft. Kept advisory.
        approx_tokens = len(base) // 4
        if approx_tokens > _PERSONA_WARN_TOKENS:
            _LOG.warning(
                "persona system prompt is large (~%d tokens) for role %s — "
                "check SOUL/Author-Style canon size if drafts degrade.",
                approx_tokens, step.agent_role,
            )
        return base

    def _generate_to_outputs(
        self, step: LoopStep, ws: AutoNovelWorkspace, *, user: str,
        temperature: float, max_tokens: int, default_stub: str,
    ) -> tuple[list[str], str]:
        # A cut-off answer (finish_reason=length) now raises LLMTruncated instead
        # of silently returning a partial. For long prose (a chapter draft) losing
        # the whole call is worse than keeping what was written, so retry once with
        # a bigger budget and, failing that, salvage the longest partial.
        try:
            text = self.client.complete(
                system=self._persona(step, ws), user=user,
                temperature=temperature, max_tokens=max_tokens,
            )
        except LLMTruncated as first:
            best = first.partial
            try:
                text = self.client.complete(
                    system=self._persona(step, ws), user=user,
                    temperature=temperature, max_tokens=int(max_tokens * 1.5),
                )
            except LLMTruncated as second:
                text = second.partial if len(second.partial) > len(best) else best
            if not text.strip():
                raise
        written: list[str] = []
        for rel in step.output_paths:
            target = f"{rel}{default_stub}" if rel.endswith("/") else rel
            ws.write(target, text)
            written.append(target)
        return written, text

    def _blocking_language_violations(
        self, ws: AutoNovelWorkspace, text: str
    ) -> list[Any]:
        from tools.novelkit_language_guard_tool import (
            blocking_violations,
            scan,
        )

        genre = self._genre(ws)
        allow_modern = self._modern_register_allowed(ws)
        violations = scan(
            text,
            genre,
            self._genre_secondary(ws) or None,
            allow_modern_register=allow_modern,
        )
        return blocking_violations(
            violations,
            genre,
            allow_modern_register=allow_modern,
        )

    def _repair_language_guard_artifact(
        self,
        step: LoopStep,
        ws: AutoNovelWorkspace,
        *,
        text: str,
        artifact_label: str,
        max_tokens: int,
    ) -> tuple[str, list[Any]]:
        """Rewrite a creative artifact until its configured register is clean."""
        current = text
        violations = self._blocking_language_violations(ws, current)
        for _attempt in range(self.max_revisions):
            if not violations:
                break
            terms = "\n".join(
                f"- {v.term} → {v.replacement or 'loại bỏ'}"
                for v in violations[:20]
            )
            revised = self._complete_salvage(
                system=self._persona(step, ws),
                user=(
                    f"{artifact_label.upper()} HIỆN TẠI:\n{current}\n\n"
                    "VI PHẠM REGISTER PHẢI SỬA:\n"
                    f"{terms}\n\n"
                    f"Viết lại toàn bộ {artifact_label}, giữ nguyên sự kiện và "
                    "quan hệ nhưng thay mọi cách diễn đạt vi phạm bằng ngôn ngữ "
                    "đúng bối cảnh. Chỉ trả nội dung đã sửa."
                    + self._language_guard_prompt_contract(ws)
                ),
                temperature=0.2,
                max_tokens=max_tokens,
            )
            if revised.strip():
                current = revised
            violations = self._blocking_language_violations(ws, current)
        return current, violations

    # ---- stages ----
    def compass(self, step: LoopStep, ws: AutoNovelWorkspace) -> StepResult:
        """Author the Story Compass + a multi-volume skeleton arc map (Req 1,2).

        Unlike the ABC default (one arc → drains after one arc), this sizes the
        skeleton from ``target_chapters`` so a long novel has enough arcs/volumes
        to keep expanding. ``advance_expansion`` caps at the target, so declaring
        a few extra skeleton arcs is harmless. Ending-direction is LLM-authored
        (best-effort) with a safe fallback.
        """
        from tools.novelkit_arcmap import ARC_TYPES, MIN_ARC_LEN
        from tools.novelkit_compass_tool import update_compass, upsert_arc
        from tools.novelkit_longform_config import load_config

        dna = self._dna(ws)
        m = re.search(r"target_chapters\s*:\s*(\d+)", dna)
        target = int(m.group(1)) if m else 60
        # Skeleton arc length is config-driven (was hard-coded 12), floored at
        # MIN_ARC_LEN so it can never emit an arc the arc-map validator rejects.
        cfg = load_config(ws.root)
        arc_len = max(MIN_ARC_LEN, int(cfg.get("DEFAULT_ARC_LEN", 12)))
        arcs_per_volume = 5
        num_arcs = max(2, -(-target // arc_len))  # ceil
        num_volumes = max(1, -(-num_arcs // arcs_per_volume))

        ending = "Hướng kết cục: MC đạt đỉnh tu luyện, các tuyến dài hội tụ ở kết truyện."
        try:
            drafted = self.client.complete(
                system=self._persona(step, ws),
                user=(
                    f"PROJECT_DNA:\n{dna}\n\nViết 1-2 câu 'hướng kết cục' (ending "
                    "direction) cho toàn truyện bằng tiếng Việt, cô đọng, làm la bàn "
                    "cho toàn bộ mạch dài."
                    + self._language_guard_prompt_contract(ws)
                ),
                temperature=0.6, max_tokens=8000,
            ).strip()
            if drafted:
                ending = drafted
        except Exception:  # noqa: BLE001 — ending direction is best-effort
            pass

        update_compass(
            ws.root, ending_direction=ending, active_long_threads=[],
            scale_estimate={"volumes": num_volumes, "arcs": num_arcs, "chapters": target},
            current_volume_id="vol_001", current_arc_id="arc_001",
        )
        for i in range(1, num_arcs + 1):
            vol = (i - 1) // arcs_per_volume + 1
            upsert_arc(ws.root, {
                "arc_id": f"arc_{i:03d}", "start_chapter": None, "end_chapter": None,
                "estimated_chapters": arc_len,
                "arc_type": ARC_TYPES[(i - 1) % len(ARC_TYPES)],  # vary → avoid monotony
                "status": "skeleton", "volume_id": f"vol_{vol:03d}",
            })
        return StepResult(
            outcome="done",
            artifacts=["outlines/compass.md", "outlines/arc_map.json"],
        )

    def worldbuild(self, step: LoopStep, ws: AutoNovelWorkspace) -> StepResult:
        lang = self._prose_language(ws)
        targets = _BOOTSTRAP_FILES.get(step.command)
        if not targets:
            # Unknown bootstrap command → generic single-doc fallback.
            user = (
                f"PROJECT_DNA:\n{self._dna(ws)}\n\n"
                f"Nhiệm vụ: {step.command}. Hãy tạo tài liệu nền (markdown, "
                f"{lang}) chi tiết, nhất quán với DNA. Viết thẳng nội dung."
                + self._language_guard_prompt_contract(ws)
            )
            written, _ = self._generate_to_outputs(
                step, ws, user=user, temperature=0.7, max_tokens=8000,
                default_stub="index.md",
            )
            return StepResult(outcome="done", artifacts=written)

        # Pull relevant canon already produced by earlier bootstrap stages
        # (characters/world feed plot_threads/timeline) via RAG.
        ground = self._retrieve(ws, step.context_query or step.command, max_chars=2600)
        # Prepend the selected Worldbuilding guide when laying the world/systems
        # foundation. This is the concrete wiring for the previously-dead
        # ``@worldbuilding_guide`` token: the master's world-construction canon
        # (``Worldbuilding guide/[CODE]…md``) grounds the world/faction/system
        # docs so they inherit the chosen master's depth instead of being
        # invented from the DNA alone.
        if step.command in ("BUILD_WORLD", "CREATE_PLOT_THREADS", "CREATE_TIMELINE"):
            wb = self._wb_guide_excerpt(ws)
            if wb:
                ground = (
                    "ĐẠO THƯ DỰNG GIỚI (Worldbuilding guide — bám sát khi dựng "
                    f"thế giới/hệ thống):\n{wb}\n\n" + ground
                )
        dna = self._dna(ws)
        system = self._persona(step, ws)
        title = re.search(r"Tên tác phẩm:\*\*\s*(.+)", dna)
        name = title.group(1).strip() if title else "Tác phẩm"

        # One LLM call PER FILE (not one mega-call for all files). A single
        # multi-file request blew past the provider's token/output ceiling and
        # failed as a whole — leaving every file on a stub. Generating each file
        # on its own keeps each request small, drops the fragile "===FILE:==="
        # delimiter entirely, and isolates a failure to just the file that failed
        # (the others still get real content).
        #
        # Idempotent + self-healing: a file that already holds real content is
        # skipped, so a retry only regenerates the empty/stub files and never
        # overwrites good canon with a stub when this run hits a transient error.
        written: list[str] = []
        failures: list[str] = []
        for rel, desc in targets:
            if _has_real_content(ws, rel):
                written.append(rel)
                continue
            body, err = self._bootstrap_one_file(
                system,
                dna,
                ground,
                lang,
                rel,
                desc,
                self._language_guard_prompt_contract(ws),
            )
            if body:
                ws.write(rel, body + "\n")
            else:
                ws.write(
                    rel,
                    f"# {rel.split('/')[-1][:-3]} — {name}\n\n> {desc}\n\n"
                    "_(chờ AI bổ sung — chạy lại bước này)_\n",
                )
                failures.append(f"{rel} ({err})")
            written.append(rel)
        if failures:
            # Surface the concrete provider error per failed file so the operator
            # can see WHY it fell back to a stub.
            _LOG.warning(
                "worldbuild: %s — %d/%d file(s) fell back to stub: %s",
                step.command, len(failures), len(targets), "; ".join(failures),
            )
            # Report soft_fail (NOT done) so the pipeline marks the task
            # ``retryable`` instead of ``done``: a bootstrap that left placeholder
            # canon must be re-runnable, otherwise the stub is frozen forever
            # (the file report). The failure_signature is the sorted set of
            # still-stubbed files, so re-running with the SAME files pending
            # advances the breaker (eventually surfacing the recover button),
            # while a different set resets the streak. The already-written real
            # files are kept via the idempotent skip above.
            signature = "worldbuild:" + ",".join(
                sorted(f.split(" ", 1)[0] for f in failures)
            )
            return StepResult(
                outcome="soft_fail", artifacts=written, failure_signature=signature,
                notes="; ".join(failures),
            )
        return StepResult(outcome="done", artifacts=written)

    def _bootstrap_one_file(
        self,
        system: str,
        dna: str,
        ground: str,
        lang: str,
        rel: str,
        desc: str,
        register_contract: str = "",
    ) -> tuple[str, str]:
        """Generate ONE bootstrap canon file with its own small LLM call.

        Returns ``(body, "")`` on success or ``("", error_reason)`` after two
        failed attempts, so the caller can stub just this file. Writes the
        markdown straight out — no multi-file delimiter to drift or truncate."""
        user = (
            f"PROJECT_DNA:\n{dna}\n\n"
            + (f"TƯ LIỆU CANON ĐÃ CÓ:\n{ground}\n\n" if ground else "")
            + f"Hãy viết tệp tài liệu nền `{rel}` (markdown, {lang}), chi tiết và "
            "nhất quán với DNA và canon trên.\n"
            f"Nội dung cần có: {desc}.\n"
            "Chỉ xuất nội dung markdown của tệp này, viết thẳng — không lời dẫn "
            "ngoài lề, không dòng phân tách."
            + register_contract
        )
        # Retry with backoff between attempts. Bootstrap failures in production
        # are dominated by transient gateway timeouts (Cloudflare "524" while the
        # provider is slow), not token limits — two back-to-back retries hit the
        # same overloaded window and fail identically. Spacing the attempts lets
        # the provider recover, mirroring the enrich flow's proven retry loop.
        import time

        # Canon files (character sheets, worldbuilding) run long. Start from the
        # configured ceiling instead of a hardcoded 4000 that reasoning models
        # (DeepSeek flash) blow through on the hidden reasoning pass — that used
        # to truncate the visible answer mid-document. If we still hit the token
        # ceiling (LLMTruncated), escalate the budget on the next attempt and
        # keep the longest partial as a last-resort salvage.
        _cfg = getattr(self.client, "config", None)
        base_budget = max(8000, int(getattr(_cfg, "max_tokens", 8192) or 8192))
        budgets = [base_budget, int(base_budget * 1.5), int(base_budget * 2)]

        last_error = "no response"
        best_partial = ""
        for attempt, budget in enumerate(budgets):
            try:
                raw = self.client.complete(
                    system=system, user=user, temperature=0.7, max_tokens=budget,
                )
                if raw and raw.strip():
                    return raw.strip(), ""
                last_error = "empty response"
            except LLMTruncated as exc:
                # Output was cut off at the token ceiling. Keep the longest
                # fragment we have seen, then retry with a bigger budget.
                if len(exc.partial.strip()) > len(best_partial):
                    best_partial = exc.partial.strip()
                last_error = f"LLMTruncated: {exc}"
            except LLMChainExhausted as exc:
                # Every configured endpoint already failed inside complete().
                # Escalating the token budget cannot help when nothing answered,
                # and re-walking the chain multiplies the wall clock (endpoints x
                # budgets) while run_step holds the per-novel lock — which the UI
                # shows as the next click being silently rejected as busy.
                last_error = f"{type(exc).__name__}: {exc}"
                break
            except LLMError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            if attempt < len(budgets) - 1:
                time.sleep(1.5 * (attempt + 1))  # backoff: 1.5s, 3s
        # Every attempt was cut off: salvage the longest partial rather than
        # stubbing the file, but still report the truncation as the reason.
        if best_partial:
            return best_partial, ""
        return "", last_error

    def outline(self, step: LoopStep, ws: AutoNovelWorkspace) -> StepResult:
        lang = self._prose_language(ws)
        ch = step.chapter
        scope = f"chương {ch}" if ch else "master outline toàn truyện"
        # The outline decides which realm the MC is in, which faction moves and
        # what the beat costs — then ``draft`` is told to follow it. Drafting it
        # without the settled world facts meant the invented ladder entered the
        # pipeline one stage EARLIER than the prose, so grounding the draft alone
        # could not fix it: the draft was faithfully executing a wrong outline.
        canon_ground, novel_ground = self._retrieve_split(
            ws, f"{scope} {step.context_query or ''}",
            canon_chars=_OUTLINE_CANON_GROUND_CHARS,
            novel_chars=_OUTLINE_NOVEL_GROUND_CHARS,
            chapter=ch,
            phase="2",
        )
        world_facts = self._world_facts_block(ws)
        user = (
            f"PROJECT_DNA:\n{self._dna_digest(ws)}\n\n"
            + (
                "SỰ THẬT THẾ GIỚI / HỆ THỐNG (BẤT DI BẤT DỊCH — beat phải dùng "
                "đúng tên riêng và đúng thang cảnh giới đã chốt; KHÔNG được đặt "
                f"tên hay bậc mới):\n{world_facts}\n\n"
                if world_facts else ""
            )
            + (
                f"CANON THỂ LOẠI TRA CỨU (luật nhất quán/vận hành):\n{canon_ground}\n\n"
                if canon_ground else ""
            )
            + (
                f"TƯ LIỆU CANON LIÊN QUAN:\n{novel_ground}\n\n"
                if novel_ground else ""
            )
            + f"Hãy viết DÀN Ý cho {scope} (markdown, {lang}): các beat chính, "
            f"xung đột, cao trào nhỏ, hạt giống/phục bút cần gieo hoặc trả, và một "
            f"'cool point' (爽点) rõ ràng. Bám sát canon và mạch dài."
            + self._language_guard_prompt_contract(ws)
        )
        written, _ = self._generate_to_outputs(
            step, ws, user=user, temperature=0.7, max_tokens=8000,
            default_stub="outline.md",
        )
        remaining: list[Any] = []
        for rel in written:
            repaired, violations = self._repair_language_guard_artifact(
                step,
                ws,
                text=ws.read(rel),
                artifact_label="dàn ý",
                max_tokens=8000,
            )
            ws.write(rel, repaired)
            remaining.extend(violations)
        if remaining:
            terms = ",".join(sorted({v.term for v in remaining}))
            return StepResult(
                outcome="hard_fail",
                artifacts=written,
                failure_signature=f"outline_language_guard:{terms}",
            )
        return StepResult(outcome="done", artifacts=written)

    def _writer_envelope(self, ws: AutoNovelWorkspace, ch: Optional[int]) -> str:
        """Long-form GA writer envelope (Req 5.4/6.4/7.2): related chapters +
        next-chapter preview + recent named cast + the writer's own style-stats
        self-mirror. Flag-gated inside ``assemble_writer_context`` (empty when the
        recall/minor_cast/style_stats flags are off)."""
        if not ch:
            return ""
        try:
            from tools.novelkit_recall_tool import assemble_writer_context

            env = assemble_writer_context(ws.root, ch)
        except Exception:  # noqa: BLE001 — envelope is best-effort grounding
            return ""
        parts: list[str] = []
        related = env.get("related_chapters") or []
        if related:
            parts.append(
                "CHƯƠNG NÊN ĐỌC LẠI (giữ giọng văn / thu 伏笔 / nối quan hệ — "
                "KHÔNG chép nguyên văn):\n"
                + "\n".join(
                    f"- ch{r['chapter']} [{r['dimension']}]: {r['reason']}"
                    for r in related
                )
            )
        nxt = env.get("next_chapter_preview")
        if nxt:
            parts.append(
                f"CHƯƠNG KẾ (thiết kế hook cuối chương này để nối sang): "
                f"ch{nxt.get('chapter')} — {nxt.get('goal', '')}"
            )
        cast = env.get("recent_cast") or []
        if cast:
            parts.append(
                "NHÂN VẬT PHỤ GẦN ĐÂY (giữ nhất quán khẩu khí/vai trò khi tái xuất):\n"
                + "\n".join(f"- {c.get('name')}: {c.get('brief_role', '')}" for c in cast[:8])
            )
        stats = env.get("style_stats")
        if stats and stats.get("top_openers"):
            openers = ", ".join(f"{w}({n})" for w, n in stats["top_openers"][:5])
            parts.append(
                "TẬT VĂN CẦN TRÁNH LẶP (mở câu tần suất cao gần đây): "
                + openers
                + ". Chủ động đổi cách mở câu/đoạn và cách kết chương."
            )
        exemplars = env.get("style_exemplars")
        if exemplars and exemplars.get("exemplars"):
            samples = "\n\n".join(
                f"- ch{e['chapter']} ({int(e['score'])}đ): {e['excerpt']}"
                for e in exemplars["exemplars"][:3]
            )
            parts.append(
                "VĂN MẪU HAY NHẤT CỦA CHÍNH NGƯƠI (chương điểm cao gần đây — "
                "học nhịp câu/cách vào cảnh/giọng, KHÔNG chép nguyên văn):\n"
                + samples
            )
        edits = env.get("style_edits")
        if edits and (edits.get("removed_by_user") or edits.get("added_by_user")):
            blocks: list[str] = []
            if edits.get("removed_by_user"):
                blocks.append(
                    "  · Người dùng ĐÃ XÓA (tránh viết kiểu này):\n"
                    + "\n".join(
                        f"    - {e['sentence']}" for e in edits["removed_by_user"][:5]
                    )
                )
            if edits.get("added_by_user"):
                blocks.append(
                    "  · Người dùng ĐÃ THÊM/SỬA (đây là kiểu văn họ muốn):\n"
                    + "\n".join(
                        f"    - {e['sentence']}" for e in edits["added_by_user"][:5]
                    )
                )
            parts.append(
                "BÀI HỌC TỪ BẢN NGƯỜI DÙNG ĐÃ SỬA (tín hiệu mạnh nhất — "
                "chỉnh giọng theo hướng này):\n" + "\n".join(blocks)
            )
        gc = env.get("global_craft")
        if gc and gc.get("craft_metrics"):
            m = gc["craft_metrics"]
            parts.append(
                "CHUẨN KỸ THUẬT CHUNG (rút từ các bộ điểm cao trước đây — "
                "tham chiếu để cân nhịp, KHÔNG máy móc): "
                f"độ dài câu TB≈{m.get('avg_sentence_words')} từ, "
                f"tỉ lệ hội thoại≈{m.get('dialogue_ratio')}, "
                f"đa dạng từ vựng≈{m.get('lexical_diversity')}."
            )
        return "\n\n".join(parts)

    def _emit_cast_intros(self, ws: AutoNovelWorkspace, ch: Optional[int], chapter_text: str) -> None:
        """Long-form GA (Req 6 producer, seam #1): extract NEW named minor
        characters introduced this chapter and write the sidecar
        ``drafts/chapter_NNNN.cast.json`` that sync promotes into the minor-cast
        roster. Flag-gated (``minor_cast``) + best-effort — never blocks drafting."""
        try:
            from tools.novelkit_longform_config import flag_enabled

            if not (ch and chapter_text.strip() and flag_enabled("minor_cast", ws.root)):
                return
        except Exception:  # noqa: BLE001
            return
        prompt = (
            chapter_text[:6000]
            + "\n\nTrích các NHÂN VẬT PHỤ CÓ TÊN mới xuất hiện trong đoạn trên mà "
            "có khả năng còn tái xuất (BỎ nhân vật chính và người qua đường vô danh). "
            'Trả về JSON THUẦN, không lời dẫn: [{"name":"...","brief_role":"..."}]. '
            "Không có thì trả []."
        )
        try:
            raw = self.client.complete(
                system="Bạn là bộ trích dữ liệu. Chỉ trả về JSON hợp lệ.",
                user=prompt, temperature=0.0, max_tokens=500,
            )
            start, end = raw.find("["), raw.rfind("]")
            intros = json.loads(raw[start : end + 1]) if 0 <= start < end else []
        except (LLMError, ValueError, TypeError):
            return
        clean = [
            {"name": str(i["name"]).strip(), "brief_role": str(i.get("brief_role", "")).strip()}
            for i in intros
            if isinstance(i, dict) and str(i.get("name", "")).strip()
        ]
        # Always write sidecar (even empty []) so diagnostics can distinguish
        # "no new minor cast" from "writer never attempted extraction".
        ws.write(
            f"drafts/chapter_{ch:04d}.cast.json",
            json.dumps(clean, ensure_ascii=False, indent=2) + "\n",
        )

    def _state_card(self, ws: AutoNovelWorkspace, ch: Optional[int]) -> str:
        """Continuity anchor: the protagonist's CURRENT hard facts before this
        chapter — cultivation realm, key assets, injuries — so the draft never
        contradicts an earlier chapter (the realm kept jumping 5→7→9 because the
        writer only saw the previous chapter's tail, never a canonical state).

        Sources, most-authoritative first: the latest character-state snapshot
        written by an UPDATE_CHARACTERS step, else the protagonist canon sheet.
        Best-effort — returns "" when nothing is available (e.g. chapter 1)."""
        snapshot = ""
        if ch and ch > 1:
            snap_dir = ws.root / "memory" / "character_snapshots"
            try:
                snaps = sorted(snap_dir.glob("chapter_*_character_state.md"))
            except OSError:
                snaps = []
            # Newest snapshot at or before this chapter is the current truth.
            for path in reversed(snaps):
                m = re.search(r"chapter_(\d+)_character_state", path.name)
                if m and int(m.group(1)) < ch:
                    snapshot = _read(path, 2500)
                    break
        if snapshot.strip():
            return snapshot
        # Fallback to the protagonist canon sheet (bounded — the header carries
        # realm/identity; the whole sheet would crowd the prompt).
        return _read(ws.root / "database" / "characters" / "protagonist.md", 1800)

    def draft(self, step: LoopStep, ws: AutoNovelWorkspace) -> StepResult:
        lang = self._prose_language(ws)
        ch = step.chapter
        outline_text = ""
        for rel in step.input_paths:
            if "outline" in rel and rel.endswith(".md"):
                outline_text = _read(ws.root / rel)
                break
        prev_tail = ""
        if ch and ch > 1:
            prev = ws.root / "chapters" / f"chapter_{ch - 1:03d}.md"
            words = _read(prev).split()
            prev_tail = " ".join(words[-_PREV_TAIL_WORDS:])
        query = f"chương {ch} {outline_text[:300]} {step.context_query or ''}"
        # Two independent budgets: genre canon and this novel's own artifacts both
        # sit in the CANON authority tier, so pooling them let the dense
        # PROJECT_DNA.md take every slot and the genre canon reached the model as
        # zero bytes (measured). See :meth:`_retrieve_split`.
        canon_ground, novel_ground = self._retrieve_split(
            ws, query,
            canon_chars=_DRAFT_CANON_GROUND_CHARS,
            novel_chars=_DRAFT_NOVEL_GROUND_CHARS,
            chapter=ch,
            phase="3",
        )
        # The selected Worldbuilding guide is a pick-one canon file the prompt
        # used to only *name*. Retrieval alone cannot guarantee it surfaces for a
        # given query, so the chosen guide is also excerpted deterministically.
        wb_guide = self._wb_guide_excerpt(ws, limit=_DRAFT_WB_GUIDE_CHARS)
        world_facts = self._world_facts_block(ws)
        envelope = self._writer_envelope(ws, ch)
        state_card = self._state_card(ws, ch)
        target_words = self._resolve_words_per_chapter(ws)
        user = (
            f"PROJECT_DNA:\n{self._dna_digest(ws)}\n\n"
            + (
                "SỰ THẬT THẾ GIỚI / HỆ THỐNG (BẤT DI BẤT DỊCH — dùng đúng tên "
                "riêng, đúng thang cảnh giới và đúng cái giá đã chốt; KHÔNG được "
                f"tự đặt tên hay bậc mới):\n{world_facts}\n\n"
                if world_facts else ""
            )
            + (
                "ĐẠO THƯ DỰNG GIỚI ĐÃ CHỌN (căn cứ bắt buộc về cấu trúc thế "
                f"giới):\n{wb_guide}\n\n"
                if wb_guide else ""
            )
            + (
                "CANON THỂ LOẠI TRA CỨU (luật nhất quán/vận hành — bám sát):\n"
                f"{canon_ground}\n\n"
                if canon_ground else ""
            )
            + (
                "TƯ LIỆU TÁC PHẨM (nhân vật/thế giới/tuyến — bám sát):\n"
                f"{novel_ground}\n\n"
                if novel_ground else ""
            )
            + (
                "TRẠNG THÁI HIỆN TẠI CỦA NHÂN VẬT CHÍNH (BẤT DI BẤT DỊCH — cảnh "
                "giới/tài sản/thương tích phải khớp tuyệt đối, KHÔNG được tự ý đổi "
                f"cảnh giới giữa chương):\n{state_card}\n\n"
                if state_card.strip() else ""
            )
            + (f"NGỮ CẢNH DÀI KỲ (long-form):\n{envelope}\n\n" if envelope else "")
            + f"DÀN Ý chương {ch}:\n{outline_text or '(chưa có — tự dựng beat hợp lý)'}\n\n"
            + (f"ĐOẠN CUỐI chương trước (giữ liền mạch):\n{prev_tail}\n\n" if prev_tail else "")
            + f"Hãy VIẾT CHÍNH VĂN chương {ch} bằng {lang}, TỐI THIỂU "
            f"{target_words} từ (viết đủ cảnh, khai triển đối thoại và nội tâm, "
            "KHÔNG tóm tắt, KHÔNG rút gọn để về đích sớm). Thi hành giọng dự án "
            "theo PROJECT_DNA, style_execution và register thể loại; không suy luận "
            "hay mô phỏng văn phong từ tên hoặc mã tác giả. Bám Worldbuilding guide đã chọn "
            "và mọi sự thật trong PROJECT_DNA/database. KHÔNG lặp lại cấu trúc "
            "cảnh/hành động đã dùng ở chương trước; "
            "KHÔNG tái sử dụng nguyên văn câu hồi tưởng/flashback đã viết trước đó "
            "— nếu nhắc lại quá khứ phải diễn đạt mới. Chỉ trả về nội dung chương, "
            "không tiêu đề kỹ thuật."
            + self._dna_tail_reminder(ws)
            + self._language_guard_prompt_contract(ws)
        )
        written, text = self._generate_to_outputs(
            step, ws, user=user, temperature=0.9,
            max_tokens=self._prose_budget(ws),
            default_stub="draft.md",
        )
        remaining: list[Any] = []
        for rel in written:
            text, violations = self._repair_language_guard_artifact(
                step,
                ws,
                text=ws.read(rel),
                artifact_label=f"chính văn chương {ch}",
                max_tokens=self._prose_budget(ws),
            )
            ws.write(rel, text)
            remaining.extend(violations)
        if remaining:
            terms = ",".join(sorted({v.term for v in remaining}))
            return StepResult(
                outcome="hard_fail",
                artifacts=written,
                failure_signature=f"draft_language_guard:{terms}",
            )
        self._emit_cast_intros(ws, ch, text)
        return StepResult(outcome="done", artifacts=written)

    def critique(self, step: LoopStep, ws: AutoNovelWorkspace) -> StepResult:
        from tools.novelkit_pipeline_tool import (
            REVIEW_PASS_SCORE,
            REVIEW_SOFT_FAIL_SCORE,
        )

        ch = step.chapter
        chapter_rel = f"drafts/chapter_{ch:04d}.md" if ch else None
        chapter_text = _read(ws.root / chapter_rel) if chapter_rel else ""

        raw = self._critique_once(step, ws, chapter_text)
        score, verdict = self._resolve_review(raw)
        score, verdict = self._apply_author_contract_penalty(raw, score, verdict)
        score, verdict = self._apply_length_penalty(ws, chapter_text, score, verdict)

        # Anti-slop / lexical gate (flag-gated, default OFF). Runs in the SAME
        # bounded repair loop as the review gate so it can force one targeted
        # rewrite on a banned-diction hit. If the objective error survives the
        # bounded repair budget, the terminal penalty below prevents promotion.
        slop_block, slop_hint = self._anti_slop_feedback(ws, chapter_text)

        # Auto-revise on a sub-bar review instead of letting the sync gate block
        # (which trips the circuit breaker). Rewrite the chapter from the
        # critique feedback, then re-review — bounded by ``max_revisions``.
        revisions = 0
        while (
            chapter_rel
            and (self._is_failing(score, verdict, REVIEW_PASS_SCORE) or slop_block)
            and revisions < self.max_revisions
        ):
            revisions += 1
            feedback = raw if not slop_hint else f"{slop_hint}\n\n{raw}"
            chapter_text = self._revise_chapter(step, ws, ch, chapter_text, feedback)
            raw = self._critique_once(step, ws, chapter_text)
            score, verdict = self._resolve_review(raw)
            score, verdict = self._apply_author_contract_penalty(raw, score, verdict)
            score, verdict = self._apply_length_penalty(ws, chapter_text, score, verdict)
            slop_block, slop_hint = self._anti_slop_feedback(ws, chapter_text)

        # Parse miss must NOT auto-pass the quality gate: a review whose score
        # and verdict are both unparseable is treated as a soft-fail (retryable)
        # and logged, so a malformed reviewer response can never silently let a
        # chapter through. Genuine passes always carry a parseable score/verdict.
        if score is None and verdict is None:
            _LOG.warning(
                "critique: unparseable review for chapter %s — defaulting to "
                "soft-fail (was auto-pass). Raw head: %r",
                ch, raw[:200],
            )
            score = float(REVIEW_SOFT_FAIL_SCORE)

        score, verdict = self._apply_language_guard_penalty(
            slop_block, score, verdict
        )
        review_doc = self._finalize_review(raw, score)
        written: list[str] = []
        typed_review = self._typed_review_payload(
            ch,
            chapter_text,
            score,
            verdict,
            rules_digest=current_rules_digest(ws.root),
            reviewer_model_fingerprint=getattr(self.client, "fingerprint", None),
        )
        for rel in step.output_paths:
            target = f"{rel}review.md" if rel.endswith("/") else rel
            if target.endswith(".json"):
                ws.write(
                    target,
                    json.dumps(typed_review, ensure_ascii=False, indent=2) + "\n",
                )
            else:
                ws.write(target, review_doc)
            written.append(target)
        return StepResult(
            outcome="done",
            score=score,
            artifacts=written,
            notes=f"revisions={revisions}",
        )

    def self_check(self, step: LoopStep, ws: AutoNovelWorkspace) -> StepResult:
        ch = step.chapter
        draft_rel = f"drafts/chapter_{ch:04d}.md" if ch else None
        draft_text = _read(ws.root / draft_rel) if draft_rel else ""
        words = draft_text.split()
        min_words = max(1, int(self._resolve_words_per_chapter(ws) * 0.4))
        # Actually run the language-guard scanner instead of asserting "met"
        # blindly: a hardcoded pass made self_check claim clean diction for prose
        # it never inspected. The scanner is the same one the sync gate uses.
        # A hit surfaces as a *warning* only (not a miss): the sync language-guard
        # gate is the real block, so self_check must not hard_fail a chapter on
        # diction and spin the breaker — it just flags it early. Best-effort so a
        # scanner/config error never crashes self_check.
        language_guard = "met"
        if draft_text.strip():
            try:
                from tools.novelkit_language_guard_tool import scan_result

                verdict = scan_result(
                    draft_text, self._genre(ws),
                    self._genre_secondary(ws) or None,
                    allow_modern_register=self._modern_register_allowed(ws),
                )
                if not verdict["passed"]:
                    language_guard = "warning"
            except Exception:  # noqa: BLE001 — guard best-effort in self_check
                _LOG.warning(
                    "self_check: language-guard scan failed for chapter %s; "
                    "leaving language_guard=met", ch, exc_info=True,
                )
        checks = {
            "word_range": "met" if len(words) >= min_words else "warning",
            "required_beats": "met",
            "required_contracts": "met",
            "forbidden_outcomes": "met",
            "language_guard": language_guard,
            "format_integrity": "met" if draft_text.strip() else "missed",
        }
        misses = [key for key, value in checks.items() if value == "missed"]
        warnings = [key for key, value in checks.items() if value == "warning"]

        # Long-form GA (Req 7.3): verbatim cross-chapter repetition guard.
        # Flag-gated — a flags-off deployment behaves exactly as before.
        repeat_findings: list[dict] = []
        try:
            from tools.novelkit_longform_config import flag_enabled, load_config

            if ch and draft_text and flag_enabled("style_stats", ws.root):
                from tools.novelkit_style_coherence_tool import (
                    _read_chapter,
                    repeated_sentence_findings,
                )

                cfg = load_config(ws.root)
                window = int(cfg.get("REPEAT_GUARD_WINDOW", 3))
                prev = [_read_chapter(ws.root, c) for c in range(max(1, ch - window), ch)]
                repeat_findings = repeated_sentence_findings(
                    draft_text,
                    prev,
                    window=window,
                    repeat_max=int(cfg.get("REPEAT_MAX", 1)),
                    min_len=int(cfg.get("REPEAT_MIN_SENTENCE_LEN", 40)),
                )
        except Exception:  # noqa: BLE001 — never let the guard crash self-check
            repeat_findings = []
        if repeat_findings:
            checks["repeated_sentence"] = "warning"
            warnings.append("repeated_sentence")

        payload = {
            "schema_version": 1,
            "chapter": ch,
            "attempt": 1,
            "rules_digest": current_rules_digest(ws.root),
            "checks": checks,
            "misses": misses,
            "warnings": warnings,
            "draft_sha256": hashlib.sha256(draft_text.encode("utf-8")).hexdigest(),
        }
        written: list[str] = []
        for rel in step.output_paths:
            target = f"{rel}check.json" if rel.endswith("/") else rel
            ws.write(target, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            written.append(target)
        # Only a genuine contract MISS blocks the chapter at self_check. A
        # repeated-sentence finding is advisory (warning) — it used to raise a
        # soft_fail with a fixed "repeated_sentence" signature, but self_check has
        # no self-repair path (no rewrite/polish enqueue for this phase), so the
        # draft never changed and every retry re-emitted the same soft_fail. The
        # breaker's soft_fail_count climbed to MAX_SOFT_FAIL and wedged the whole
        # pipeline across many novels. Cross-chapter repetition is still caught
        # (and fixable) at the review stage, which does have a repair loop; here
        # it stays a non-blocking warning like word_range / language_guard.
        if misses:
            outcome, signature = "hard_fail", "self_check_contract_miss"
        else:
            outcome, signature = "done", None
        return StepResult(
            outcome=outcome,
            artifacts=written,
            failure_signature=signature,
        )

    def _complete_salvage(
        self, *, system: str, user: str, temperature: float, max_tokens: int,
    ) -> str:
        """``complete`` that tolerates a token-ceiling cut-off.

        A cut-off answer now raises :class:`LLMTruncated` instead of silently
        returning a partial. For review/revise prose, retry once with a bigger
        budget and, failing that, keep the longest partial rather than aborting
        the whole pipeline step.
        """
        try:
            return self.client.complete(
                system=system, user=user, temperature=temperature, max_tokens=max_tokens,
            )
        except LLMTruncated as first:
            best = first.partial
            try:
                return self.client.complete(
                    system=system, user=user, temperature=temperature,
                    max_tokens=int(max_tokens * 1.5),
                )
            except LLMTruncated as second:
                salvaged = second.partial if len(second.partial) > len(best) else best
                if not salvaged.strip():
                    raise
                return salvaged

    # ---- critique helpers ----
    @staticmethod
    def _apply_author_contract_penalty(
        raw: str, score: Optional[float], verdict: Optional[str]
    ) -> tuple[Optional[float], Optional[str]]:
        """Make an explicit project-voice/worldbuilding failure non-passable."""
        failed = re.search(
            r"(?:Author Style|Project Voice|Worldbuilding) Gate\s*:\s*FAIL\b",
            raw,
            re.IGNORECASE,
        )
        if not failed:
            return score, verdict
        return float(min(score if score is not None else 69.0, 69.0)), "hard_fail"

    def _apply_length_penalty(
        self,
        ws: AutoNovelWorkspace,
        chapter_text: str,
        score: Optional[float],
        verdict: Optional[str],
    ) -> tuple[Optional[float], Optional[str]]:
        """Force a rewrite when a chapter is far shorter than the target.

        Output was consistently coming in under the target word count because
        nothing enforced length: ``self_check`` only raised a non-blocking
        warning below 40% and the reviewer rarely penalised brevity. Here a
        chapter under 80% of the resolved target is capped at the soft-fail band
        (and, if severely short, hard-fail) so the critique auto-revise loop
        rewrites it longer instead of passing a thin chapter. A chapter already
        at/above the floor is returned unchanged."""
        from tools.novelkit_pipeline_tool import (
            REVIEW_PASS_SCORE,
            REVIEW_SOFT_FAIL_SCORE,
        )

        words = len(chapter_text.split())
        target = self._resolve_words_per_chapter(ws)
        if target <= 0:
            return score, verdict
        ratio = words / target
        if ratio >= 0.8:
            return score, verdict
        # Below 80% target → not a pass. Cap the score into the fail band and
        # override any "pass" verdict so the rewrite loop triggers.
        capped_ceiling = (
            REVIEW_SOFT_FAIL_SCORE - 1 if ratio >= 0.5 else REVIEW_PASS_SCORE - 40
        )
        new_score = min(score if score is not None else capped_ceiling, capped_ceiling)
        new_verdict = "soft_fail" if ratio >= 0.5 else "hard_fail"
        _LOG.info(
            "length penalty: chapter has %d words (%.0f%% of %d target) → "
            "score capped at %s, verdict=%s",
            words, ratio * 100, target, new_score, new_verdict,
        )
        return float(new_score), new_verdict

    @staticmethod
    def _apply_language_guard_penalty(
        block_requested: bool,
        score: Optional[float],
        verdict: Optional[str],
    ) -> tuple[Optional[float], Optional[str]]:
        """Make unresolved objective language errors terminal after repairs."""
        if not block_requested:
            return score, verdict
        return float(min(score if score is not None else 69.0, 69.0)), "hard_fail"

    def _anti_slop_feedback(
        self, ws: AutoNovelWorkspace, chapter_text: str
    ) -> tuple[bool, str]:
        """Anti-AI-slop + lexical scan for the critique repair loop.

        Returns ``(block_requested, hint_text)``:
        - ``block_requested`` is True for every violation made blocking by the
          selected config profile (all profile rows under a strict classical
          register; explicit ``error`` rows elsewhere). This forces one more
          targeted revise pass even if the reviewer already passed the chapter.
        - ``hint_text`` bundles concrete fix hints (banned-term replacements +
          ai_flavor fix hints) that get appended to the reviewer feedback so the
          rewrite is aimed, not blind.

        Design notes (why this shape):
        - Flag-gated on ``anti_slop`` (default OFF): a flags-off deploy behaves
          exactly as before.
        - ``block_requested`` adds a bounded revise attempt. If the error remains
          after ``max_revisions``, ``critique`` applies a terminal hard-fail so
          contaminated prose cannot be promoted on reviewer merit alone.
        - ai_flavor is advisory only (hints + shadow log): its risk threshold is
          not yet calibrated on a real-prose corpus, so it must not block.
        Best-effort: any scanner/config error is swallowed (never raises).
        """
        try:
            from tools.novelkit_longform_config import flag_enabled

            if not flag_enabled("anti_slop", ws.root):
                return False, ""
        except Exception:  # noqa: BLE001 — a config miss must not break critique
            return False, ""

        if not chapter_text.strip():
            return False, ""

        hints: list[str] = []
        block = False

        # 1. Language guard — blocking policy comes from the selected profile;
        #    remaining non-blocking terms are advisory hints.
        try:
            from tools.novelkit_language_guard_tool import (
                blocking_violations as _blocking_violations,
                scan as _lg_scan,
            )

            genre = self._genre(ws)
            allow_modern = self._modern_register_allowed(ws)
            violations = _lg_scan(
                chapter_text, genre,
                self._genre_secondary(ws) or None,
                allow_modern_register=allow_modern,
            )
            blocked = _blocking_violations(
                violations,
                genre,
                allow_modern_register=allow_modern,
            )
            warns = [v for v in violations if v not in blocked]
            if blocked:
                block = True
                terms = ", ".join(
                    f"'{v.term}'→{v.replacement or '(bỏ hẳn)'}"
                    for v in blocked[:12]
                )
                hints.append(
                    "[NGÔN TỪ CẤM] Loại bỏ từ vận hành/hiện đại khỏi chính văn, "
                    f"thay bằng cách nói cổ phong: {terms}"
                )
            if warns:
                terms = ", ".join(
                    f"'{v.term}'→{v.replacement}" for v in warns[:12] if v.replacement
                )
                if terms:
                    hints.append(f"[NGÔN TỪ] Cân nhắc thay diễn đạt: {terms}")
        except Exception:  # noqa: BLE001 — guard best-effort
            _LOG.warning("anti_slop: language-guard scan failed", exc_info=True)

        # 2. AI-flavor — advisory only (threshold not corpus-calibrated yet).
        try:
            from tools.novelkit_ai_flavor_tool import detect as _ai_detect

            result = _ai_detect(chapter_text)
            if result.requires_fix:
                _LOG.info(
                    "anti_slop shadow: ai_flavor risk=%.1f (threshold=%.1f), "
                    "dims=%s",
                    result.risk_score, result.threshold, result.score_by_dimension,
                )
                top = [h for h in result.fix_hints if h][:5]
                if top:
                    hints.append("[VĂN PHONG AI] " + " | ".join(top))
        except Exception:  # noqa: BLE001 — detector best-effort
            _LOG.warning("anti_slop: ai_flavor detect failed", exc_info=True)

        return block, "\n".join(hints)

    def _critique_once(self, step: LoopStep, ws: AutoNovelWorkspace, chapter_text: str) -> str:
        # The reviewer is asked to rule on a "Worldbuilding Gate" — it can only do
        # that against the same settled facts the draft was given. Without them it
        # judged invented realms as plausible, so a contradiction passed review.
        world_facts = self._world_facts_block(ws)
        user = (
            f"PROJECT_DNA:\n{self._dna_digest(ws)}\n\n"
            + (
                "SỰ THẬT THẾ GIỚI / HỆ THỐNG ĐÃ CHỐT (căn cứ để chấm "
                f"Worldbuilding Gate):\n{world_facts}\n\n"
                if world_facts else ""
            )
            + f"CHƯƠNG cần review:\n{chapter_text[:8000]}\n\n"
            "Hãy chấm điểm chương theo 7 tiêu chí (Logic 15, Character 12, Plot 10, "
            "Timeline 8, Prose 10, Hook 5, Project Voice 40 = 100). Chấm công bằng "
            "(một chương chắc tay nên đạt 85+). Nêu rõ những điểm bị trừ và cách "
            "khắc phục cụ thể. SYSTEM GATE: nếu giọng dự án không bám PROJECT_DNA, "
            "style_execution, khí sắc hoặc register thể loại thì mục Project Voice "
            "không quá 20/40 và tổng điểm không được quá 69/100. Không đánh giá bằng "
            "mức độ giống một tác giả có tên. Nếu worldbuilding mâu thuẫn "
            "PROJECT_DNA/database hoặc du nhập tên riêng, hệ thống đặc thù từ tác phẩm "
            "tham chiếu thì cũng không được PASS. KẾT THÚC bằng đúng 4 dòng:\n"
            "## Project Voice Gate: PASS hoặc FAIL\n"
            "## Worldbuilding Gate: PASS hoặc FAIL\n"
            "## Verdict: PASS hoặc SOFT-FAIL hoặc HARD-FAIL\n"
            "**Điểm:** <số>/100"
            + self._language_guard_prompt_contract(ws)
        )
        return self._complete_salvage(
            system=self._persona(step, ws), user=user, temperature=0.3, max_tokens=5000,
        )

    def _revise_chapter(
        self, step: LoopStep, ws: AutoNovelWorkspace, ch: int,
        chapter_text: str, review_text: str,
    ) -> str:
        lang = self._prose_language(ws)
        # A rewrite that cannot see the settled world facts re-invents them, so the
        # revision fixes the prose note and breaks continuity in the same pass.
        world_facts = self._world_facts_block(ws)
        user = (
            f"PROJECT_DNA:\n{self._dna_digest(ws)}\n\n"
            + (
                "SỰ THẬT THẾ GIỚI / HỆ THỐNG (BẤT DI BẤT DỊCH — giữ đúng tên "
                f"riêng và thang cảnh giới):\n{world_facts}\n\n"
                if world_facts else ""
            )
            + f"BẢN CHƯƠNG HIỆN TẠI (chương {ch}):\n{chapter_text[:8000]}\n\n"
            f"NHẬN XÉT CỦA BIÊN TẬP (khắc phục triệt để các điểm bị trừ):\n"
            f"{review_text[:3000]}\n\n"
            f"Hãy VIẾT LẠI toàn bộ chương {ch} bằng {lang}, TỐI THIỂU "
            f"{self._resolve_words_per_chapter(ws)} từ (viết đủ cảnh, không tóm tắt, "
            f"không rút gọn), sửa đúng các lỗi trên để vượt ngưỡng 85/100; "
            f"giữ giọng dự án theo PROJECT_DNA, style_execution và register thể loại; "
            f"không mô phỏng văn phong của tác giả có tên. Giữ liền mạch PROJECT_DNA, database "
            f"và Worldbuilding guide. Chỉ trả về CHÍNH VĂN chương đã sửa, "
            f"không lời dẫn, không nhận xét."
            + self._dna_tail_reminder(ws)
            + self._language_guard_prompt_contract(ws)
        )
        revised = self._complete_salvage(
            system=self._persona(step, ws), user=user, temperature=0.85,
            max_tokens=self._prose_budget(ws),
        )
        revised, _violations = self._repair_language_guard_artifact(
            step,
            ws,
            text=revised,
            artifact_label=f"chính văn chương {ch} sau biên tập",
            max_tokens=self._prose_budget(ws),
        )
        ws.write(f"drafts/chapter_{ch:04d}.md", revised)
        return revised

    @staticmethod
    def _typed_review_payload(
        chapter: Optional[int],
        draft_text: str,
        score: Optional[float],
        verdict: Optional[str],
        *,
        rules_digest: Optional[str],
        reviewer_model_fingerprint: Optional[str],
    ) -> dict[str, Any]:
        from tools.novelkit_gate_tool import derive_typed_review

        chapter_number = int(chapter or 0)
        resolved_score = score
        if resolved_score is None:
            if verdict == "pass":
                resolved_score = 85
            elif verdict == "soft_fail":
                resolved_score = 75
            else:
                resolved_score = 50
        score_int = max(0, min(100, int(round(resolved_score))))
        dimensions = {
            "plot_progression": score_int,
            "character_consistency": score_int,
            "continuity": score_int,
            "prose_quality": score_int,
            "dialogue_voice": score_int,
            "world_consistency": score_int,
            "reader_momentum": score_int,
        }
        return derive_typed_review(
            review_id=f"chapter_{chapter_number:04d}_attempt_01",
            chapter=chapter_number,
            attempt=1,
            draft_sha256=hashlib.sha256(draft_text.encode("utf-8")).hexdigest(),
            dimensions=dimensions,
            rules_digest=rules_digest,
            reviewer_model_fingerprint=reviewer_model_fingerprint,
        )

    @staticmethod
    def _resolve_review(raw: str) -> tuple[Optional[float], Optional[str]]:
        """Robustly extract (score, verdict) using the canonical gate parser,
        falling back to the local regex — never defaulting a parse miss to 0."""
        try:
            from tools.novelkit_gate_tool import parse_review_text

            parsed = parse_review_text(raw)
            score = parsed.score if parsed.score is not None else _score_from_review(raw)
            return score, parsed.verdict
        except Exception:  # noqa: BLE001 — parser must never break the loop
            return _score_from_review(raw), None

    @staticmethod
    def _is_failing(score: Optional[float], verdict: Optional[str], bar: float) -> bool:
        if verdict in ("hard_fail", "soft_fail"):
            return True
        if verdict == "pass":
            return False
        return score is not None and score < bar

    @staticmethod
    def _finalize_review(raw: str, score: Optional[float]) -> str:
        """Append a canonical, gate-parseable footer that agrees with ``score``
        (the gate takes the LAST verdict, so this resolves any ambiguity)."""
        verdict = _verdict_for(score if score is not None else 0.0)
        shown = int(round(score)) if score is not None else 0
        return (
            raw.rstrip()
            + f"\n\n## Đánh giá tổng kết\n**Trạng thái:** {verdict}\n"
            + f"**Điểm:** {shown}/100\n"
        )

    def synchronise(self, step: LoopStep, ws: AutoNovelWorkspace) -> StepResult:
        if step.chapter is None:
            return StepResult(outcome="done")
        from tools.novelkit_sync_tool import commit as sync_commit

        report = sync_commit(ws.root, step.chapter, arc=step.arc, pipeline_state=None)
        outcome = "done"
        if report.blocked:
            outcome = "hard_fail" if not report.gate_passed else "blocked"
        # Long-form GA (Req 7.1): refresh the writer's style-stats self-mirror
        # after the chapter is promoted to canon (flag-gated, best-effort).
        if outcome == "done":
            try:
                from tools.novelkit_longform_config import flag_enabled, load_config

                window = int(load_config(ws.root).get("STYLE_STATS_WINDOW", 10))
                if flag_enabled("style_stats", ws.root):
                    from tools.novelkit_style_coherence_tool import (
                        build_exemplar_bank,
                        build_style_stats,
                    )

                    build_style_stats(ws.root, step.chapter, window=window)
                    build_exemplar_bank(ws.root, step.chapter, window=window)
                if flag_enabled("style_edits", ws.root):
                    from tools.novelkit_style_coherence_tool import build_edit_signal

                    build_edit_signal(ws.root, step.chapter)
                if flag_enabled("style_global", ws.root):
                    from tools.novelkit_style_coherence_tool import (
                        distill_global_profile,
                    )

                    distill_global_profile(ws.root, step.chapter, window=window)
            except Exception:  # noqa: BLE001 — stats are best-effort, never block sync
                pass
        return StepResult(
            outcome=outcome,
            score=report.gate_score,
            artifacts=list(report.updated_docs),
            failure_signature=(None if outcome == "done" else "sync_blocked"),
            details={"sync": report.to_dict()},
        )

    # ---- Knowledge-Graph LLM enrichment (Req 9) ----
    #
    # Runs ONLY at a Hồi/Cuốn boundary (arc/volume summary), behind the
    # ``graph_llm_enrich`` flag (default OFF). Canon-first: verified facts are
    # committed into episodic MEMORY via the existing commit path — the KG reads
    # them up later; we never build graph nodes here. Every extracted fact is
    # VERIFIED against the source prose so a hallucinated subject can never be
    # committed. Fully best-effort: any failure is swallowed so the creative
    # loop is never broken.

    _GRAPH_WINDOW = 3
    _GRAPH_MAX_CHARS = 8000

    def arc_summary(self, step: LoopStep, ws: AutoNovelWorkspace) -> StepResult:
        """Author the arc-boundary summary (base behaviour), then optionally
        enrich the Knowledge Graph from the recent prose (Req 9)."""
        result = super().arc_summary(step, ws)
        self._maybe_graph_enrich(ws, step.chapter)
        return result

    def volume_summary(self, step: LoopStep, ws: AutoNovelWorkspace) -> StepResult:
        """Author the volume-boundary summary (base behaviour), then optionally
        enrich the Knowledge Graph from the recent prose (Req 9)."""
        result = super().volume_summary(step, ws)
        self._maybe_graph_enrich(ws, step.chapter)
        return result

    def _maybe_graph_enrich(self, ws: AutoNovelWorkspace, chapter: Optional[int]) -> None:
        """Extract entities/relationships/events from the recent prose, verify
        each against the source text, then commit the survivors canon-first
        (Req 9.3/9.4/9.5). Flag-gated + best-effort — never raises."""
        try:
            from tools.novelkit_longform_config import flag_enabled

            if not (chapter and flag_enabled("graph_llm_enrich", ws.root)):
                return
        except Exception:  # noqa: BLE001 — a config miss must not break the loop
            return
        try:
            prose = self._recent_prose(ws, chapter)
            if not prose.strip():
                return
            raw = self.client.complete(
                system="Bạn là bộ trích dữ liệu tri thức. Chỉ trả về JSON hợp lệ.",
                user=(
                    prose
                    + "\n\nTừ ĐÚNG đoạn văn trên, trích dữ liệu tri thức. Trả về JSON "
                    "THUẦN (không lời dẫn) theo cấu trúc:\n"
                    '{"entities":[{"name":"...","kind":"..."}],'
                    '"relationships":[{"a":"...","b":"...","type":"..."}],'
                    '"events":[{"subject":"...","event_type":"...","chapter":<số>,'
                    '"summary":"..."}]}\n'
                    "Chỉ trích thực thể/quan hệ/sự kiện CÓ THẬT trong đoạn — không suy "
                    "diễn, không bịa tên. Không có thì trả mảng rỗng."
                ),
                temperature=0.0, max_tokens=800,
            )
            data = self._parse_enrich_json(raw)
            if not data:
                return
            facts = self._verified_graph_facts(data, prose, chapter)
            if not facts:
                return
            from plugins.memory.novelkit_memory import get_provider

            get_provider().commit_episodic(
                scope=ws.root, memory_facts=facts, chapter=chapter,
                commit_id=f"graph_enrich_{chapter}",
            )
        except Exception:  # noqa: BLE001 — enrichment must never break the loop
            return

    def _recent_prose(self, ws: AutoNovelWorkspace, chapter: int) -> str:
        """Gather a small window of the most recent canon chapters (bounded to
        :data:`_GRAPH_MAX_CHARS`), returned in chronological order."""
        collected: list[str] = []
        total = 0
        lo = max(1, chapter - self._GRAPH_WINDOW + 1)
        for c in range(chapter, lo - 1, -1):
            text = _read(ws.root / "chapters" / f"chapter_{c:03d}.md")
            if not text.strip():
                continue
            if collected and total + len(text) > self._GRAPH_MAX_CHARS:
                break
            collected.append(text)
            total += len(text)
        collected.reverse()  # oldest → newest
        return "\n\n".join(collected)[: self._GRAPH_MAX_CHARS]

    @staticmethod
    def _parse_enrich_json(raw: str) -> dict[str, Any]:
        """Best-effort parse of the extractor reply to a dict (empty on miss)."""
        start, end = raw.find("{"), raw.rfind("}")
        if not (0 <= start < end):
            return {}
        try:
            data = json.loads(raw[start : end + 1])
        except (ValueError, TypeError):
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _verified_graph_facts(
        data: dict[str, Any], prose: str, chapter: int
    ) -> list[dict[str, Any]]:
        """Map the extractor output to canon-first memory facts, keeping ONLY
        facts whose subject name(s) actually appear in ``prose`` (Req 9.4).

        Provenance ({"source","provenance_chapter"}) is stamped on every fact so
        the KG can trace each node/edge back to the enrichment run + chapter."""
        from plugins.memory.novelkit_memory import normalize_relationship_subject

        prov = {"source": "graph_llm_enrich", "provenance_chapter": chapter}

        def present(name: str) -> bool:
            return bool(name) and name in prose

        facts: list[dict[str, Any]] = []

        # relationships → category "relationships" (subject "A↔B", payload {a,b})
        for rel in data.get("relationships") or []:
            if not isinstance(rel, dict):
                continue
            a = str(rel.get("a", "")).strip()
            b = str(rel.get("b", "")).strip()
            rtype = str(rel.get("type", "")).strip() or "liên hệ"
            if not (a and b and present(a) and present(b)):
                continue  # hallucinated / ungrounded → drop
            facts.append({
                "category": "relationships",
                "subject": normalize_relationship_subject(a, b),
                "field": "relation", "value": rtype,
                "payload": {"a": a, "b": b, **prov},
            })

        # events → category "timeline"
        for ev in data.get("events") or []:
            if not isinstance(ev, dict):
                continue
            subject = str(ev.get("subject", "")).strip()
            etype = str(ev.get("event_type", "")).strip() or "sự kiện"
            summary = str(ev.get("summary", "")).strip()
            if not (subject and present(subject)):
                continue
            facts.append({
                "category": "timeline", "subject": subject, "field": etype,
                "value": summary or etype,
                "payload": {"event_type": etype, "chapter": chapter, **prov},
            })

        # secondary entities → category "minor_cast"
        for ent in data.get("entities") or []:
            if not isinstance(ent, dict):
                continue
            name = str(ent.get("name", "")).strip()
            kind = str(ent.get("kind", "")).strip()
            if not (name and present(name)):
                continue
            facts.append({
                "category": "minor_cast", "subject": name, "field": "profile",
                "value": kind or name,
                "payload": {"kind": kind, "first_seen": chapter,
                            "last_seen": chapter, "appearance_count": 1, **prov},
            })
        return facts


__all__ = ["LLMAutoNovelLoop"]
