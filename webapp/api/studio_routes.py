"""Local Studio routes."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from webapp.api.deps import get_current_user
from webapp.db.models import User
from webapp.db.session import get_db

from .service import SERVICE

router = APIRouter(prefix="/api/studio/novels", tags=["studio"])

#: Persisted derivative knowledge-graph file, relative to the novel workspace.
_GRAPH_REL_PATH = "logs/knowledge_graph.json"


@router.get("/{slug}/graph")
def read_graph(
    slug: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Read-only view of a novel's persisted knowledge graph (Req 8.1).

    Ownership is enforced by ``_require_owned_novel`` (raises ServiceError 404 for
    an unknown/foreign slug, mapped to HTTP 404 by the app's exception handler).

    This endpoint NEVER rebuilds the graph — it only serves the derivative
    artifact already exported to ``logs/knowledge_graph.json`` (Req 8.6, so the
    frontend reads a static file). A missing file is a valid empty state, not an
    error, and a corrupt/unreadable file is reported as empty rather than a 500.

    The body also carries a ``contradictions`` map (``{"soft": [...], "hard": [...]}``)
    so the frontend can highlight conflicting nodes/edges (Req 8.4). It is derived
    read-only via ``detect_contradictions`` (pure, no writes); any empty/error path
    yields the empty tiered map rather than a 500.
    """
    _novel, path = SERVICE._require_owned_novel(db, user, slug)
    empty_contradictions: dict[str, list[Any]] = {"soft": [], "hard": []}
    graph_path = path / _GRAPH_REL_PATH
    if not graph_path.is_file():
        return {"exists": False, "graph": None, "contradictions": empty_contradictions}
    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # Unreadable/corrupt export → treat as empty, never crash the read path.
        return {"exists": False, "graph": None, "contradictions": empty_contradictions}
    try:
        from tools.novelkit_graph_tool import detect_contradictions

        contradictions = detect_contradictions(path)
    except Exception:  # noqa: BLE001 — detection is best-effort; never 500 the read
        contradictions = empty_contradictions
    return {
        "exists": True,
        "graph_digest": data.get("graph_digest"),
        "metadata": data.get("metadata"),
        "graph": data.get("graph"),
        "contradictions": contradictions,
    }
