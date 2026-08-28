"""NovelKit language guard tool — one genre-parameterized guard (merges D1).

Phase 3 of the migration (Task 7). This Custom Tool **merges the two legacy
language guards** — ``genre_language_guard.py`` (the generic per-genre banned
term lists) and ``xianxia_language_guard.py`` + ``config/xianxia_language_guard.json``
(the Xianxia-only guard) — into a single, genre-parameterized tool (finding D1).

Standardization rule applied (design.md §C.2): **genre is a parameter, not a
code branch.** There is no Xianxia-specific code path any more — Xianxia is just
a profile at ``config/language_guard/xianxia.json``. Adding a new genre guard is
a matter of dropping a ``config/language_guard/<genre>.json`` profile (and,
optionally, a canon ``vocabulary.txt`` whitelist), not writing code.

What is ported (semantics-preserving)
-------------------------------------
- **Per-genre banned terms** (``genre_language_guard.py``): each profile carries
  a ``banned_terms`` list (operational / modern / out-of-genre diction) with a
  suggested replacement, reason, and severity. (Requirement 12.1.)
- **Universal operational vocabulary** (``xianxia_language_guard`` operational
  regex): a genre-agnostic blocklist of pipeline/runtime words ("debug",
  "workflow", "metadata", "runtime", "pipeline", ...) that must never reach
  prose regardless of genre. (Requirement 12.1; Requirement 16.1.)
- **ASCII vs Unicode term matching** (ported from ``xianxia_term_pattern``):
  short upper-case acronyms (``MC``/``RAG``/``API``/``POV``) match
  case-sensitively with word boundaries so they do not fire inside ordinary
  words; everything else matches case-insensitively.

Hybrid handling (Requirements 12.2, 12.3, 17)
---------------------------------------------
``scan(text, genre, secondary_genre?)`` builds the allowed whitelist as the
**union of the primary and secondary genre whitelists**. A term that would be
banned by the primary profile but appears in the combined whitelist is *not*
flagged (the secondary genre legitimises it). Tokens outside *both* whitelists
are still flagged. The primary genre always wins on conflicts — the secondary
genre only **adds** whitelist entries, it never relaxes the universal
operational blocklist beyond its own whitelist nor contributes new bans.

Correctness property (design.md §"Correctness Properties" P6)
-------------------------------------------------------------
**P6 — Language guard soundness**: an operational / out-of-genre token that is
not in the whitelist (primary ∪ secondary) is always flagged; a token in the
whitelist is never flagged. **Validates: Requirements 12.1.**

The module is dependency-free (stdlib only) so it is verifiable in isolation;
``tools.registry`` is the one local import (the Hermes registry shim).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional

from tools import registry

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

#: Package root (parent of ``tools/``).
_PACKAGE_ROOT = Path(__file__).resolve().parents[1]

#: Where genre guard profiles live (Task 7.2 — xianxia is just a profile here).
LANGUAGE_GUARD_CONFIG_DIR = _PACKAGE_ROOT / "config" / "language_guard"

#: Canon genre vocabulary whitelists (one term per line, ``#`` comments).
CANON_SYSTEM_DIR = _PACKAGE_ROOT / "skills" / "novelkit-canon" / "canon" / "system"

#: Genre aliases → canonical slugs are normalised here so callers can pass
#: "Sci-fi", "sci fi", "scifi" etc. interchangeably.
_GENRE_SLUG_OVERRIDES = {
    "scifi": "scifi",
    "sci-fi": "scifi",
    "sci fi": "scifi",
    "science fiction": "scifi",
    "time travel": "time_travel",
    "timetravel": "time_travel",
    "meta genre": "meta_genre",
    "metagenre": "meta_genre",
}

#: Canon directory names per genre slug (for vocabulary.txt whitelist lookup).
_CANON_DIR_FOR_GENRE = {
    "xianxia": "Xianxia",
    "urban": "Urban",
    "romance": "Romance",
    "scifi": "Sci-fi",
    "time_travel": "Time Travel",
    "meta_genre": "Meta Genre",
    "apocalypse": "Apocalypse",
    "cthulhu": "Cthulhu",
    "dark_theme": "Dark Theme",
    "many_children": "Many Children",
    "rules_horror": "Rules Horror",
    "short_form": "Short Form",
    "streaming": "Streaming",
    "substitute": "Substitute",
    "war_espionage": "War Espionage",
    "esports": "eSports",
}


def normalize_genre(genre: str) -> str:
    """Normalise a genre label to a profile slug.

    Lower-cases, trims, collapses whitespace, and applies the alias overrides so
    "Sci-fi" / "sci fi" / "scifi" all resolve to ``scifi``. Unknown labels are
    returned in their normalised (underscored) form so a matching profile file
    can still be found by name.
    """
    raw = str(genre or "").strip().lower()
    collapsed = re.sub(r"\s+", " ", raw)
    if collapsed in _GENRE_SLUG_OVERRIDES:
        return _GENRE_SLUG_OVERRIDES[collapsed]
    return collapsed.replace(" ", "_")


def modern_register_allowed(metadata: Optional[dict[str, Any]]) -> bool:
    """Return whether canon explicitly places the story in a modern register."""
    if not isinstance(metadata, dict):
        return False
    explicit = metadata.get("allow_modern_register")
    if explicit is True or str(explicit).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return True
    era = " ".join(
        str(metadata.get(key) or "") for key in ("world_era", "setting_era")
    ).casefold()
    return any(
        marker in era
        for marker in (
            "hiện đại",
            "đương đại",
            "modern",
            "contemporary",
            "cyberpunk",
            "steampunk",
        )
    )


def workspace_guard_context(
    novel_path: "str | Path",
) -> tuple[str, Optional[str], bool]:
    """Resolve the guard profile and register exception from one novel's DNA."""
    root = Path(novel_path)
    metadata: dict[str, Any] = {}
    try:
        loaded = json.loads(
            (root / "PROJECT_DNA.fields.json").read_text(encoding="utf-8")
        )
        if isinstance(loaded, dict):
            metadata.update(loaded)
    except (OSError, ValueError, TypeError):
        pass

    try:
        dna_text = (root / "PROJECT_DNA.md").read_text(encoding="utf-8")
    except OSError:
        dna_text = ""
    for key in (
        "genre",
        "genre_primary",
        "genre_secondary",
        "world_era",
        "setting_era",
        "allow_modern_register",
    ):
        if key in metadata:
            continue
        match = re.search(rf"(?mi)^\s*{key}\s*:\s*([^\n#]+)", dna_text)
        if match:
            metadata[key] = match.group(1).strip().strip("\"'")

    primary = str(
        metadata.get("genre_primary") or metadata.get("genre") or ""
    ).strip()
    secondary = str(metadata.get("genre_secondary") or "").strip() or None
    return primary, secondary, modern_register_allowed(metadata)


