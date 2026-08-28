"""Consistency dimension in creative diagnostics (Req 4.3; Property P23).

A hard KG contradiction (death@50 then acts@80) must surface as a
``dimension == "consistency"`` finding from ``diagnose``. The consistency
dimension only runs when the ``graph`` feature flag is enabled, so the test
novel ships a per-novel ``config/longform.json`` turning it on. The whole path
is read-only (P23): running diagnose must not create/mutate any file.
"""

from __future__ import annotations

import hashlib
import json

import bootstrap  # noqa: F401 — ensures novelkit_graph is registered
from plugins.memory.novelkit_memory import get_provider
from tools.novelkit_diagnostics_tool import diagnose


def _enable_graph_flag(root):
    """Write a per-novel config turning the ``graph`` feature flag on."""
    cfg = root / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "longform.json").write_text(
        json.dumps({"flags": {"graph": True}}), encoding="utf-8"
    )


def _disable_graph_flag(root):
    """Write a per-novel config turning the ``graph`` feature flag off."""
    cfg = root / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "longform.json").write_text(
        json.dumps({"flags": {"graph": False}}), encoding="utf-8"
    )


def _disable_graph_flag(root):
    """Write a per-novel config turning the ``graph`` feature flag off."""
    cfg = root / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "longform.json").write_text(
        json.dumps({"flags": {"graph": False}}), encoding="utf-8"
    )


def _seed_dead_then_acts(root):
    (root / "database" / "characters").mkdir(parents=True)
    (root / "database" / "characters" / "A.md").write_text("# A\n", "utf-8")
    (root / "chapters").mkdir()
    for n in (50, 80):
        (root / "chapters" / f"chapter_{n:03d}.md").write_text("x", "utf-8")
    p = get_provider()
    p.add(
        {"category": "timeline", "subject": "A", "field": "death",
         "value": "chết", "source_chapter": 50, "payload": {}},
        scope=root,
    )
    p.add(
        {"category": "character_state", "subject": "A", "field": "state_change",
         "value": "vung kiếm", "source_chapter": 80, "payload": {}},
        scope=root,
    )
    from tools.novelkit_graph_tool import build

    build(str(root))


def test_consistency_finding(tmp_path):
    _enable_graph_flag(tmp_path)
    _seed_dead_then_acts(tmp_path)
    findings = diagnose(str(tmp_path))
    consistency = [f for f in findings if f["dimension"] == "consistency"]
    assert consistency, "expected at least one consistency finding"
    assert all(f["evidence"] and f["suggestion"] for f in consistency)


def test_consistency_off_when_flag_disabled(tmp_path):
    # graph flag explicitly off → no consistency dim.
    _disable_graph_flag(tmp_path)
    _seed_dead_then_acts(tmp_path)
    findings = diagnose(str(tmp_path))
    assert not any(f["dimension"] == "consistency" for f in findings)


def test_consistency_diagnose_is_read_only(tmp_path):
    _enable_graph_flag(tmp_path)
    _seed_dead_then_acts(tmp_path)

    def _snapshot():
        h = hashlib.sha256()
        for p in sorted(tmp_path.rglob("*")):
            if p.is_file():
                h.update(p.relative_to(tmp_path).as_posix().encode())
                h.update(p.read_bytes())
        return h.hexdigest()

    before = _snapshot()
    diagnose(str(tmp_path))
    diagnose(str(tmp_path), redact=True)
    assert _snapshot() == before  # no canon/state mutation (P23)
