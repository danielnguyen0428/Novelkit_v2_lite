"""NovelKit DNA tool — PROJECT_DNA parse / genre resolve / enrich / bootstrap.

Phase 3 of the migration (Task 9.5). Consolidates the deterministic creative
logic of four legacy scripts into one self-registering Hermes Custom Tool:

- ``enrich_dna.py``            — PROJECT_DNA markdown parsing + enrichment plan.
- ``project_dna_metadata.py``  — PROJECT_DNA.meta.json sidecar helpers.
- ``generate_novel_from_prompt.py`` — title → slug.
- ``bootstrap_planning_docs.py``    — hydrate PLAN / GOAL_TRACKER / Memory docs.
- ``genre_aliases.json``       — Vietnamese natural-language genre alias map.

The legacy LLM enrichment (Gemini calls, provider/key-pool wiring) is **dropped**
— that belongs to Hermes provider resolution. What survives is the deterministic
craft: parsing PROJECT_DNA fields, resolving (composite) genre strings to
canonical slugs, computing *which* fields still need enrichment, and rendering
the initial planning documents from the DNA contract.

The module is self-contained (stdlib only) plus the local ``tools.registry``
shim and the ``config/genre_aliases.json`` data file.

Design references: design.md §"Components and Interfaces" #9
(``parse(dna_md) -> DNA``, ``resolve_genre(text) -> slug``, ``enrich(dna) -> dna'``,
``bootstrap_docs(dna) -> PLAN/GOAL_TRACKER``).
Requirements 11 (sync/bootstrap), 15 (author-style), 17 (multi/hybrid genre).
"""

from __future__ import annotations

import difflib
import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from tools import registry

logger = logging.getLogger(__name__)

#: Genre alias config path — ``novelkit-hermes/config/genre_aliases.json``.
GENRE_ALIASES_CONFIG_PATH: Path = (
    Path(__file__).resolve().parents[1] / "config" / "genre_aliases.json"
)

#: Composite operators joining two genre names. Longer phrases first.
COMPOSITE_OPERATORS: tuple[str, ...] = ("kết hợp", "với", "và", "+", "/", "、", "&")

#: Default ratio when authors specify a composite without an explicit weighting.
DEFAULT_COMPOSITE_RATIO = "70-30"

PROJECT_DNA_METADATA_FILENAME = "PROJECT_DNA.meta.json"


# --------------------------------------------------------------------------- #
# Genre resolution (ported from cp_genre.py, self-contained on genre_aliases)
# --------------------------------------------------------------------------- #


def slugify_genre(value: str) -> str:
    """Lowercase, ASCII-fold, single-spaced slug (ported from cp_genre.py)."""
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.lower()).strip()


@lru_cache(maxsize=4)
def _load_genre_alias_map(path_str: str) -> dict[str, str]:
    """Build ``slugify(alias) -> canonical_slug`` from genre_aliases.json.

    The JSON keys are canonical slugs (e.g. ``"xianxia"``, ``"time_travel"``);
    each canonical slug maps to itself plus every listed alias maps to it. A
    missing / malformed config yields an empty map (callers degrade to "unknown
    genre" rather than crashing).
    """
    path = Path(path_str)
    mapping: dict[str, str] = {}
    if not path.is_file():
        logger.warning("dna: genre alias config not found at %s", path)
        return mapping
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("dna: failed to load genre alias config %s: %s", path, exc)
        return mapping
    aliases_section = payload.get("aliases")
    if not isinstance(aliases_section, dict):
        return mapping
    for canonical_slug, alias_list in aliases_section.items():
        canonical = str(canonical_slug).strip()
        if not canonical:
            continue
        # Canonical slug resolves to itself (both raw and slugified forms).
        mapping.setdefault(slugify_genre(canonical), canonical)
        mapping.setdefault(canonical.replace("_", " ").replace("-", " "), canonical)
        if not isinstance(alias_list, list):
            continue
        for raw_alias in alias_list:
            normalized = slugify_genre(str(raw_alias))
            if normalized:
                mapping.setdefault(normalized, canonical)
    return mapping


def _genre_alias_map() -> dict[str, str]:
    return _load_genre_alias_map(str(GENRE_ALIASES_CONFIG_PATH))


def _clear_genre_cache() -> None:
    """Test helper — drop the cached genre alias map."""
    _load_genre_alias_map.cache_clear()


def resolve_genre_alias(name: str) -> Optional[str]:
    """Resolve any alias variant to its canonical genre slug, or ``None``."""
    if not name:
        return None
    slug = slugify_genre(name)
    if not slug:
        return None
    return _genre_alias_map().get(slug)