# --------------------------------------------------------------------------- #
# Universal operational vocabulary (genre-agnostic blocklist, Requirement 12.1)
# --------------------------------------------------------------------------- #

#: Pipeline / runtime / metadata words that must never appear in prose, in any
#: genre. Ported from ``xianxia_language_guard.XIANXIA_OPERATIONAL_PROSE_TERM_RE``
#: but lifted out of the Xianxia-specific code into a shared blocklist so every
#: genre inherits it. Each entry carries a neutral reason; replacements are left
#: to the genre profile (which may localise them, as xianxia.json does).
_UNIVERSAL_OPERATIONAL_TERMS: tuple[str, ...] = (
    "runtime",
    "metadata",
    "schema",
    "debug",
    "pipeline",
    "workflow",
    "control plane",
    "dispatcher",
    "failover",
    "provider",
    "embedding",
    "reindex",
    "checkpoint",
    "rollback",
    "artifact",
    "task_key",
    "output_path",
    "output_paths",
    "review_outcome",
    "system prompt",
    "business prompt",
)


# --------------------------------------------------------------------------- #
# Data models
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class BannedTerm:
    """A term that should not appear in a genre's creative output."""

    term: str
    replacement: str = ""
    reason: str = ""
    severity: str = "warning"  # "warning" or "error"
    pattern: str = ""
    allow_in_modern_setting: bool = False


