"""One place where a novel's canon routing is decided.

Why this module exists
----------------------
The same four questions — *which genre? which author style? which worldbuilding
guide? which squad?* — used to be answered independently in at least eight
places: ``dna_form.generation_prompt``, ``dna_form.enrich_prompt``,
``service.create_novel``, ``service.enrich_dna``, ``llm_loop._genre``,
``llm_loop._canon_pack_specs``, ``llm_loop._squad`` and the gate/language-guard
tools. Each site had its own source preference and its own fallback, so they
could disagree about the *same novel*:

* ``_canon_pack_specs`` read ``style_model`` from the PROJECT_DNA.md frontmatter
  via regex — over text capped at 16 000 chars — while ``_dna_tail_reminder``
  preferred the ``PROJECT_DNA.fields.json`` sidecar. A novel whose frontmatter
  was missing the key still *claimed* a locked style in the prompt tail while
  loading no author-style canon at all.
* ``_squad`` read ``PROJECT_DNA.meta.json``; the canon pack read the
  frontmatter. Two files, one decision.

Every historical "the selected style/worldbuilding was ignored" bug traces back
to that split. Resolving once, from an explicit source order, is what makes the
answer the same for every consumer.

Source order (highest first) is deliberate:

1. ``PROJECT_DNA.fields.json`` — the structured sidecar the create/enrich form
   writes. This is the user's actual selection.
2. ``PROJECT_DNA.meta.json`` — the routing pointer sidecar.
3. ``PROJECT_DNA.md`` frontmatter — human-editable, and truncated on read, so it
   is the last resort rather than the first.

This module performs no I/O beyond reading those three files and never guesses a
genre: an unresolved genre is returned as ``""`` so the caller decides whether
that is fatal (creation) or recoverable (drafting).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

#: Frontmatter is read with a cap because PROJECT_DNA.md can be very large and
#: the frontmatter is always at the top. Only the routing keys live here.
_FRONTMATTER_MAX_CHARS = 4000

#: Genre markers that mean "this is a blend, look at ``genre_primary``" rather
#: than naming a real genre with a canon pack of its own.
_ROUTING_ONLY_GENRES = frozenset({"", "hybrid", "none", "null", "unknown"})

#: Default squad when a novel names none. Matches the historical fallback in
#: ``llm_loop._squad`` so existing novels keep resolving identically.
DEFAULT_SQUAD = "sub_agents"


def _load_json(path: Path) -> dict[str, Any]:
    """Read a JSON object, or return ``{}`` for missing/corrupt/non-object."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return {str(k): v for k, v in data.items()} if isinstance(data, dict) else {}


def _frontmatter(root: Path) -> dict[str, str]:
    """Parse ``key: value`` pairs from the head of PROJECT_DNA.md."""
    try:
        raw = (root / "PROJECT_DNA.md").read_text(encoding="utf-8")[
            :_FRONTMATTER_MAX_CHARS
        ]
    except (OSError, UnicodeDecodeError):
        return {}
    out: dict[str, str] = {}
    for line in raw.splitlines():
        if line.strip() in ("---", ""):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)$", line)
        if m:
            out.setdefault(m.group(1), m.group(2).strip())
    return out


