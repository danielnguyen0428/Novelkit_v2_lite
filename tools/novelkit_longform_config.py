"""Long-form GA feature config + flags loader (Req 14.1, 14.2).

Stdlib-only. Config is merged in this precedence (later wins):

1. :data:`DEFAULTS` (this module)
2. package config ``novelkit-hermes/config/longform.json``
3. compass auto-enable (when ``mode="compass"``) — safety net
4. per-novel override ``<novel_path>/config/longform.json`` (optional)

This mirrors the "genre/config is a parameter, not a code branch" rule from the
migration design: long-form thresholds and feature flags live in config, never
hard-coded in the pipeline.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

_LOG = logging.getLogger(__name__)

DEFAULTS: dict[str, Any] = {
    "COMPASS_MODE_MIN_CHAPTERS": 60,
    "MIN_ARC_LEN": 8,
    "DEFAULT_ARC_LEN": 12,
    "K_PER_DIM": 2,
    "STYLE_STATS_WINDOW": 10,
    "REPEAT_GUARD_WINDOW": 3,
    "REPEAT_MAX": 1,
    "REPEAT_MIN_SENTENCE_LEN": 40,
    "RECENT_CAST_LIMIT": 12,
    "MAX_STOP_BLOCKS": 3,
    "flags": {
        "compass": False,
        "recall": False,
        "minor_cast": False,
        "style_stats": False,
        "reminder": False,
        "steer": False,
        "diag": False,
        "graph": False,
        "graph_llm_enrich": False,
        "anti_slop": False,
        "style_edits": False,
        "style_global": False,
    },
    "ANTI_SLOP_AI_RISK_WARN": 35.0,
}

#: Feature-flag names recognised by :func:`flag_enabled` (used by tests/config).
FLAG_NAMES: tuple[str, ...] = tuple(DEFAULTS["flags"].keys())

#: When mode is "compass", force-enable all feature flags as a safety net.
#: Per-novel config can still override individual flags to False.
COMPASS_AUTO_FLAGS: dict[str, bool] = {name: True for name in FLAG_NAMES}

#: Package-level config shipped with the repo.
PACKAGE_CONFIG_PATH: Path = (
    Path(__file__).resolve().parent.parent / "config" / "longform.json"
)


def _read_json(path: Path, *, required: bool = False) -> dict[str, Any]:
    """Read a JSON object from ``path``; ``{}`` when absent or unreadable.

    ``required=True`` marks a config whose absence is a *deployment* fault rather
    than an optional override, and logs it. This distinction matters: every flag
    in :data:`DEFAULTS` is ``False`` while every flag in the shipped
    ``config/longform.json`` is ``True``, so losing that one file silently turned
    off all twelve long-form features (recall, graph, style stats, anti-slop…)
    with no error and no log — the pipeline simply got quieter and worse.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if required:
            _LOG.error(
                "long-form config %s is MISSING — every feature flag falls back "
                "to the disabled defaults (recall/graph/style_stats/anti_slop "
                "will be off). Restore the file to re-enable them.",
                path,
            )
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        if required:
            _LOG.error(
                "long-form config %s is UNREADABLE (%s) — every feature flag "
                "falls back to the disabled defaults. Fix the file to re-enable "
                "them.",
                path, exc,
            )
        return {}
    if not isinstance(data, dict):
        if required:
            _LOG.error(
                "long-form config %s is not a JSON object (got %s) — feature "
                "flags fall back to the disabled defaults.",
                path, type(data).__name__,
            )
        return {}
    return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Return a new dict: ``override`` merged over ``base`` (one level deep for
    the nested ``flags`` map; scalars replaced)."""
    out = dict(base)
    for key, value in override.items():
        if (
            key in out
            and isinstance(out[key], dict)
            and isinstance(value, dict)
        ):
            merged = dict(out[key])
            merged.update(value)
            out[key] = merged
        else:
            out[key] = value
    return out


def load_config(
    novel_path: Optional[str | Path] = None, *, mode: Optional[str] = None
) -> dict[str, Any]:
    """Resolve effective long-form config.

    Merge order (later wins):
    ``DEFAULTS`` < package ``config/longform.json`` < compass-auto-enable
    (when ``mode=="compass"``) < per-novel ``<novel_path>/config/longform.json``.

    The compass layer guarantees all flags are ON for compass-mode novels even
    if the package config is reset. Per-novel config can still opt-out individual
    flags by setting them to ``false``.
    """
    cfg = _deep_merge(DEFAULTS, _read_json(PACKAGE_CONFIG_PATH, required=True))
    if mode == "compass":
        cfg = _deep_merge(cfg, {"flags": COMPASS_AUTO_FLAGS})
    if novel_path is not None:
        novel_cfg = _read_json(Path(novel_path) / "config" / "longform.json")
        if novel_cfg:
            cfg = _deep_merge(cfg, novel_cfg)
    return cfg


def flag_enabled(
    name: str, novel_path: Optional[str | Path] = None, *, mode: Optional[str] = None
) -> bool:
    """True when feature flag ``name`` is enabled in the effective config."""
    if name not in FLAG_NAMES:
        raise ValueError(f"unknown long-form flag {name!r}; expected {FLAG_NAMES}")
    return bool(load_config(novel_path, mode=mode).get("flags", {}).get(name, False))


__all__ = [
    "COMPASS_AUTO_FLAGS",
    "DEFAULTS",
    "FLAG_NAMES",
    "PACKAGE_CONFIG_PATH",
    "load_config",
    "flag_enabled",
]