@dataclass(frozen=True)
class Violation:
    """A single language-guard hit (design.md §3 → ``scan -> Violation[]``)."""

    term: str
    genre: str
    replacement: str = ""
    reason: str = ""
    severity: str = "warning"
    count: int = 1
    source: str = "profile"  # "profile" | "operational"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GuardProfile:
    """A genre guard profile loaded from ``config/language_guard/<genre>.json``.

    A profile is a pure data object: ``banned_terms`` (what to flag) plus an
    optional ``whitelist`` (genre vocabulary that is always allowed, even if it
    collides with a banned term — this is what makes hybrid genres work).

    ``register_rules`` / ``style_overrides`` carry the *prose-contract* half of a
    genre's register: the prompt sentences that used to be hardcoded as
    ``if genre == "xianxia"`` (and ``and style_code == "VN"``) branches in both
    ``llm_loop`` and ``dna_form``. Encoding them here means adding a genre's
    register contract is a config edit, and the drafting prompt and the DNA
    generation prompt read the SAME text instead of two hand-synced copies.
    """

    genre: str
    banned_terms: tuple[BannedTerm, ...] = ()
    whitelist: frozenset[str] = frozenset()
    strict_classical_register: bool = False
    #: Register sentences that apply to every novel of this genre. ``default``
    #: is used normally; ``lexical_exception`` replaces it for a novel whose
    #: selected Author Style declares its own modern-diction licence.
    register_rules: tuple[str, ...] = ()
    register_rules_lexical_exception: tuple[str, ...] = ()
    #: Extra register sentences keyed by author-style code, e.g. ``{"VN": [...]}``.
    style_overrides: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def register_contract(
        self, *, style_code: str = "", lexical_exception: bool = False
    ) -> tuple[str, ...]:
        """The ordered register sentences for one novel of this genre.

        Genre rules first, then any rules specific to the selected author style,
        so a style-specific cadence rule always reads as a refinement of the
        genre floor rather than competing with it.
        """
        base = (
            self.register_rules_lexical_exception
            if lexical_exception and self.register_rules_lexical_exception
            else self.register_rules
        )
        extra = self.style_overrides.get((style_code or "").strip().upper(), ())
        return tuple(base) + tuple(extra)

    @classmethod
    def from_payload(cls, genre: str, payload: dict[str, Any]) -> "GuardProfile":
        banned: list[BannedTerm] = []
        for row in payload.get("banned_terms") or []:
            if not isinstance(row, dict):
                continue
            term = str(row.get("term") or "").strip()
            if not term:
                continue
            banned.append(
                BannedTerm(
                    term=term,
                    replacement=str(row.get("replacement") or "").strip(),
                    reason=str(row.get("reason") or "").strip(),
                    severity=str(row.get("severity") or "warning").strip() or "warning",
                    pattern=str(row.get("pattern") or "").strip(),
                    allow_in_modern_setting=bool(row.get("allow_in_modern_setting")),
                )
            )
        whitelist = {
            str(w).strip().casefold()
            for w in (payload.get("whitelist") or [])
            if str(w).strip()
        }
        def rules(value: Any) -> tuple[str, ...]:
            if isinstance(value, str):
                value = [value]
            return tuple(
                str(row).strip()
                for row in (value or [])
                if str(row).strip()
            )

        overrides: dict[str, tuple[str, ...]] = {}
        raw_overrides = payload.get("style_overrides")
        if isinstance(raw_overrides, dict):
            for code, value in raw_overrides.items():
                parsed = rules(value)
                if parsed:
                    overrides[str(code).strip().upper()] = parsed

        return cls(
            genre=genre,
            banned_terms=tuple(banned),
            whitelist=frozenset(whitelist),
            strict_classical_register=bool(
                payload.get("strict_classical_register")
            ),
            register_rules=rules(payload.get("register_rules")),
            register_rules_lexical_exception=rules(
                payload.get("register_rules_lexical_exception")
            ),
            style_overrides=overrides,
        )


# --------------------------------------------------------------------------- #
# Term matching (ported from xianxia_term_pattern)
# --------------------------------------------------------------------------- #


@lru_cache(maxsize=512)
def term_pattern(term: str) -> re.Pattern[str]:
    """Compile a match pattern for ``term``.

    ASCII short upper-case acronyms (e.g. ``MC``, ``RAG``, ``API``, ``POV``)
    match case-sensitively with non-word boundaries so they do not fire inside
    ordinary words. All other ASCII terms match case-insensitively with
    boundaries; Unicode (Vietnamese) terms match case-insensitively as
    substrings (boundary classes are unreliable for Vietnamese diacritics).
    """
    if term.isascii():
        flags = 0 if (term.isupper() and len(term) <= 4) else re.IGNORECASE
        return re.compile(
            rf"(?<![A-Za-z0-9_-]){re.escape(term)}(?![A-Za-z0-9_-])",
            flags=flags,
        )
    return re.compile(re.escape(term), flags=re.IGNORECASE)