@dataclass(frozen=True)
class ResolvedCanon:
    """Every canon-routing decision for one novel, resolved exactly once.

    Consumers read these fields instead of re-deriving them, so the drafting
    loop, the DNA enrichment prompt, the review gate and the language guard can
    no longer disagree about which style or guide a novel selected.

    ``genre_primary`` is ``""`` when no genre could be resolved — never a
    guessed default. Callers on the creation path should treat that as an error;
    callers on the drafting path should log it.
    """

    genre_primary: str = ""
    genre_secondary: str = ""
    style_primary: str = ""
    style_secondary: str = ""
    worldbuilding_code: str = ""
    canon_pack: str = ""
    canon_pack_secondary: str = ""
    squad: str = DEFAULT_SQUAD
    squad_secondary: str = ""
    #: Which of the three files each routing value actually came from, for
    #: diagnostics: ``{"style_primary": "fields", ...}``.
    sources: dict[str, str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.sources is None:
            object.__setattr__(self, "sources", {})

    @property
    def resolved(self) -> bool:
        """True when a real (non-routing-marker) genre was found."""
        return bool(self.genre_primary)

    @property
    def effective_worldbuilding_code(self) -> str:
        """Guide code to load, falling back to the author-style code.

        The packs ship one worldbuilding guide per master, keyed by the same
        code, so a novel that picked a style but no explicit guide should read
        that master's guide rather than none at all.
        """
        return self.worldbuilding_code or self.style_primary

    def pack_selections(self) -> tuple[tuple[str, str, str], ...]:
        """``(pack, style_code, worldbuilding_code)`` per pack, primary first.

        Pairing each pack with *its own* codes here is what stops a hybrid novel
        from loading the secondary pack with the primary author's code — the
        secondary pack must follow ``style_secondary``/``style_blend``.
        """
        selections: list[tuple[str, str, str]] = []
        if self.canon_pack:
            selections.append(
                (
                    self.canon_pack,
                    self.style_primary,
                    self.effective_worldbuilding_code,
                )
            )
        if self.canon_pack_secondary:
            selections.append(
                (
                    self.canon_pack_secondary,
                    self.style_secondary,
                    self.style_secondary,
                )
            )
        return tuple(selections)


def _pack_name(raw: str) -> str:
    """Normalise a canon-pack reference to a bare pack directory name.

    The DNA form writes ``system/<Pack>`` while callers resolve against the
    ``canon/system`` root, so the prefix has to come off exactly once. Doing it
    here means no consumer can forget: passing ``system/Xianxia`` straight to
    ``_CANON_SYSTEM_ROOT / pack`` silently yields a nonexistent
    ``canon/system/system/Xianxia`` and the whole pack drops out with no error.
    """
    pack = str(raw or "").strip().strip("/")
    if not pack:
        return ""
    if pack.startswith("system/"):
        pack = pack.split("system/", 1)[1]
    return pack.strip("/")


def resolve_canon(root: Path) -> ResolvedCanon:
    """Resolve a novel's canon routing from its three on-disk sources.

    ``root`` is the novel workspace directory (the one holding PROJECT_DNA.md).
    Missing or corrupt sources are skipped rather than raising: a novel with
    only a frontmatter still resolves, which keeps legacy and hand-authored
    workspaces working.
    """
    root = Path(root)
    fields = _load_json(root / "PROJECT_DNA.fields.json")
    meta = _load_json(root / "PROJECT_DNA.meta.json")
    front = _frontmatter(root)
    layers = (("fields", fields), ("meta", meta), ("frontmatter", front))
    sources: dict[str, str] = {}

    def pick(name: str, *keys: str) -> str:
        """First non-empty value for ``keys`` across the source layers."""
        for source_name, layer in layers:
            for key in keys:
                value = str(layer.get(key) or "").strip()
                if value:
                    sources[name] = source_name
                    return value
        return ""

    genre_primary = pick("genre_primary", "genre_primary")
    if not genre_primary:
        # A bare ``genre`` is a routing marker: it reads "hybrid" for blends, so
        # trusting it first used to yield the pseudo-genre "hybrid", which has no
        # language-guard profile and silently disabled the lexical guard.
        bare = pick("genre_primary", "genre")
        genre_primary = "" if bare.lower() in _ROUTING_ONLY_GENRES else bare

    genre_secondary = pick("genre_secondary", "genre_secondary")
    if genre_secondary.lower() in _ROUTING_ONLY_GENRES:
        genre_secondary = ""

    style_primary = pick("style_primary", "style_model").upper()
    style_secondary = pick(
        "style_secondary", "style_secondary", "style_blend"
    ).upper()
    # A secondary style equal to the primary carries no information and would
    # make the secondary pack reload the primary author's profile.
    if style_secondary == style_primary:
        style_secondary = ""

    return ResolvedCanon(
        genre_primary=genre_primary,
        genre_secondary=genre_secondary,
        style_primary=style_primary,
        style_secondary=style_secondary,
        worldbuilding_code=pick(
            "worldbuilding_code", "worldbuilding_guide"
        ).upper(),
        canon_pack=_pack_name(pick("canon_pack", "canon_pack")),
        canon_pack_secondary=_pack_name(
            pick("canon_pack_secondary", "canon_pack_secondary")
        ),
        squad=pick("squad", "sub_agents_squad") or DEFAULT_SQUAD,
        squad_secondary=pick("squad_secondary", "sub_agents_squad_secondary"),
        sources=sources,
    )


__all__ = ["ResolvedCanon", "resolve_canon", "DEFAULT_SQUAD"]