def suggest_genre_alternatives(name: str, limit: int = 3) -> list[str]:
    """Return up to ``limit`` canonical slugs that are close fuzzy matches."""
    if not name or limit <= 0:
        return []
    slug = slugify_genre(name)
    if not slug:
        return []
    alias_map = _genre_alias_map()
    candidates = difflib.get_close_matches(
        slug, list(alias_map.keys()), n=max(limit * 3, 6), cutoff=0.6
    )
    seen: set[str] = set()
    suggestions: list[str] = []
    for alias in candidates:
        canonical = alias_map[alias]
        if canonical not in seen:
            seen.add(canonical)
            suggestions.append(canonical)
            if len(suggestions) >= limit:
                break
    return suggestions


def _split_on_composite_operators(raw: str) -> list[str]:
    cleaned = (raw or "").strip()
    if not cleaned:
        return []
    pattern_parts: list[str] = []
    for op in COMPOSITE_OPERATORS:
        if any(ch.isalpha() for ch in op):
            pattern_parts.append(rf"\s+{re.escape(op)}\s+")
        else:
            pattern_parts.append(re.escape(op))
    splitter = re.compile("|".join(pattern_parts), flags=re.IGNORECASE)
    return [part.strip() for part in splitter.split(cleaned) if part.strip()]


_RATIO_RE = re.compile(r"\b(\d{1,3})\s*[-:/]\s*(\d{1,3})\b")


def _extract_ratio(raw: str) -> tuple[str, Optional[str]]:
    if not raw:
        return raw, None
    match = _RATIO_RE.search(raw)
    if not match:
        return raw, None
    ratio = f"{int(match.group(1))}-{int(match.group(2))}"
    remaining = (raw[: match.start()] + raw[match.end():]).strip(" ,;:")
    return remaining, ratio


@dataclass(frozen=True)
class GenreSpec:
    """Resolved genre configuration for a novel."""

    primary: str
    secondary: Optional[str] = None
    ratio: Optional[str] = None

    @property
    def is_hybrid(self) -> bool:
        return self.secondary is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary": self.primary,
            "secondary": self.secondary,
            "ratio": self.ratio,
            "is_hybrid": self.is_hybrid,
        }


def parse_composite_genre(raw: str) -> tuple[str, Optional[str], str]:
    """Parse a (possibly composite) genre string → (primary, secondary, ratio).

    Raises ``ValueError`` for >2 genres, ratios not summing to 100, or unknown
    genre tokens (with fuzzy "did you mean" suggestions).
    """
    if raw is None:
        raise ValueError("Genre string is empty")
    text, explicit_ratio = _extract_ratio(str(raw))
    parts = _split_on_composite_operators(text)
    if not parts:
        raise ValueError("Genre string is empty")
    if len(parts) > 2:
        raise ValueError(f"Maximum 2 genres allowed (got {len(parts)}: {parts})")

    resolved: list[str] = []
    for part in parts:
        canonical = resolve_genre_alias(part)
        if canonical is None:
            suggestions = suggest_genre_alternatives(part)
            hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
            raise ValueError(f"Unknown genre: {part!r}.{hint}")
        resolved.append(canonical)

    primary = resolved[0]
    secondary = resolved[1] if len(resolved) > 1 else None
    ratio = explicit_ratio or DEFAULT_COMPOSITE_RATIO
    primary_share, _, secondary_share = ratio.partition("-")
    try:
        total = int(primary_share) + int(secondary_share)
    except ValueError as exc:
        raise ValueError(f"Invalid ratio {ratio!r}: parts must be integers") from exc
    if total != 100:
        raise ValueError(f"Ratio must sum to 100 (got {ratio!r} = {total})")
    return primary, secondary, ratio


def resolve_genre(text: str) -> Optional[str]:
    """Resolve a genre string to its canonical *primary* slug, or ``None``.

    Tolerates composite strings (returns the primary). Never raises — unknown
    or empty input returns ``None`` so callers can branch.
    """
    if not text:
        return None
    try:
        primary, _secondary, _ratio = parse_composite_genre(text)
        return primary
    except ValueError:
        return resolve_genre_alias(text)


def resolve_genre_spec(text: str) -> GenreSpec:
    """Resolve a (possibly composite) genre string into a :class:`GenreSpec`."""
    primary, secondary, ratio = parse_composite_genre(text)
    return GenreSpec(primary=primary, secondary=secondary, ratio=ratio if secondary else None)


# --------------------------------------------------------------------------- #
# PROJECT_DNA.meta.json sidecar (ported from project_dna_metadata.py)
# --------------------------------------------------------------------------- #


def project_dna_metadata_path(project_dna_path: Path) -> Path:
    return Path(project_dna_path).with_name(PROJECT_DNA_METADATA_FILENAME)


