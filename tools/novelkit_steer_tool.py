"""NovelKit steer tool — realtime intervention router (Req 9).

Classifies a user's mid-run instruction and routes it deterministically (no LLM
needed for routing; the LLM only *executes* once the route is fixed), mirroring
the ``coordinator.md`` taxonomy:

    continue · query · modify → { stage_plan | scope_change | plot_or_character
                                  | rewrite_existing | style_rule }

Key discipline (Req 9.6): "怎么viết" (craft/style) → ``style_rule`` (novelkit_rules);
"viết gì" (plot/structure) → architect/compass; "sửa đã viết" → editor enqueue.
``rewrite_existing`` only enqueues into ``rewrite_queue`` — the writer never edits
a finished chapter directly (sync stays the only path into canon).

Steers are logged to ``logs/steer_log.jsonl`` and recorded on
``CreativeState.pending_steer`` so a resume restores them (Property P22).
Idempotent by ``steer_id`` (deterministic over the text).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from tools import registry

STEER_LOG_REL = "logs/steer_log.jsonl"

ROUTES = (
    "none",
    "answer",
    "stage_plan",
    "scope_change",
    "plot_or_character",
    "rewrite_existing",
    "style_rule",
)


@dataclass(frozen=True)
class SteerIntent:
    steer_id: str
    kind: str  # continue | query | modify
    route: str
    raw_text: str
    affected_chapters: tuple[int, ...] = ()
    scope: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["affected_chapters"] = list(self.affected_chapters)
        return data


# --- pattern banks (ordered, most-specific first) -------------------------- #

_CONTINUE_RE = re.compile(r"\b(tiếp tục|viết tiếp|tiếp đi|đi tiếp|continue)\b", re.I)
_QUERY_RE = re.compile(
    r"(hiện trạng|trạng thái|thế nào|bao nhiêu|là gì|cho.*xem|status|\?)", re.I
)
_REWRITE_RE = re.compile(
    r"(viết lại|sửa lại|chỉnh lại|chỉnh sửa|rewrite).{0,15}(chương|chapter)", re.I
)
_STYLE_RE = re.compile(
    r"(\d+\s*(?:từ|chữ)\b|mỗi chương.*(?:từ|chữ)|văn phong|phong cách|giọng văn|"
    r"đối thoại|tiêu đề|ít dùng|không dùng|hạn chế|câu ngắn|câu dài|ngôi kể|"
    r"bớt (?:tả|miêu tả)|nhịp văn)",
    re.I,
)
_SCOPE_RE = re.compile(
    r"((tăng|thêm|kéo dài|rút ngắn|thu ngắn|giảm|nâng).{0,12}(chương|chapter|cuốn|卷)"
    r"|số chương|lên\s*\d+\s*chương|dài hơn|ngắn hơn|提前收尾|sớm kết)",
    re.I,
)
_STAGE_RE = re.compile(r"(giai đoạn|hướng (?:tiếp theo|sau)|định hướng|brief)", re.I)

_CHAPTER_NUM_RE = re.compile(r"(?:chương|chapter)\s*(\d+)", re.I)


def _steer_id(text: str) -> str:
    return hashlib.sha1(text.strip().encode("utf-8")).hexdigest()[:12]


def classify(text: str, dna_path: Optional[str | Path] = None) -> SteerIntent:
    """Route ``text`` to exactly one route (pure, deterministic — P22)."""
    raw = (text or "").strip()
    sid = _steer_id(raw)
    chapters = tuple(int(m) for m in _CHAPTER_NUM_RE.findall(raw))

    if _CONTINUE_RE.search(raw):
        return SteerIntent(sid, "continue", "none", raw)
    if _QUERY_RE.search(raw):
        return SteerIntent(sid, "query", "answer", raw)
    # modify subtypes, most specific first
    if _REWRITE_RE.search(raw):
        return SteerIntent(sid, "modify", "rewrite_existing", raw,
                           affected_chapters=chapters, scope="existing_chapters")
    if _STYLE_RE.search(raw):
        return SteerIntent(sid, "modify", "style_rule", raw, scope="craft")
    if _SCOPE_RE.search(raw):
        return SteerIntent(sid, "modify", "scope_change", raw, scope="length")
    if _STAGE_RE.search(raw):
        return SteerIntent(sid, "modify", "stage_plan", raw, scope="next_stage")
    return SteerIntent(sid, "modify", "plot_or_character", raw, scope="story")


# --- apply ------------------------------------------------------------------ #


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_log(novel_path: Path, record: dict[str, Any]) -> None:
    path = novel_path / STEER_LOG_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _already_applied(novel_path: Path, steer_id: str) -> bool:
    """True if the steer log already records a successful apply for ``steer_id``.

    This is the robust idempotency source (review #16): it survives a resume
    even after a downstream consumer clears ``pending_steer``.
    """
    path = novel_path / STEER_LOG_REL
    if not path.exists():
        return False
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("steer_id") == steer_id and record.get("applied") is True:
                    return True
    except OSError:
        return False
    return False


def _append_due_action(ps: Any, action: dict[str, Any]) -> bool:
    """Append a creative due-action, deduped by (kind, source_steer)."""
    key = (action.get("kind"), action.get("source_steer"))
    for existing in ps.creative.due_actions:
        if (existing.get("kind"), existing.get("source_steer")) == key:
            return False
    ps.creative.due_actions.append(action)
    return True


def _apply_scope_change(root: Path, ps: Any, intent: SteerIntent) -> dict[str, Any]:
    """Retarget the story length: update the compass scale (if any) + queue a
    reseed due-action so the outline is re-expanded to the new chapter count."""
    numbers = re.findall(r"\d+", intent.raw_text)
    target = int(numbers[0]) if numbers else None
    compass_updated = False
    if target is not None:
        from tools.novelkit_compass_tool import read_compass, update_compass

        current = read_compass(root)
        if current is not None:
            scale = dict(current.get("scale_estimate") or {})
            scale["chapters"] = target
            update_compass(
                root,
                ending_direction=str(current.get("ending_direction") or ""),
                active_long_threads=list(current.get("active_long_threads") or []),
                scale_estimate=scale,
                current_volume_id=current.get("current_volume_id"),
                current_arc_id=current.get("current_arc_id"),
            )
            compass_updated = True
    action: dict[str, Any] = {
        "kind": "reseed",
        "text": intent.raw_text,
        "source_steer": intent.steer_id,
        "created_at": _now_iso(),
    }
    if target is not None:
        action["target_chapters"] = target
    _append_due_action(ps, action)
    return {
        "executed": "scope_change",
        "target_chapters": target,
        "compass_updated": compass_updated,
    }


def _execute_route(root: Path, ps: Any, intent: SteerIntent) -> dict[str, Any]:
    """Perform the deterministic side-effect for a classified steer route.

    Discipline (Req 9.6): craft/style → ``novelkit_rules`` (append_rule);
    plot/structure → recorded as a creative due-action for the architect/compass
    to consume next planning pass; length → compass retarget + reseed;
    "sửa đã viết" → rewrite_queue only (sync stays the sole path into canon).
    """
    route = intent.route

    if route == "rewrite_existing":
        added: list[int] = []
        for ch in intent.affected_chapters:
            queue_id = f"rewrite_chapter_{ch:04d}_steer_{intent.steer_id}"
            if not any(
                q.get("queue_id") == queue_id for q in ps.creative.rewrite_queue
            ):
                ps.creative.rewrite_queue.append({
                    "queue_id": queue_id, "kind": "rewrite", "chapter": ch,
                    "reason_codes": ["user_steer"], "priority": 20,
                    "attempt": 0, "max_attempts": 3, "status": "pending",
                    "created_at": _now_iso(),
                })
                added.append(ch)
        return {"executed": "rewrite_enqueued", "chapters": added}

    if route == "style_rule":
        from tools.novelkit_rules_tool import append_rule

        result = append_rule(root, intent.raw_text)
        return {
            "executed": "style_rule",
            "rule_id": result.get("rule_id"),
            "rules_digest": result.get("rules_digest"),
            "changed": result.get("changed"),
        }

    if route == "scope_change":
        return _apply_scope_change(root, ps, intent)

    if route in ("stage_plan", "plot_or_character"):
        _append_due_action(ps, {
            "kind": route,
            "text": intent.raw_text,
            "source_steer": intent.steer_id,
            "created_at": _now_iso(),
        })
        return {"executed": "due_action", "kind": route}

    # 'answer' (query) and any other route: nothing to execute, just recorded.
    return {"executed": "recorded"}


def apply(
    novel_path: str | Path, text: str, state: dict[str, Any]
) -> dict[str, Any]:
    """Apply a steer to a serialised PipelineState (Req 9).

    Idempotent by ``steer_id`` via the steer log (robust across resume). The
    route is executed deterministically here — style rules are written to the
    rule snapshot, length changes retarget the compass + queue a reseed, plot /
    stage steers are recorded as creative due-actions, and rewrites are enqueued
    (the writer never edits finished canon directly). Returns the updated state,
    the route, and an ``executed`` summary.
    """
    from tools.novelkit_pipeline_tool import PipelineState

    root = Path(novel_path)
    intent = classify(text)
    ps = PipelineState.from_dict(state)

    existing = ps.creative.pending_steer
    if _already_applied(root, intent.steer_id) or (
        existing and existing.get("steer_id") == intent.steer_id
    ):
        return {
            "state": ps.to_dict(), "route": intent.route,
            "affected_chapters": list(intent.affected_chapters),
            "steer_id": intent.steer_id, "applied": False, "executed": {},
        }

    if intent.kind == "continue":
        _append_log(root, {
            "steer_id": intent.steer_id, "kind": intent.kind, "route": intent.route,
            "affected_chapters": [], "applied": False, "at": _now_iso(),
        })
        return {
            "state": ps.to_dict(), "route": intent.route,
            "affected_chapters": [], "steer_id": intent.steer_id,
            "applied": False, "executed": {},
        }

    executed = _execute_route(root, ps, intent)

    ps.creative.pending_steer = {
        "steer_id": intent.steer_id, "kind": intent.kind, "route": intent.route,
        "affected_chapters": list(intent.affected_chapters),
        "raw_text": intent.raw_text, "created_at": _now_iso(),
        "executed": executed,
    }

    _append_log(root, {
        "steer_id": intent.steer_id, "kind": intent.kind, "route": intent.route,
        "affected_chapters": list(intent.affected_chapters),
        "executed": executed, "applied": True, "at": _now_iso(),
    })
    return {
        "state": ps.to_dict(), "route": intent.route,
        "affected_chapters": list(intent.affected_chapters),
        "steer_id": intent.steer_id, "applied": True, "executed": executed,
    }


def consume_due_actions(
    novel_path: str | Path, state: dict[str, Any]
) -> dict[str, Any]:
    """Consume pending due_actions from CreativeState (Orchestrator calls each turn).

    For each due_action:
    - ``plot_or_character`` → delegate to Plot Weaver (update outline/compass)
    - ``stage_plan`` → delegate to Plot Weaver (redirect next arc direction)
    - ``reseed`` → handled inline (target_chapters already updated by scope_change)

    Returns the updated state + a manifest of consumed actions. Idempotent: an
    empty ``due_actions`` list is a no-op. Consumed actions are removed from state
    so they are never re-processed on resume (P22).
    """
    from tools.novelkit_pipeline_tool import PipelineState

    root = Path(novel_path)
    ps = PipelineState.from_dict(state)
    consumed: list[dict[str, Any]] = []
    remaining: list[dict[str, Any]] = []

    for action in ps.creative.due_actions:
        kind = action.get("kind")
        if kind in ("plot_or_character", "stage_plan", "reseed"):
            consumed.append({
                "kind": kind,
                "source_steer": action.get("source_steer"),
                "text": action.get("text", ""),
                "delegate_to": "Plot Weaver",
                "instruction": _due_action_instruction(kind, action, root),
            })
        else:
            remaining.append(action)

    ps.creative.due_actions = remaining
    if consumed:
        ps.state_version += 1

    return {
        "state": ps.to_dict(),
        "consumed": consumed,
        "remaining_count": len(remaining),
    }


def _due_action_instruction(kind: str, action: dict[str, Any], root: Path) -> str:
    """Build the Plot Weaver dispatch instruction for a consumed due_action."""
    text = action.get("text", "")
    if kind == "plot_or_character":
        return (
            f"CẬP NHẬT foundation theo chỉ thị người dùng: \"{text}\". "
            "Cập nhật outline/compass/arc_map nếu ảnh hưởng cấu trúc. "
            "Cập nhật database/characters nếu ảnh hưởng nhân vật. "
            "Giữ nguyên các chương đã sync — chỉ ảnh hưởng chương chưa viết."
        )
    if kind == "stage_plan":
        return (
            f"ĐỔI HƯỚNG giai đoạn/arc kế tiếp theo chỉ thị: \"{text}\". "
            "Cập nhật compass.md (ending_direction / active_long_threads) và "
            "layered_outline.json cho Hồi skeleton kế tiếp."
        )
    if kind == "reseed":
        target = action.get("target_chapters")
        return (
            f"RESEED pipeline: target_chapters={target}. "
            "Gọi advance_expansion nếu cần mở rộng DAG."
        )
    return f"Unknown due_action kind: {kind}"


def steer_tool(action: str, **kwargs: Any) -> Any:
    if action == "classify":
        return classify(kwargs["text"], kwargs.get("dna_path")).to_dict()
    if action == "apply":
        return apply(kwargs["novel_path"], kwargs["text"], kwargs["state"])
    if action == "consume_due_actions":
        return consume_due_actions(kwargs["novel_path"], kwargs["state"])
    raise ValueError(
        f"unknown action {action!r}; expected classify|apply|consume_due_actions"
    )


registry.register(
    "novelkit_steer",
    steer_tool,
    schema={
        "name": "novelkit_steer",
        "description": "Realtime intervention router (classify + apply + consume_due_actions).",
        "input": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["classify", "apply", "consume_due_actions"]},
                "text": {"type": "string"},
                "novel_path": {"type": "string"},
                "state": {"type": "object"},
            },
            "required": ["action"],
        },
        "output": {"type": "object"},
    },
    module=__name__,
)


__all__ = ["steer_tool", "classify", "apply", "consume_due_actions", "SteerIntent", "ROUTES"]