def _count_occurrences(text: str, term: str, pattern: str = "") -> int:
    if pattern:
        pattern_hits = len(re.findall(pattern, text, flags=re.IGNORECASE))
        literal_hits = len(term_pattern(term).findall(text))
        return max(pattern_hits, literal_hits)
    return len(term_pattern(term).findall(text))


# --------------------------------------------------------------------------- #
# Profile loading
# --------------------------------------------------------------------------- #


@lru_cache(maxsize=64)
def _load_profile_payload(genre_slug: str) -> Optional[dict[str, Any]]:
    path = LANGUAGE_GUARD_CONFIG_DIR / f"{genre_slug}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=64)
def _load_canon_vocabulary(genre_slug: str) -> frozenset[str]:
    """Load the genre whitelist from the canon ``vocabulary.txt`` (if present).

    One term per line; ``#`` comments and blank lines are ignored. Missing files
    yield an empty set (forward-compatible: the canon vocab files may be filled
    in later).
    """
    dir_name = _CANON_DIR_FOR_GENRE.get(genre_slug)
    if not dir_name:
        return frozenset()
    path = CANON_SYSTEM_DIR / dir_name / "vocabulary.txt"
    if not path.exists():
        return frozenset()
    terms: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        terms.add(stripped.casefold())
    return frozenset(terms)


def load_profile(genre: str) -> GuardProfile:
    """Load (and cache) the guard profile for ``genre``.

    Combines the JSON profile's ``whitelist`` with the canon ``vocabulary.txt``
    whitelist for the same genre. A genre with no profile file yields an empty
    profile (only the universal operational blocklist applies).
    """
    slug = normalize_genre(genre)
    payload = _load_profile_payload(slug) or {}
    profile = GuardProfile.from_payload(slug, payload)
    canon_whitelist = _load_canon_vocabulary(slug)
    if canon_whitelist:
        # ``replace`` (not a hand-listed GuardProfile(...) rebuild) so a field
        # added to the profile is carried through automatically. The old rebuild
        # silently dropped any field it did not enumerate, which is exactly how a
        # new config key can appear to be ignored at runtime.
        profile = replace(profile, whitelist=profile.whitelist | canon_whitelist)
    return profile


# --------------------------------------------------------------------------- #
# Core scan (design.md §3 — scan(text, genre, secondary_genre?) -> Violation[])
# --------------------------------------------------------------------------- #


def _combined_whitelist(
    primary: GuardProfile, secondary: Optional[GuardProfile]
) -> frozenset[str]:
    """Whitelist = primary ∪ secondary (Requirement 12.2)."""
    if secondary is None:
        return primary.whitelist
    return primary.whitelist | secondary.whitelist


def scan(
    text: str,
    genre: str,
    secondary_genre: Optional[str] = None,
    *,
    allow_modern_register: bool = False,
) -> list[Violation]:
    """Scan ``text`` for operational / out-of-genre diction.

    Args:
        text: prose to check.
        genre: primary genre (selects the guard profile + whitelist).
        secondary_genre: optional secondary genre for hybrid works; its
            whitelist is unioned with the primary's (Requirement 12.2/17). Its
            bans do **not** apply — the primary genre wins (Requirement 12.3).

    Returns:
        A list of :class:`Violation` (one per distinct flagged term), in the
        order: universal-operational hits first, then profile-specific bans.

    Property P6: a banned/operational token absent from the combined whitelist
    is always flagged; a token present in the whitelist is never flagged.
    """
    text = str(text or "")
    if not text:
        return []

    primary = load_profile(genre)
    secondary = load_profile(secondary_genre) if secondary_genre else None
    whitelist = _combined_whitelist(primary, secondary)

    violations: list[Violation] = []
    seen: set[str] = set()

    def _emit(
        term: str,
        *,
        replacement: str,
        reason: str,
        severity: str,
        source: str,
        pattern: str = "",
    ) -> None:
        key = term.casefold()
        if key in seen:
            return
        # Whitelist wins (hybrid case): a term legitimised by either genre is
        # never flagged, even if it would otherwise be banned/operational.
        if key in whitelist:
            return
        count = _count_occurrences(text, term, pattern)
        if count <= 0:
            return
        seen.add(key)
        violations.append(
            Violation(
                term=term,
                genre=primary.genre,
                replacement=replacement,
                reason=reason,
                severity=severity,
                count=count,
                source=source,
            )
        )

    # 1. Universal operational vocabulary (genre-agnostic, Requirement 12.1).
    for term in _UNIVERSAL_OPERATIONAL_TERMS:
        _emit(
            term,
            replacement="",
            reason="Operational/runtime language must not appear in prose",
            severity="error",
            source="operational",
        )

    # 2. Genre-specific banned terms from the primary profile.
    for bt in primary.banned_terms:
        if bt.allow_in_modern_setting and allow_modern_register:
            continue
        _emit(
            bt.term,
            replacement=bt.replacement,
            reason=bt.reason or f"Out-of-genre term for {primary.genre}",
            severity=bt.severity,
            source="profile",
            pattern=bt.pattern,
        )

    return violations