def _stringify_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def read_project_dna_metadata(project_dna_path: Path) -> dict[str, str]:
    path = project_dna_metadata_path(project_dna_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    metadata: dict[str, str] = {}
    for key, value in payload.items():
        if not key or value is None or isinstance(value, (dict, list)):
            continue
        text = _stringify_scalar(value)
        if text:
            metadata[str(key)] = text
    return metadata


def write_project_dna_metadata(project_dna_path: Path, metadata: dict[str, Any]) -> None:
    path = project_dna_metadata_path(project_dna_path)
    path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


# --------------------------------------------------------------------------- #
# Title → slug (ported from generate_novel_from_prompt.py)
# --------------------------------------------------------------------------- #

_SLUG_DIACRITICS = {
    "à": "a", "á": "a", "ả": "a", "ã": "a", "ạ": "a",
    "ă": "a", "ằ": "a", "ắ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a",
    "â": "a", "ầ": "a", "ấ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
    "đ": "d",
    "è": "e", "é": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e",
    "ê": "e", "ề": "e", "ế": "e", "ể": "e", "ễ": "e", "ệ": "e",
    "ì": "i", "í": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
    "ò": "o", "ó": "o", "ỏ": "o", "õ": "o", "ọ": "o",
    "ô": "o", "ồ": "o", "ố": "o", "ổ": "o", "ỗ": "o", "ộ": "o",
    "ơ": "o", "ờ": "o", "ớ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
    "ù": "u", "ú": "u", "ủ": "u", "ũ": "u", "ụ": "u",
    "ư": "u", "ừ": "u", "ứ": "u", "ử": "u", "ữ": "u", "ự": "u",
    "ỳ": "y", "ý": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
}


def slugify_title(title: str) -> str:
    """Generate a slug from a Vietnamese title (ported from generate_novel)."""
    slug = (title or "").lower().strip()
    for src, dst in _SLUG_DIACRITICS.items():
        slug = slug.replace(src, dst)
    slug = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
    return slug[:80] if slug else "untitled_novel"


# --------------------------------------------------------------------------- #
# PROJECT_DNA parsing (ported from enrich_dna.py)
# --------------------------------------------------------------------------- #

PLACEHOLDER_PATTERNS = (
    re.compile(r"^\[.*\]$"),
    re.compile(r"^\[Chờ hệ thống tự sinh"),
    re.compile(r"^\[Điền "),
    re.compile(r"phải \[hành động\]"),
    re.compile(r"\[Truyện thật sự"),
)

_FRONTMATTER_BLOCK_RE = re.compile(
    r"(?:^|\n)---\s*\n(.*?)\n---\s*(?:\n|$)", flags=re.DOTALL
)


@dataclass
class ParsedDna:
    """Light parsed view of PROJECT_DNA.md."""

    frontmatter: dict[str, str] = field(default_factory=dict)
    title: str = ""
    logline: str = ""
    usp: str = ""
    target_audience: str = ""
    genre_primary: str = ""
    genre_secondary: str = ""
    tone: str = ""
    style: str = ""
    protagonist: str = ""
    antagonist: str = ""
    mc_traits: str = ""
    mc_motivation: str = ""
    supporting_cast: str = ""
    mc_archetype: str = ""
    hook_strategy: str = ""
    worldbuilding: str = ""
    enrichment_pending: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _is_placeholder(value: str) -> bool:
    stripped = (value or "").strip()
    if not stripped:
        return True
    return any(p.search(stripped) for p in PLACEHOLDER_PATTERNS)


def _field_value(text: str, label: str) -> str:
    """Extract ``- **Label:** value`` from a markdown section."""
    pattern = re.compile(
        rf"^-\s*\*\*{re.escape(label)}:\*\*\s*(.+)$", flags=re.MULTILINE
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _first_field_value(text: str, *labels: str) -> str:
    for label in labels:
        value = _field_value(text, label)
        if value:
            return value
    return ""


def _bullet_block_value(text: str, *labels: str) -> str:
    for label in labels:
        inline = _field_value(text, label)
        if inline:
            return inline
        pattern = re.compile(
            rf"^\s*-\s+\*\*{re.escape(label)}:\*\*\s*(?:\r?\n)([\s\S]*?)"
            r"(?=\n\s*-\s+\*\*|\n##\s+|\n###\s+|\Z)",
            flags=re.MULTILINE,
        )
        match = pattern.search(text)
        if not match:
            continue
        cleaned = "\n".join(
            line.replace("\t", "  ").strip()
            for line in match.group(1).splitlines()
            if line.strip()
        ).strip()
        if cleaned:
            return cleaned
    return ""


def parse_dna(text: str, metadata: Optional[dict[str, str]] = None) -> ParsedDna:
    """Parse PROJECT_DNA.md text (+ optional sidecar metadata) into a ParsedDna."""
    parsed = ParsedDna()
    fm_match = _FRONTMATTER_BLOCK_RE.search(text or "")
    if fm_match:
        for line in fm_match.group(1).splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                parsed.frontmatter[key.strip()] = value.strip()
    parsed.frontmatter.update(metadata or {})

    parsed.enrichment_pending = (
        parsed.frontmatter.get("enrichment_pending", "").lower() == "true"
    )
    parsed.genre_primary = parsed.frontmatter.get(
        "genre_primary", parsed.frontmatter.get("genre", "")
    )
    parsed.genre_secondary = parsed.frontmatter.get("genre_secondary", "")

    parsed.title = _first_field_value(text, "Tên tác phẩm")
    parsed.logline = _first_field_value(
        text, "Lời dẫn một câu", "Logline", "Logline (1 câu pitch)"
    )
    parsed.usp = _first_field_value(
        text, "Dấu riêng của truyện", "USP", "USP (Unique Selling Point)"
    )
    parsed.target_audience = _field_value(text, "Đối tượng độc giả")
    parsed.tone = _first_field_value(text, "Khí sắc", "Tone")
    parsed.style = _field_value(text, "Ghi chú phong cách")
    parsed.protagonist = _first_field_value(text, "Nhân vật chính", "Protagonist")
    parsed.antagonist = _first_field_value(
        text, "Đối trọng chính", "Phản diện cuối", "Antagonist"
    )
    parsed.mc_traits = _field_value(text, "Đặc điểm nổi bật")
    parsed.mc_motivation = _field_value(text, "Động cơ khởi đầu")
    parsed.supporting_cast = _bullet_block_value(
        text, "Dàn nhân vật phụ", "Dàn harem / đồng môn / tổ đội"
    )
    parsed.mc_archetype = _first_field_value(
        text, "Cốt cách nhân vật chính", "MC Archetype"
    )
    parsed.hook_strategy = _first_field_value(
        text, "Thế câu dẫn độc giả", "Hook Strategy"
    )
    parsed.worldbuilding = _first_field_value(
        text, "Tư duy thế giới", "Tư Duy Thế Giới (Worldbuilding)"
    )
    return parsed


# --------------------------------------------------------------------------- #
# Enrichment plan (deterministic — LLM fill belongs to Hermes provider)
# --------------------------------------------------------------------------- #

#: Representative PROJECT_DNA fields the enrich step must see filled.
#: ((markdown labels, preferred first), json_key). Ported from the
#: ``ENRICH_SCHEMA_KEYS`` table in enrich_dna.py (core subset).
ENRICH_SCHEMA_KEYS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("Phép thử lời dẫn", "Logline TEST"), "logline_test"),
    (("Cấm kỵ theo Đại Thần",), "author_taboo"),
    (("Tên thế giới / Bối cảnh",), "world_name"),
    (("Thời đại",), "world_era"),
    (("Tư duy thế giới", "Tư Duy Thế Giới (Worldbuilding)"), "world_mindset"),
    (("Bí mật lịch sử / Lời nguyền",), "world_secret"),
    (("Tên pháp hệ", "Tên hệ thống"), "system_name"),
    (("Các cấp bậc / Giai tầng chính",), "system_tiers"),
    (("Đặc điểm nổi bật",), "mc_traits"),
    (("Động cơ khởi đầu",), "mc_motivation"),
    (("Mong cầu bề mặt", "Want"), "mc_want"),
    (("Thiếu khuyết nội tâm", "Need"), "mc_need"),
    (("Niềm tin sai", "Lie"), "mc_lie"),
    (("Vết thương cũ", "Ghost"), "mc_ghost"),
    (("Giọng riêng", "Voice"), "mc_voice"),
    (("Phản diện cuối",), "villain_name"),
    (("Mong cầu phản diện", "Want phản diện"), "villain_want"),
    (("Thế câu dẫn độc giả", "Hook Strategy"), "hook_strategy"),
    (("Biến cố khởi phát", "Inciting Incident"), "inciting_incident"),
    (("Cú lật giữa truyện", "Midpoint Twist"), "midpoint_twist"),
    (("Đại cao trào", "Climax"), "climax"),
    (("Chủ đề cốt lõi",), "theme_core"),
    (("Core Wound", "Vết thương lõi"), "core_wound"),
    (("World Pressure", "Sức ép thế giới"), "world_pressure"),
    (("Reader Addiction Loop", "Vòng kéo độc giả"), "reader_addiction_loop"),
    (("Sổ phục bút", "Seed Master"), "seed_master"),
    (("Sổ tuyến truyện", "Thread Registry"), "thread_registry"),
)


