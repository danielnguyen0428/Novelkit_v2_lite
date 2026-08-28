"""NovelKit compass tool — Story Compass, layered outline, arc map (Req 1, 2, 4).

The Story Compass is the long-form "where is this story going" artifact that the
legacy pipeline lacked (it only ever wrote a one-shot ``master_outline.md``).
This tool owns three canon artifacts and the deterministic scaffolding around
them; the *creative content* is authored by the Plot Weaver agent, this tool
just persists it idempotently and answers boundary/expansion questions.

Artifacts (all under the novel workspace):
- ``outlines/compass.md``         — canon, human-readable + embedded json block.
- ``outlines/layered_outline.json`` — current volume (detailed) + next (skeleton).
- ``outlines/arc_map.json``       — narrative arc boundaries (see novelkit_arcmap).

All writes are **idempotent / content-addressed** (Property P14): re-writing the
same content returns ``changed=False`` and leaves the file byte-identical, so a
repeated expansion never churns canon (mirrors sync P11).

Stdlib-only. Self-registers as ``novelkit_compass``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Optional

from tools import registry
from tools.novelkit_arcmap import ArcMap, ArcSpec, MIN_ARC_LEN

_LOG = logging.getLogger("novelkit.compass")

COMPASS_REL = "outlines/compass.md"
LAYERED_OUTLINE_REL = "outlines/layered_outline.json"
ARC_MAP_REL = "outlines/arc_map.json"

_COMPASS_BLOCK_RE = re.compile(r"```json compass-data\n(.*?)\n```", re.DOTALL)


# --------------------------------------------------------------------------- #
# Atomic write (temp + fsync + replace) — local to avoid import cycles
# --------------------------------------------------------------------------- #


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    tmp.replace(path)


def _write_if_changed(path: Path, text: str) -> bool:
    """Write ``text`` only when it differs from the current file. Returns
    True when the file content changed (idempotency primitive, P14)."""
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    _atomic_write_text(path, text)
    return True


# --------------------------------------------------------------------------- #
# Compass
# --------------------------------------------------------------------------- #


def _compass_data(
    *,
    ending_direction: str,
    active_long_threads: list[dict[str, Any]],
    scale_estimate: dict[str, Any],
    current_volume_id: Optional[str],
    current_arc_id: Optional[str],
) -> dict[str, Any]:
    return {
        "ending_direction": ending_direction,
        "active_long_threads": active_long_threads,
        "scale_estimate": scale_estimate,
        "current_volume_id": current_volume_id,
        "current_arc_id": current_arc_id,
    }


def _digest(data: dict[str, Any]) -> str:
    canonical = json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def _render_compass_md(data: dict[str, Any], digest: str) -> str:
    threads = data.get("active_long_threads") or []
    scale = data.get("scale_estimate") or {}
    lines = [
        "---",
        "schema: 1",
        f"compass_digest: {digest}",
        "---",
        "",
        "# Story Compass — Thiên Mệnh Thư",
        "",
        "## Ending Direction",
        "",
        str(data.get("ending_direction") or "").strip(),
        "",
        "## Scale Estimate",
        "",
        ", ".join(f"{k}: {v}" for k, v in sorted(scale.items())) or "(unset)",
        "",
        "## Active Long Threads",
        "",
    ]
    if threads:
        for t in threads:
            lines.append(f"- {json.dumps(t, ensure_ascii=False, sort_keys=True)}")
    else:
        lines.append("(none)")
    lines += [
        "",
        "<!-- machine-readable canon; do not edit by hand -->",
        "```json compass-data",
        json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2),
        "```",
        "",
    ]
    return "\n".join(lines)


def update_compass(
    novel_path: str | Path,
    *,
    ending_direction: str,
    active_long_threads: Optional[list[dict[str, Any]]] = None,
    scale_estimate: Optional[dict[str, Any]] = None,
    current_volume_id: Optional[str] = None,
    current_arc_id: Optional[str] = None,
) -> dict[str, Any]:
    """Create/refresh ``outlines/compass.md`` idempotently (Req 1; P14)."""
    root = Path(novel_path)
    data = _compass_data(
        ending_direction=ending_direction,
        active_long_threads=list(active_long_threads or []),
        scale_estimate=dict(scale_estimate or {}),
        current_volume_id=current_volume_id,
        current_arc_id=current_arc_id,
    )
    digest = _digest(data)
    text = _render_compass_md(data, digest)
    changed = _write_if_changed(root / COMPASS_REL, text)
    return {"compass_digest": digest, "changed": changed, "path": COMPASS_REL}


def read_compass(novel_path: str | Path) -> Optional[dict[str, Any]]:
    """Parse the embedded json block of ``compass.md`` (None when absent)."""
    path = Path(novel_path) / COMPASS_REL
    if not path.exists():
        return None
    match = _COMPASS_BLOCK_RE.search(path.read_text(encoding="utf-8"))
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        _LOG.warning(
            "compass: compass.md embedded json block at %s is malformed; "
            "treating as no compass", path, exc_info=True,
        )
        return None
    data["compass_digest"] = _digest(
        {k: v for k, v in data.items() if k != "compass_digest"}
    )
    return data


# --------------------------------------------------------------------------- #
# Layered outline
# --------------------------------------------------------------------------- #


def _write_json_if_changed(path: Path, payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    return _write_if_changed(path, text)


def write_layered_outline(
    novel_path: str | Path, payload: dict[str, Any]
) -> dict[str, Any]:
    root = Path(novel_path)
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    digest = f"sha256:{hashlib.sha256(canonical).hexdigest()}"
    changed = _write_json_if_changed(root / LAYERED_OUTLINE_REL, payload)
    return {"layered_outline_digest": digest, "changed": changed}


def read_layered_outline(novel_path: str | Path) -> Optional[dict[str, Any]]:
    path = Path(novel_path) / LAYERED_OUTLINE_REL
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        _LOG.warning(
            "compass: layered_outline.json at %s is not valid JSON; ignoring",
            path, exc_info=True,
        )
        return None


# --------------------------------------------------------------------------- #
# Arc map
# --------------------------------------------------------------------------- #


def read_arc_map(novel_path: str | Path) -> ArcMap:
    path = Path(novel_path) / ARC_MAP_REL
    if not path.exists():
        return ArcMap()
    try:
        return ArcMap.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError:
        # A corrupt arc map otherwise degrades silently to "no arcs", making
        # boundary_check report at_arc_end=False everywhere and plan_expansion
        # find nothing. Surface it so the corruption is diagnosable.
        _LOG.warning(
            "compass: arc_map.json at %s is not valid JSON; treating as empty",
            path, exc_info=True,
        )
        return ArcMap()


def upsert_arc(novel_path: str | Path, arc: dict[str, Any]) -> dict[str, Any]:
    """Insert/replace an arc in ``arc_map.json`` idempotently (P14)."""
    root = Path(novel_path)
    arc_map = read_arc_map(root)
    changed = arc_map.upsert(ArcSpec.from_dict(arc))
    arc_map.validate()
    if changed:
        _write_json_if_changed(root / ARC_MAP_REL, arc_map.to_dict())
    return {"arc_map_digest": arc_map.digest(), "changed": changed}


# --------------------------------------------------------------------------- #
# Boundary + expansion planning
# --------------------------------------------------------------------------- #


def boundary_check(novel_path: str | Path, chapter: int) -> dict[str, Any]:
    """Whether ``chapter`` ends an arc and/or volume per the arc map (Req 4)."""
    arc_map = read_arc_map(novel_path)
    arc = arc_map.arc_for(chapter)
    at_arc_end = bool(arc and arc.end_chapter == chapter)
    at_volume_end = False
    if at_arc_end and arc is not None and arc.volume_id:
        # A volume ends only at its LAST-declared arc: if any arc of the same
        # volume is declared after this one (even a not-yet-placed skeleton),
        # the volume is not finished (fixes premature at_volume_end).
        same_volume = [a for a in arc_map.arcs if a.volume_id == arc.volume_id]
        at_volume_end = bool(same_volume) and same_volume[-1].arc_id == arc.arc_id
    return {
        "chapter": chapter,
        "at_arc_end": at_arc_end,
        "at_volume_end": at_volume_end,
        "arc_id": arc.arc_id if arc else None,
        "volume_id": arc.volume_id if arc else None,
    }


def plan_expansion(novel_path: str | Path) -> dict[str, Any]:
    """Return the next skeleton arc that should be expanded, if any (Req 2)."""
    arc_map = read_arc_map(novel_path)
    for arc in arc_map.arcs:
        if arc.status == "skeleton":
            return {
                "kind": "arc",
                "target_id": arc.arc_id,
                "arc_type": arc.arc_type,
                "estimated_chapters": arc.estimated_chapters,
                "expand_task_key": f"arc.{arc.arc_id}.expand",
            }
    return {"kind": None, "target_id": None}


def migrate_to_compass(
    novel_path: str | Path,
    *,
    current_chapter: int,
    target_chapters: int,
    arc_size: int = 50,
) -> dict[str, Any]:
    """Bootstrap compass artifacts for an in-progress novel (Req 11.4).

    Derives a Story Compass + an arc map from the current progress: chapters
    already written ``[1, current_chapter]`` become a single ``done`` arc (so
    they are treated as already-expanded), and the scale estimate seeds from
    ``target_chapters``. Idempotent: re-running with the same progress is a
    no-op on canon (P14).
    """
    root = Path(novel_path)
    compass = update_compass(
        root,
        ending_direction="(migrated — cập nhật ở ranh giới Cuốn kế)",
        active_long_threads=[],
        scale_estimate={"chapters": target_chapters},
        current_volume_id="vol_001",
        current_arc_id="arc_001",
    )
    arc_changed = False
    if current_chapter >= 1:
        arc = {
            "arc_id": "arc_001",
            "start_chapter": 1,
            "end_chapter": current_chapter,
            "estimated_chapters": max(MIN_ARC_LEN, current_chapter),
            "arc_type": "growth_breakthrough",
            "status": "done",
            "volume_id": "vol_001",
        }
        arc_changed = upsert_arc(root, arc)["changed"]
    return {
        "compass_digest": compass["compass_digest"],
        "expanded_through_chapter": max(0, current_chapter),
        "changed": compass["changed"] or arc_changed,
    }


# --------------------------------------------------------------------------- #
# Tool dispatch + registration
# --------------------------------------------------------------------------- #

_ACTIONS = {
    "update_compass": update_compass,
    "read_compass": read_compass,
    "write_layered_outline": write_layered_outline,
    "read_layered_outline": read_layered_outline,
    "upsert_arc": upsert_arc,
    "read_arc_map": lambda novel_path: read_arc_map(novel_path).to_dict(),
    "boundary_check": boundary_check,
    "plan_expansion": plan_expansion,
    "migrate_to_compass": migrate_to_compass,
}


def compass_tool(action: str, **kwargs: Any) -> Any:
    fn = _ACTIONS.get(action)
    if fn is None:
        raise ValueError(
            f"unknown action {action!r}; expected one of {sorted(_ACTIONS)}"
        )
    return fn(**kwargs)


registry.register(
    "novelkit_compass",
    compass_tool,
    schema={
        "name": "novelkit_compass",
        "description": "Story Compass, layered outline, and arc-map management "
        "(idempotent, content-addressed).",
        "input": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": sorted(_ACTIONS)},
                "novel_path": {"type": "string"},
            },
            "required": ["action", "novel_path"],
        },
        "output": {"type": "object"},
    },
    module=__name__,
)


__all__ = [
    "compass_tool",
    "update_compass",
    "read_compass",
    "write_layered_outline",
    "read_layered_outline",
    "read_arc_map",
    "upsert_arc",
    "boundary_check",
    "plan_expansion",
    "COMPASS_REL",
    "LAYERED_OUTLINE_REL",
    "ARC_MAP_REL",
]