def blocking_violations(
    violations: Iterable[Violation],
    genre: str,
    *,
    allow_modern_register: bool = False,
) -> list[Violation]:
    """Apply the profile's configured blocking policy to scan violations."""
    rows = list(violations)
    profile = load_profile(genre)
    if profile.strict_classical_register and not allow_modern_register:
        return rows
    return [violation for violation in rows if violation.severity == "error"]


def scan_result(
    text: str,
    genre: str,
    secondary_genre: Optional[str] = None,
    *,
    allow_modern_register: bool = False,
) -> dict[str, Any]:
    """Convenience wrapper returning a summary dict (severity + total hits)."""
    violations = scan(
        text,
        genre,
        secondary_genre,
        allow_modern_register=allow_modern_register,
    )
    total_hits = sum(v.count for v in violations)
    blocked = blocking_violations(
        violations,
        genre,
        allow_modern_register=allow_modern_register,
    )
    if blocked:
        severity = "error"
    elif violations:
        severity = "warning"
    else:
        severity = "ok"
    return {
        "genre": normalize_genre(genre),
        "secondary_genre": normalize_genre(secondary_genre) if secondary_genre else None,
        "violations": [v.to_dict() for v in violations],
        "total_hits": total_hits,
        "severity": severity,
        "passed": severity == "ok",
    }


# --------------------------------------------------------------------------- #
# Tool entrypoint + self-registration
# --------------------------------------------------------------------------- #

_LANGUAGE_GUARD_TOOL_SCHEMA: dict[str, Any] = {
    "name": "novelkit_language_guard",
    "description": (
        "Genre-parameterized language guard. Flags operational/modern/"
        "out-of-genre diction in prose; supports hybrid genres via a "
        "primary ∪ secondary whitelist."
    ),
    "input": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Prose to check"},
            "genre": {"type": "string", "description": "Primary genre slug"},
            "secondary_genre": {
                "type": ["string", "null"],
                "description": "Optional secondary genre (hybrid)",
            },
            "allow_modern_register": {
                "type": "boolean",
                "description": "Explicit canon exception for a modern setting",
            },
        },
        "required": ["text", "genre"],
    },
    "output": {
        "type": "object",
        "properties": {
            "genre": {"type": "string"},
            "secondary_genre": {"type": ["string", "null"]},
            "violations": {"type": "array", "items": {"type": "object"}},
            "total_hits": {"type": "integer"},
            "severity": {"type": "string", "enum": ["ok", "warning", "error"]},
            "passed": {"type": "boolean"},
        },
        "required": ["violations", "severity", "passed"],
    },
}


def language_guard_tool(
    text: str,
    genre: str,
    secondary_genre: Optional[str] = None,
    allow_modern_register: bool = False,
) -> dict[str, Any]:
    """Stateless tool entrypoint: ``(text, genre, secondary_genre?) -> summary``."""
    return scan_result(
        text,
        genre,
        secondary_genre,
        allow_modern_register=allow_modern_register,
    )


# Self-register at import time (Requirement 6.2 — self-registering tool).
registry.register(
    "novelkit_language_guard",
    language_guard_tool,
    schema=_LANGUAGE_GUARD_TOOL_SCHEMA,
    module=__name__,
)