def enrich(dna_text: str, metadata: Optional[dict[str, str]] = None) -> dict[str, Any]:
    """Compute a deterministic enrichment plan for a PROJECT_DNA document.

    Returns ``{dna, pending_fields, filled_fields, complete}``. ``pending_fields``
    lists the schema keys whose markdown field is missing or still a placeholder
    — i.e. the fields a downstream LLM (via Hermes provider resolution) must
    generate. ``complete`` is True when nothing remains pending.
    """
    parsed = parse_dna(dna_text, metadata)
    pending: list[dict[str, str]] = []
    filled: list[str] = []
    for labels, schema_key in ENRICH_SCHEMA_KEYS:
        value = _first_field_value(dna_text or "", *labels)
        if _is_placeholder(value):
            pending.append({"key": schema_key, "label": labels[0]})
        else:
            filled.append(schema_key)
    return {
        "dna": parsed.to_dict(),
        "pending_fields": pending,
        "filled_fields": filled,
        "complete": not pending and not parsed.enrichment_pending,
    }


# --------------------------------------------------------------------------- #
# Bootstrap planning docs (ported from bootstrap_planning_docs.py)
# --------------------------------------------------------------------------- #

_XIANXIA_PLANNING_REPLACEMENTS = (
    ("Seed", "Hạt giống"),
    ("Quest", "Mạch cầu đạo"),
    ("Fire", "Mạch đối đầu"),
    ("Constellation", "Mạch nhân duyên"),
    ("Thread", "Tuyến"),
    ("thread", "tuyến"),
    ("plant", "gieo"),
    ("harvest", "trả"),
    ("payoff", "quả trả"),
    ("advance", "đẩy"),
    ("Arc", "Đại hồi"),
    ("arc", "đại hồi"),
    ("MC", "nhân vật chính"),
)

