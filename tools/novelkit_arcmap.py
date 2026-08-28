"""Flexible, narrative-driven arc boundaries (Req 4; Property P16).

The legacy pipeline cut an "arc" mechanically every ``ARC_SIZE=50`` chapters,
which does not match the *creative* arc rhythm (a Xianxia arc runs ~8–25
chapters depending on type). This module introduces an **arc map** — a canon
artifact (``outlines/arc_map.json``) that records the real arc boundaries the
Plot Weaver designs — and the lookups the pipeline uses instead of arithmetic.

Invariants (P16):
- Arcs with concrete bounds **partition** the chapter range with no gap/overlap.
- Every arc declares ``estimated_chapters >= MIN_ARC_LEN``.
- When no arc map is present, callers fall back to the exact legacy arithmetic
  (``(chapter-1)//arc_size + 1``) so existing novels behave identically.

Stdlib-only; verifiable in isolation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Optional

#: Minimum length of an arc (a rhythm cycle cannot resolve in < 8 chapters).
MIN_ARC_LEN = 8

#: Universal arc-type vocabulary (mapped from the Xianxia arc-template set).
ARC_TYPES: tuple[str, ...] = (
    "growth_breakthrough",
    "tournament",
    "secret_realm",
    "faction_conflict",
    "tribulation_war",
    "daily_transition",
)

#: Arc lifecycle statuses.
ARC_STATUSES: tuple[str, ...] = ("skeleton", "detailed", "done")


class ArcMapError(ValueError):
    """Raised when an arc map violates a structural invariant (P16)."""


@dataclass(frozen=True)
class ArcSpec:
    """One arc. ``start_chapter``/``end_chapter`` are ``None`` while the arc is
    still a *skeleton* (goal + estimate only, not yet placed on the timeline)."""

    arc_id: str
    arc_type: str
    estimated_chapters: int
    start_chapter: Optional[int] = None
    end_chapter: Optional[int] = None
    goal: str = ""
    status: str = "skeleton"
    volume_id: Optional[str] = None

    @property
    def is_placed(self) -> bool:
        return self.start_chapter is not None and self.end_chapter is not None

    def contains(self, chapter: int) -> bool:
        return (
            self.is_placed
            and self.start_chapter <= chapter <= self.end_chapter  # type: ignore[operator]
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "arc_id": self.arc_id,
            "volume_id": self.volume_id,
            "start_chapter": self.start_chapter,
            "end_chapter": self.end_chapter,
            "arc_type": self.arc_type,
            "estimated_chapters": self.estimated_chapters,
            "goal": self.goal,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArcSpec":
        return cls(
            arc_id=str(data["arc_id"]),
            arc_type=str(data.get("arc_type") or "daily_transition"),
            estimated_chapters=int(data.get("estimated_chapters") or 0),
            start_chapter=data.get("start_chapter"),
            end_chapter=data.get("end_chapter"),
            goal=str(data.get("goal") or ""),
            status=str(data.get("status") or "skeleton"),
            volume_id=data.get("volume_id"),
        )


@dataclass
class ArcMap:
    arcs: list[ArcSpec] = field(default_factory=list)

    # ---- (de)serialisation ------------------------------------------------ #
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArcMap":
        return cls(arcs=[ArcSpec.from_dict(a) for a in data.get("arcs") or []])

    def to_dict(self) -> dict[str, Any]:
        payload = {"schema": 1, "arcs": [a.to_dict() for a in self.arcs]}
        payload["arc_map_digest"] = self.digest()
        return payload

    def digest(self) -> str:
        canonical = json.dumps(
            [a.to_dict() for a in self.arcs],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(canonical).hexdigest()}"

    # ---- invariants (P16) ------------------------------------------------- #
    def validate(self) -> None:
        for arc in self.arcs:
            if arc.estimated_chapters < MIN_ARC_LEN:
                raise ArcMapError(
                    f"arc {arc.arc_id!r} estimated_chapters "
                    f"{arc.estimated_chapters} < MIN_ARC_LEN {MIN_ARC_LEN}"
                )
            if arc.arc_type not in ARC_TYPES:
                raise ArcMapError(f"arc {arc.arc_id!r} unknown arc_type {arc.arc_type!r}")
            if arc.status not in ARC_STATUSES:
                raise ArcMapError(f"arc {arc.arc_id!r} unknown status {arc.status!r}")
        placed = sorted(
            (a for a in self.arcs if a.is_placed),
            key=lambda a: a.start_chapter,  # type: ignore[arg-type]
        )
        expected_start = 1
        for arc in placed:
            if arc.start_chapter != expected_start:  # type: ignore[operator]
                raise ArcMapError(
                    f"arc {arc.arc_id!r} starts at {arc.start_chapter}, "
                    f"expected {expected_start} (gap/overlap)"
                )
            if arc.end_chapter < arc.start_chapter:  # type: ignore[operator]
                raise ArcMapError(f"arc {arc.arc_id!r} end < start")
            expected_start = arc.end_chapter + 1  # type: ignore[operator]

    # ---- lookups ---------------------------------------------------------- #
    def arc_for(self, chapter: int) -> Optional[ArcSpec]:
        for arc in self.arcs:
            if arc.contains(chapter):
                return arc
        return None

    def arc_index_for(self, chapter: int) -> int:
        """1-based index (over ALL arcs, in declared order) of the arc that
        contains ``chapter``. Raises ``KeyError`` when no placed arc covers it."""
        for idx, arc in enumerate(self.arcs, start=1):
            if arc.contains(chapter):
                return idx
        raise KeyError(f"no placed arc contains chapter {chapter}")

    def is_last_chapter_of_arc(self, chapter: int) -> bool:
        arc = self.arc_for(chapter)
        return arc is not None and arc.end_chapter == chapter

    def upsert(self, spec: ArcSpec) -> bool:
        """Insert or replace ``spec`` by ``arc_id``. Returns True when changed."""
        for i, arc in enumerate(self.arcs):
            if arc.arc_id == spec.arc_id:
                if arc == spec:
                    return False
                self.arcs[i] = spec
                return True
        self.arcs.append(spec)
        return True


__all__ = [
    "ArcMap",
    "ArcSpec",
    "ArcMapError",
    "MIN_ARC_LEN",
    "ARC_TYPES",
    "ARC_STATUSES",
]