_CULTIVATION_SPEED_LABELS = {
    "fast": "Nhanh — 5-15 tiểu cảnh, hoặc gần 1 đại cảnh mỗi 1-2 đại hồi",
    "slow": "Chậm — 1 đại cảnh hoặc 2-4 tiểu cảnh trong một đại hồi",
    "ultra_slow": "Siêu chậm — 0.5 đại cảnh, hoặc 1-3 tiểu cảnh trong một đại hồi",
}


def _normalize_cultivation_speed(value: str) -> str:
    cleaned = str(value or "").strip().strip("'\"")
    lookup = cleaned.casefold().replace("_", " ").replace("-", " ")
    if "ultra slow" in lookup or "siêu chậm" in lookup or "sieu cham" in lookup or "0.5 đại cảnh" in lookup:
        return "ultra_slow"
    if lookup == "fast" or "nhanh" in lookup or "5-15" in lookup:
        return "fast"
    if lookup == "slow" or "chậm" in lookup or "cham" in lookup or "2-4" in lookup:
        return "slow"
    return ""


def _cultivation_speed_label(value: str) -> str:
    return _CULTIVATION_SPEED_LABELS.get(
        _normalize_cultivation_speed(value) or "slow",
        _CULTIVATION_SPEED_LABELS["slow"],
    )


def _bootstrap_field_value(text: str, *labels: str) -> str:
    for label in labels:
        pattern = re.compile(
            rf"^-\s*\*\*{re.escape(label)}:\*\*\s*([\s\S]*?)(?=\n-\s*\*\*|\n## |\Z)",
            flags=re.MULTILINE,
        )
        match = pattern.search(text)
        if match:
            value = re.sub(r"\s*\n\s*", " ", match.group(1)).strip()
            if value:
                return value
    return ""


def _title_from_heading(text: str) -> str:
    match = re.search(r"^# .+?—\s*(.+?)\s*$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def _int_value(raw: str, default: int) -> int:
    match = re.search(r"\d+", str(raw or ""))
    return int(match.group(0)) if match else default


def _clean(value: str, *, xianxia: bool, fallback: str) -> str:
    text = (value or "").strip() or fallback
    text = re.sub(r"\s+", " ", text).strip()
    if xianxia:
        for source, target in _XIANXIA_PLANNING_REPLACEMENTS:
            text = re.sub(
                rf"(?<![A-Za-z0-9_-]){re.escape(source)}(?![A-Za-z0-9_-])",
                target,
                text,
                flags=re.IGNORECASE if source.isascii() else 0,
            )
        text = re.sub(r"\s+", " ", text).strip()
    return text or fallback


def _read_bootstrap_frontmatter(dna_path: Path, text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    match = _FRONTMATTER_BLOCK_RE.search(text)
    if match:
        for line in match.group(1).splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or ":" not in stripped:
                continue
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and value:
                metadata[key] = value
    metadata.update(read_project_dna_metadata(dna_path))
    return metadata


def _extract_dna_fields(project_path: Path) -> dict[str, Any]:
    dna_path = project_path / "PROJECT_DNA.md"
    text = dna_path.read_text(encoding="utf-8")
    metadata = _read_bootstrap_frontmatter(dna_path, text)
    genre_text = " ".join(
        str(metadata.get(key, ""))
        for key in ("genre", "genre_primary", "genre_secondary")
    ).casefold()
    xianxia = "xianxia" in genre_text or "tiên hiệp" in text.casefold()

    title = (
        _bootstrap_field_value(text, "Tên tác phẩm")
        or _title_from_heading(text)
        or project_path.name
    )
    target_chapters = _int_value(
        metadata.get("target_chapters")
        or _bootstrap_field_value(text, "Ước tính tổng số chương"),
        120,
    )
    target_words = _int_value(
        metadata.get("target_words_per_chapter")
        or _bootstrap_field_value(text, "Số từ mỗi chương", "Words/chapter"),
        2500,
    )

    def value(*labels: str, fallback: str) -> str:
        return _clean(_bootstrap_field_value(text, *labels), xianxia=xianxia, fallback=fallback)

    return {
        "title": _clean(title, xianxia=xianxia, fallback=project_path.name),
        "xianxia": xianxia,
        "target_chapters": target_chapters,
        "target_words": target_words,
        "logline": value("Lời dẫn một câu", "Logline", "Logline (1 câu pitch)", fallback="Hạt giống truyện đã khóa trong khế ước gốc."),
        "world": value("Tên thế giới / Bối cảnh", fallback="thiên địa chính của truyện"),
        "world_rule": value("Tư duy thế giới", "Tư Duy Thế Giới (Worldbuilding)", fallback="Thiên địa ép nhân vật trả giá qua từng lựa chọn."),
        "system_name": value("Tên pháp hệ", "Tên hệ thống", fallback="pháp hệ cốt lõi"),
        "tiers": value("Các cấp bậc / Giai tầng chính", fallback="mốc tiến cảnh chưa chia nhỏ"),
        "cultivation_speed": value("Tốc độ tu luyện", "Cultivation speed", fallback=_cultivation_speed_label(metadata.get("cultivation_speed", ""))),
        "cultivation_age_benchmarks": value("Mốc tuổi tu luyện", "Cultivation age benchmarks", fallback=metadata.get("cultivation_age_benchmarks", "51 tuổi -> Trúc Cơ hậu kỳ nếu áp dụng Nhĩ Căn/NC")),
        "resources": value("Tài nguyên cốt lõi", fallback="tài nguyên tu hành chính"),
        "bottleneck": value("Nút thắt chính", "Bottleneck chính", fallback="nút thắt đạo tâm và sinh tồn"),
        "protagonist": value("Nhân vật chính", "Protagonist", fallback="nhân vật chính"),
        "antagonist": value("Phản diện cuối", "Đối trọng chính", "Antagonist", fallback="đối trọng chính"),
        "mc_want": value("Mong cầu bề mặt", "Want", fallback="sống sót và bước tiếp trên đạo lộ"),
        "mc_need": value("Thiếu khuyết nội tâm", "Need", fallback="dám chọn mình là ai và chịu giá cho lựa chọn ấy"),
        "seeds": value("Sổ phục bút", "Seed Master", fallback="hạt giống chính sẽ gieo từ chương đầu."),
        "threads": value("Sổ tuyến truyện", "Thread Registry", fallback="mạch sống còn, mạch đối đầu và mạch nhân duyên."),
        "boss_ladder": value("Bậc thang trùm đại hồi", "Arc Boss Ladder", fallback="đại hồi đầu có kẻ cản đường trực tiếp."),
    }


def _plan_doc(fields: dict[str, Any]) -> str:
    return f"""# Đường Dài Tác Phẩm — {fields["title"]}

> Sổ này giữ mạch sáng tác đường dài. Trước khi lập cương hoặc viết chương, Khí Linh phải đối chiếu các neo dưới đây.

## Khái Quát

| Mục | Giá trị |
|---|---|
| Tác phẩm | {fields["title"]} |
| Số chương dự định | {fields["target_chapters"]} |
| Số chữ mỗi chương | {fields["target_words"]} |
| Thiên địa | {fields["world"]} |
| Nhân vật chính | {fields["protagonist"]} |
| Đối trọng chính | {fields["antagonist"]} |
| Pháp hệ | {fields["system_name"]} |
| Tốc độ tu luyện | {fields["cultivation_speed"]} |
| Mốc tuổi tu luyện | {fields["cultivation_age_benchmarks"]} |

## Sổ Chương

| Chương | Tình hình | Trọng tâm đạo pháp | Quả cần trả |
|---|---|---|---|
| Chương 1 | Chờ cương sạch và chính văn sạch | {fields["system_name"]}: {fields["tiers"]} | {fields["logline"]} |

## Mạch Tu Hành

Tốc độ tu luyện đã khóa: {fields["cultivation_speed"]}. Mốc tuổi tu luyện: {fields["cultivation_age_benchmarks"]}. Mộng Yểm phải chia bình cảnh, cơ duyên, bí cảnh và đột phá theo đại hồi; Khí Linh viết chính văn không tự vượt nhịp này.

| Nhân vật | Nền hiện tại | Mốc kế tiếp | Tài nguyên | Nút thắt |
|---|---|---|---|---|
| {fields["protagonist"]} | Bước đầu chạm đạo, chưa khóa chiến quả chương đầu | Mở dấu hiệu đầu của {fields["system_name"]} | {fields["resources"]} | {fields["bottleneck"]} |

## Luật Thiên Địa

| Vùng chạm tới | Luật vận hành | Người giữ quyền | Cái giá |
|---|---|---|---|
| {fields["world"]} | {fields["world_rule"]} | Tông môn, thế lực hoặc người cầm luật trong đại hồi đầu | Mỗi bước tiến phải để lại hậu quả rõ trong người, vật hoặc quan hệ |
"""


def _goal_doc(fields: dict[str, Any]) -> str:
    return f"""# Sổ Theo Dõi Đại Nguyện — {fields["title"]}

> Mỗi cương chương phải giữ ít nhất một mạch truyện tiến lên, một hạt giống được gieo hoặc trả, và một biến đổi thật của nhân vật.

## Đại Nguyện Toàn Truyện

| Mã | Điều phải hoàn thành | Loại | Mốc dự kiến | Ghi chú |
|---|---|---|---|---|
| DG-001 | {fields["protagonist"]} từ chỗ {fields["mc_want"]} đi tới lựa chọn thật: {fields["mc_need"]} | Nhân vật | Trước hồi cuối | Không được chỉ kể bằng lời bình |
| DG-002 | Bóc dần bí mật của {fields["world"]} qua {fields["system_name"]} | Thiên địa | Trải đều các đại hồi | Luật phải hiện qua hành động và cái giá |
| DG-003 | Đẩy đối đầu với {fields["antagonist"]} thành xung đột đạo tâm | Đối trọng | Tăng dần từ đại hồi đầu | Phản diện có lý lẽ riêng |

## Mốc Tu Hành

Tốc độ tu luyện: {fields["cultivation_speed"]}. Mốc tuổi tu luyện: {fields["cultivation_age_benchmarks"]}. Mỗi mốc mới phải có tích lũy, chướng ngại, quá trình và hậu quả trước khi ghi nhận.

| Nhân vật | Nền hiện tại | Mốc kế tiếp | Cần tích lũy | Chỗ nghẽn |
|---|---|---|---|---|
| {fields["protagonist"]} | Chưa có chiến quả sạch sau chương đầu | Dấu hiệu đầu của {fields["system_name"]} | {fields["resources"]} | {fields["bottleneck"]} |

## Hạt Giống Và Mạch Truyện

| Loại | Nội dung | Lúc gieo | Lúc trả |
|---|---|---|---|
| Hạt giống | {fields["seeds"]} | Từ chương đầu và đại hồi một | Trả nhỏ từng cụm, trả lớn đúng đại hồi |
| Mạch truyện | {fields["threads"]} | Luôn có dấu trong cương chương | Không để mạch chính im quá lâu |
| Bậc cản đường | {fields["boss_ladder"]} | Gợi bóng từ đại hồi một | Mỗi bậc phải ép nhân vật trả giá mới |
"""


def _memory_doc(fields: dict[str, Any]) -> str:
    return f"""# Bộ Nhớ Dài Hạn — {fields["title"]}

> Đây là bản neo ban đầu trước khi chương sạch đầu tiên được thông qua. Sau mỗi chương qua kiểm, Lãng Khách cập nhật bằng sự kiện đã xảy ra thật.

## Tình Hình Hiện Tại

- Chương mới nhất đã qua kiểm: chưa có.
- Đại hồi đang mở: đại hồi một.
- Nhân vật chính: {fields["protagonist"]}.
- Thiên địa đang đặt chân: {fields["world"]}.
- Tình thế mở màn: {fields["logline"]}

## Neo Canon

- Pháp hệ: {fields["system_name"]}.
- Bậc tiến cảnh: {fields["tiers"]}.
- Tốc độ tu luyện: {fields["cultivation_speed"]}.
- Tài nguyên cốt lõi: {fields["resources"]}.
- Nút nghẽn: {fields["bottleneck"]}.
- Đối trọng chính: {fields["antagonist"]}.
- Luật thiên địa: {fields["world_rule"]}.

## Mạch Cần Giữ

- Hạt giống: {fields["seeds"]}
- Tuyến truyện: {fields["threads"]}
- Bậc cản đường: {fields["boss_ladder"]}

## Điều Chưa Được Ghi Nhận

- Chưa có chương chính văn nào qua kiểm, nên mọi biến cố sau đây phải lấy từ artifact mới được thông qua chứ không lấy từ file chờ hoặc file báo xung đột.
"""


def _should_write(path: Path, *, force: bool) -> bool:
    if force or not path.exists():
        return True
    try:
        return not path.read_text(encoding="utf-8").strip()
    except OSError:
        return True


def bootstrap_docs(project_path: str | Path, *, force: bool = False) -> dict[str, Any]:
    """Hydrate PLAN.md / GOAL_TRACKER.md / memory/Memory.md from PROJECT_DNA.md.

    Existing non-empty docs are left untouched unless ``force=True``.
    """
    project = Path(project_path)
    dna_path = project / "PROJECT_DNA.md"
    if not dna_path.exists():
        raise FileNotFoundError(f"Missing PROJECT_DNA.md at {dna_path}")

    fields = _extract_dna_fields(project)
    docs = {
        "PLAN.md": _plan_doc(fields),
        "GOAL_TRACKER.md": _goal_doc(fields),
        "memory/Memory.md": _memory_doc(fields),
    }
    updated: list[str] = []
    skipped: list[str] = []
    for rel, content in docs.items():
        target = project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if _should_write(target, force=force):
            target.write_text(content.rstrip() + "\n", encoding="utf-8")
            updated.append(rel)
        else:
            skipped.append(rel)
    return {
        "ok": True,
        "project_path": str(project),
        "updated": updated,
        "skipped": skipped,
    }


# --------------------------------------------------------------------------- #
# Tool entrypoint + self-registration (Requirement 6.2)
# --------------------------------------------------------------------------- #

_DNA_TOOL_SCHEMA = {
    "name": "novelkit_dna",
    "description": (
        "PROJECT_DNA tool: parse DNA markdown, resolve (composite) genre "
        "strings to canonical slugs, compute the enrichment plan (pending "
        "fields), and bootstrap PLAN/GOAL_TRACKER/Memory planning docs."
    ),
    "input": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["parse", "resolve_genre", "enrich", "bootstrap_docs"],
            },
            "dna_text": {"type": "string"},
            "genre_text": {"type": "string"},
            "metadata": {"type": "object"},
            "project_path": {"type": "string"},
            "force": {"type": "boolean"},
        },
        "required": ["action"],
    },
    "output": {"type": "object"},
}


def dna_tool(
    action: str,
    *,
    dna_text: Optional[str] = None,
    genre_text: Optional[str] = None,
    metadata: Optional[dict[str, str]] = None,
    project_path: Optional[str] = None,
    force: bool = False,
) -> dict[str, Any]:
    """Stateless tool entrypoint dispatching on ``action``."""
    if action == "parse":
        if dna_text is None:
            raise ValueError("parse requires dna_text")
        return parse_dna(dna_text, metadata).to_dict()
    if action == "resolve_genre":
        if genre_text is None:
            raise ValueError("resolve_genre requires genre_text")
        spec = resolve_genre_spec(genre_text)
        return spec.to_dict()
    if action == "enrich":
        if dna_text is None:
            raise ValueError("enrich requires dna_text")
        return enrich(dna_text, metadata)
    if action == "bootstrap_docs":
        if project_path is None:
            raise ValueError("bootstrap_docs requires project_path")
        return bootstrap_docs(project_path, force=force)
    raise ValueError(f"unknown action {action!r}")


registry.register(
    "novelkit_dna",
    dna_tool,
    schema=_DNA_TOOL_SCHEMA,
    module=__name__,
)


__all__ = [
    "GenreSpec",
    "ParsedDna",
    "slugify_genre",
    "slugify_title",
    "resolve_genre",
    "resolve_genre_alias",
    "resolve_genre_spec",
    "suggest_genre_alternatives",
    "parse_composite_genre",
    "project_dna_metadata_path",
    "read_project_dna_metadata",
    "write_project_dna_metadata",
    "parse_dna",
    "enrich",
    "bootstrap_docs",
    "dna_tool",
]
