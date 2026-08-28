"""NovelKit pipeline tool — DAG, phase ordering, breaker, rolling window, resume.

Phase 3 of the migration (Task 5). This Custom Tool **extracts the algorithms**
from the legacy control plane — ``control_plane.py`` + ``cp_*.py`` +
``recovery_orchestrator.py`` — and repackages them as a self-registering Hermes
tool. It deliberately **drops the legacy SQLite control plane** (finding D2):
durable state lives in a plain serialisable :class:`PipelineState` that a Hermes
session store persists, and a ``logs/pipeline_status.json`` snapshot is still
emitted so the existing doctor tooling keeps working (Task 5.2).

What is ported (semantics-preserving)
-------------------------------------
- **DAG + phase ordering** (``build_task_specs`` / dependency edges):
  Bootstrap → Outline → Write → Review → Sync, with the per-chapter dependency
  chain and the every-10th-chapter / arc-boundary character-update barrier.
  (Requirement 8; Property P1.)
- **Circuit breaker** (``breaker_open`` / ``update_breaker_state``): hard≤2,
  soft≤3, total≤5 within a scope; resets on scope change, on success, and when
  the failure signature changes. (Requirement 10.1; Property P3.)
- **Rolling window** (``rolling_window_plan``): auto-seed the next batch so the
  buffer ahead of the last synced chapter stays within ``[MIN_REMAINING,
  WINDOW]``. (Requirement 10.3; Property P4.)
- **Recovery / resume** (``next_ready_task`` + ``recovery_orchestrator``):
  resume continues from the next ready task without re-running done work, and
  failures are diagnosed into deterministic recovery actions.
  (Requirement 19.3; Property P12.)

Design references: design.md §"Components and Interfaces" #1, §"Data Models"
(Task / Verdict), §"Correctness Properties" P1/P3/P4/P12.

The module is dependency-free (stdlib only) so it is verifiable in isolation;
``tools.registry`` is the one local import (the Hermes registry shim).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from tools import registry
from tools.task_output_contracts import OutputContract, output_contract_for_task

# --------------------------------------------------------------------------- #
# Constants (ported from cp_constants.py — kept byte-identical, Task 5.2)
# --------------------------------------------------------------------------- #

#: Review quality thresholds (Requirement 9.1, shared with the gate tool).
REVIEW_PASS_SCORE = 85
REVIEW_SOFT_FAIL_SCORE = 70

#: Circuit-breaker bounds within a scope (Requirement 10.1).
MAX_HARD_FAIL = 2
MAX_SOFT_FAIL = 3
MAX_TOTAL = 5

#: How many times a chapter that fails the SYNC quality gate is sent back
#: through review+sync for another automated rewrite cycle before the pipeline
#: stops and asks for manual approval. Each cycle re-runs critique (which itself
#: revises the draft up to ``max_revisions`` times), so this bounds the extra
#: token spend while still giving a sub-bar chapter real chances to reach pass.
MAX_REWRITE_CYCLES = 2

#: Rolling-window seeding (Requirement 10.3).
ROLLING_WINDOW_SIZE = 5
ROLLING_WINDOW_MIN_REMAINING = 3

#: Arc + character-update cadence.
ARC_SIZE = 50
CHARACTER_UPDATE_INTERVAL_CHAPTERS = 10
CHAPTER_HISTORY_LIMIT = 200

#: Canon tokens (resolved by the context engine; carried unresolved on specs).
SHARED_CANON_TOKEN = "@shared_canon"
SHARED_CANON_SECONDARY_TOKEN = "@shared_canon_secondary"
SHARED_WORLDBUILDING_GUIDE_TOKEN = "@worldbuilding_guide"

#: Status snapshot template kept compatible with the legacy doctor (Task 5.2).
PIPELINE_STATUS_TEMPLATE: dict[str, Any] = {
    "novel": "",
    "current_phase": None,
    "current_chapter": None,
    "current_arc": None,
    "status": "idle",
    "last_updated": None,
    "chapter_history": [],
    "active_agents": [],
    "circuit_breaker": {
        "hard_fail_count": 0,
        "soft_fail_count": 0,
        "total_attempts": 0,
        "max_hard_fail": MAX_HARD_FAIL,
        "max_soft_fail": MAX_SOFT_FAIL,
        "max_total": MAX_TOTAL,
        "scope": None,
        "failure_signature": None,
    },
    "conflict_log": [],
    "stats": {
        "total_chapters_written": 0,
        "total_chapters_passed": 0,
        "average_score": None,
        "total_retries": 0,
        "escalations": 0,
    },
}

PIPELINE_STATUS_REL_PATH = "logs/pipeline_status.json"
PIPELINE_SCHEMA_VERSION = 3


# --------------------------------------------------------------------------- #
# Enums + data models (design.md §"Data Models")
# --------------------------------------------------------------------------- #


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    RETRYABLE = "retryable"


#: Results accepted by ``record_result`` (mirrors legacy RESULT_CHOICES).
RESULT_CHOICES = ("done", "soft_fail", "hard_fail", "blocked", "skipped")
CREATIVE_MODES = ("full_plan", "rolling", "compass")
BUDGET_STATES = ("ok", "warning", "blocked")
QUEUE_ITEM_STATUSES = ("pending", "in_progress", "resolved", "superseded")


@dataclass
class Task:
    """A single pipeline task (design.md §"Data Models" → Task)."""

    task_key: str
    phase: str
    agent_role: str
    command: str
    priority: int
    chapter: Optional[int] = None
    arc: Optional[int] = None
    depends_on: tuple[str, ...] = ()
    input_paths: tuple[str, ...] = ()
    output_paths: tuple[str, ...] = ()
    context_query: Optional[str] = None
    status: str = TaskStatus.PENDING.value
    score: Optional[float] = None
    attempt_count: int = 0

    # ---- output-contract integration (Task 5.3 / finding D7) ----
    def output_contract(self) -> OutputContract:
        return output_contract_for_task(self)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["depends_on"] = list(self.depends_on)
        data["input_paths"] = list(self.input_paths)
        data["output_paths"] = list(self.output_paths)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            task_key=data["task_key"],
            phase=str(data["phase"]),
            agent_role=data["agent_role"],
            command=data["command"],
            priority=int(data["priority"]),
            chapter=data.get("chapter"),
            arc=data.get("arc"),
            depends_on=tuple(data.get("depends_on") or ()),
            input_paths=tuple(data.get("input_paths") or ()),
            output_paths=tuple(data.get("output_paths") or ()),
            context_query=data.get("context_query"),
            status=str(data.get("status") or TaskStatus.PENDING.value),
            score=data.get("score"),
            attempt_count=int(data.get("attempt_count") or 0),
        )


@dataclass
class BreakerState:
    """Circuit-breaker counters for the current scope (Requirement 10.1)."""

    hard_fail_count: int = 0
    soft_fail_count: int = 0
    total_attempts: int = 0
    max_hard_fail: int = MAX_HARD_FAIL
    max_soft_fail: int = MAX_SOFT_FAIL
    max_total: int = MAX_TOTAL
    scope: Optional[str] = None
    failure_signature: Optional[str] = None

    @property
    def is_open(self) -> bool:
        return breaker_open(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BreakerState":
        base = {**PIPELINE_STATUS_TEMPLATE["circuit_breaker"], **(data or {})}
        return cls(
            hard_fail_count=int(base.get("hard_fail_count", 0)),
            soft_fail_count=int(base.get("soft_fail_count", 0)),
            total_attempts=int(base.get("total_attempts", 0)),
            max_hard_fail=int(base.get("max_hard_fail", MAX_HARD_FAIL)),
            max_soft_fail=int(base.get("max_soft_fail", MAX_SOFT_FAIL)),
            max_total=int(base.get("max_total", MAX_TOTAL)),
            scope=base.get("scope"),
            failure_signature=base.get("failure_signature"),
        )


@dataclass
class CreativeState:
    """Creative routing metadata embedded in PipelineState v2."""

    mode: str = "full_plan"
    current_volume_id: Optional[str] = None
    current_arc_id: Optional[str] = None
    expanded_through_chapter: int = 0
    rewrite_queue: list[dict[str, Any]] = field(default_factory=list)
    polish_queue: list[dict[str, Any]] = field(default_factory=list)
    due_actions: list[dict[str, Any]] = field(default_factory=list)
    story_compass_digest: Optional[str] = None
    layered_outline_digest: Optional[str] = None
    arc_map_digest: Optional[str] = None
    rules_digest: Optional[str] = None
    last_accepted_commit_id: Optional[str] = None
    budget_state: str = "ok"
    paused: bool = False
    pause_reason: Optional[str] = None
    # Long-form GA (v3): only serialised when non-default so legacy v2 state
    # digests stay byte-identical (backward compatibility, P24).
    pending_steer: Optional[dict[str, Any]] = None
    stop_block_count: int = 0

    def _validate(self) -> None:
        if self.mode not in CREATIVE_MODES:
            raise ValueError(f"unknown creative mode {self.mode!r}")
        if self.budget_state not in BUDGET_STATES:
            raise ValueError(f"unknown budget_state {self.budget_state!r}")
        for queue_name, items in (
            ("rewrite_queue", self.rewrite_queue),
            ("polish_queue", self.polish_queue),
        ):
            for item in items:
                status = item.get("status", "pending")
                if status not in QUEUE_ITEM_STATUSES:
                    raise ValueError(
                        f"{queue_name} item has unknown status {status!r}"
                    )

    def to_dict(self) -> dict[str, Any]:
        self._validate()
        data = {
            "mode": self.mode,
            "current_volume_id": self.current_volume_id,
            "current_arc_id": self.current_arc_id,
            "expanded_through_chapter": self.expanded_through_chapter,
            "rewrite_queue": list(self.rewrite_queue),
            "polish_queue": list(self.polish_queue),
            "due_actions": list(self.due_actions),
            "story_compass_digest": self.story_compass_digest,
            "layered_outline_digest": self.layered_outline_digest,
            "rules_digest": self.rules_digest,
            "last_accepted_commit_id": self.last_accepted_commit_id,
            "budget_state": self.budget_state,
            "paused": self.paused,
            "pause_reason": self.pause_reason,
        }
        # New v3 fields are emitted ONLY when non-default so a default
        # CreativeState serialises byte-identically to legacy v2 — preserving
        # persisted state digests on first load (P24).
        if self.arc_map_digest is not None:
            data["arc_map_digest"] = self.arc_map_digest
        if self.pending_steer is not None:
            data["pending_steer"] = self.pending_steer
        if self.stop_block_count:
            data["stop_block_count"] = self.stop_block_count
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CreativeState":
        raw = data or {}
        state = cls(
            mode=str(raw.get("mode") or "full_plan"),
            current_volume_id=raw.get("current_volume_id"),
            current_arc_id=raw.get("current_arc_id"),
            expanded_through_chapter=int(raw.get("expanded_through_chapter") or 0),
            rewrite_queue=list(raw.get("rewrite_queue") or []),
            polish_queue=list(raw.get("polish_queue") or []),
            due_actions=list(raw.get("due_actions") or []),
            story_compass_digest=raw.get("story_compass_digest"),
            layered_outline_digest=raw.get("layered_outline_digest"),
            arc_map_digest=raw.get("arc_map_digest"),
            rules_digest=raw.get("rules_digest"),
            last_accepted_commit_id=raw.get("last_accepted_commit_id"),
            budget_state=str(raw.get("budget_state") or "ok"),
            paused=bool(raw.get("paused", False)),
            pause_reason=raw.get("pause_reason"),
            pending_steer=raw.get("pending_steer"),
            stop_block_count=int(raw.get("stop_block_count") or 0),
        )
        state._validate()
        return state


@dataclass(frozen=True)
class SeedPlan:
    """Result of a rolling-window evaluation (Requirement 10.3)."""

    seeded: bool
    start_chapter: Optional[int] = None
    end_chapter: Optional[int] = None
    arc_size: int = ARC_SIZE
    target_chapters: Optional[int] = None
    window_size: int = ROLLING_WINDOW_SIZE
    remaining_window: Optional[int] = None
    inserted_tasks: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResumeReport:
    """Result of a resume (Requirement 19.3 / Property P12)."""

    next_task_key: Optional[str]
    next_task: Optional[Task]
    done_count: int
    pending_count: int
    in_progress_reset: int
    breaker_open: bool

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["next_task"] = self.next_task.to_dict() if self.next_task else None
        return data


# --------------------------------------------------------------------------- #
# Pure helpers (ported from control_plane.py)
# --------------------------------------------------------------------------- #


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_arc(
    chapter: int, arc_size: int = ARC_SIZE, *, arc_map: Optional["ArcMap"] = None
) -> int:
    """Arc index (1-based) for ``chapter``.

    When an ``arc_map`` is supplied and covers the chapter, the index is looked
    up from the narrative-driven boundaries (Req 4); otherwise it falls back to
    the exact legacy arithmetic ``(chapter-1)//arc_size + 1`` so existing novels
    behave identically (Property P16 fallback).
    """
    if arc_map is not None:
        try:
            return arc_map.arc_index_for(chapter)
        except KeyError:
            pass  # chapter beyond placed arcs → fall back to arithmetic
    return ((chapter - 1) // arc_size) + 1


def is_arc_boundary(
    chapter: int,
    arc_size: int = ARC_SIZE,
    *,
    arc_map: Optional["ArcMap"] = None,
    arc_end_fact: bool = False,
) -> bool:
    """Whether ``chapter`` ends an arc.

    ``arc_end_fact=True`` (the Plot Weaver/sync declaring ``arc_end``) always
    wins (Req 4.4, mirrors ainovel ``arc_end_reached``). Else, when an arc map
    is present, the arc's declared last chapter decides; otherwise the legacy
    ``chapter % arc_size == 0`` rule applies (P16 fallback).
    """
    if arc_end_fact:
        return True
    if arc_map is not None and arc_map.arc_for(chapter) is not None:
        return arc_map.is_last_chapter_of_arc(chapter)
    return chapter > 0 and chapter % arc_size == 0


def should_schedule_character_update(
    chapter: int,
    arc_size: int = ARC_SIZE,
    *,
    arc_map: Optional["ArcMap"] = None,
) -> bool:
    """True on every 10th chapter or at an arc boundary (Requirement 8.3)."""
    if chapter <= 0:
        return False
    return (
        chapter % CHARACTER_UPDATE_INTERVAL_CHAPTERS == 0
        or is_arc_boundary(chapter, arc_size, arc_map=arc_map)
    )


def character_update_task_key(chapter: int) -> str:
    return f"chapter.{chapter:04d}.characters"


def chapter_state_barrier_task_key(
    chapter: int,
    arc_size: int = ARC_SIZE,
    *,
    arc_map: Optional["ArcMap"] = None,
) -> str:
    """The task that the *next* chapter's outline must wait on.

    When a character-update barrier is scheduled for ``chapter`` (every 10th
    chapter / arc boundary), the next outline waits on it; otherwise it waits on
    the chapter's sync (Requirement 8.3).
    """
    if should_schedule_character_update(chapter, arc_size, arc_map=arc_map):
        return character_update_task_key(chapter)
    return f"chapter.{chapter:04d}.sync"


def breaker_open(state: dict[str, Any]) -> bool:
    """Whether the circuit breaker is open (ported from control_plane.py)."""
    return (
        state.get("hard_fail_count", 0) >= state.get("max_hard_fail", MAX_HARD_FAIL)
        or state.get("soft_fail_count", 0) >= state.get("max_soft_fail", MAX_SOFT_FAIL)
        or state.get("total_attempts", 0) >= state.get("max_total", MAX_TOTAL)
    )


def score_to_outcome(
    score: Optional[float], verdict: Optional[str] = None
) -> str:
    """Map (score, explicit verdict) → outcome (Requirement 9.1/9.2).

    Explicit verdicts always win over the score threshold. Without a verdict,
    the score bands apply: ≥85 pass, 70-84 soft_fail, <70 hard_fail.
    """
    if verdict in ("pass", "soft_fail", "hard_fail"):
        return "done" if verdict == "pass" else verdict
    if score is None:
        return "hard_fail"
    if score >= REVIEW_PASS_SCORE:
        return "done"
    if score >= REVIEW_SOFT_FAIL_SCORE:
        return "soft_fail"
    return "hard_fail"


def review_gate_passes(score: Optional[float], outcome: Optional[str]) -> bool:
    """Return True only when a review permits sync (ported _review_gate_passes).

    1. Explicit fail outcome (hard_fail | soft_fail) → blocks regardless of score.
    2. Explicit "pass" → allows.
    3. outcome is None → allow only if score ≥ REVIEW_PASS_SCORE.
    """
    if outcome in ("hard_fail", "soft_fail"):
        return False
    if outcome == "pass":
        return True
    return score is not None and score >= REVIEW_PASS_SCORE


# --------------------------------------------------------------------------- #
# DAG construction (ported from control_plane.build_task_specs)
# --------------------------------------------------------------------------- #

_BOOTSTRAP_CANON_INPUTS = (
    "PROJECT_DNA.md",
    SHARED_CANON_TOKEN,
    SHARED_CANON_SECONDARY_TOKEN,
    SHARED_WORLDBUILDING_GUIDE_TOKEN,
)


def _bootstrap_specs(mode: str = "compass") -> list[Task]:
    specs = [
        Task(
            task_key="bootstrap.characters",
            phase="1",
            agent_role="Character Architect",
            command="CREATE_CHARACTERS",
            priority=10,
            input_paths=_BOOTSTRAP_CANON_INPUTS,
            output_paths=("database/characters/",),
            context_query="core protagonist cast relationships flaws wants needs voice",
        ),
        Task(
            task_key="bootstrap.world",
            phase="1",
            agent_role="World Builder",
            command="BUILD_WORLD",
            priority=11,
            input_paths=_BOOTSTRAP_CANON_INPUTS,
            output_paths=("database/worldbuilding/", "database/systems/"),
            context_query="world rules limits factions geography economy systems",
        ),
        Task(
            task_key="bootstrap.plot_threads",
            phase="1",
            agent_role="Plot Weaver",
            command="CREATE_PLOT_THREADS",
            priority=12,
            depends_on=("bootstrap.characters", "bootstrap.world"),
            input_paths=(
                "PROJECT_DNA.md",
                "database/characters/",
                "database/worldbuilding/",
                "database/systems/",
                "GOAL_TRACKER.md",
                SHARED_CANON_TOKEN,
                SHARED_CANON_SECONDARY_TOKEN,
                SHARED_WORLDBUILDING_GUIDE_TOKEN,
            ),
            output_paths=("database/plot_threads/",),
            context_query="plot threads central conflicts unresolved seeds antagonist arcs mystery hooks",
        ),
        Task(
            task_key="bootstrap.timeline",
            phase="1",
            agent_role="Plot Weaver",
            command="CREATE_TIMELINE",
            priority=13,
            depends_on=("bootstrap.plot_threads",),
            input_paths=(
                "PROJECT_DNA.md",
                "database/characters/",
                "database/worldbuilding/",
                "database/systems/",
                "database/plot_threads/",
                "GOAL_TRACKER.md",
                SHARED_CANON_TOKEN,
                SHARED_CANON_SECONDARY_TOKEN,
                SHARED_WORLDBUILDING_GUIDE_TOKEN,
            ),
            output_paths=("database/timeline/",),
            context_query="timeline historical events world chronology character ages faction milestones",
        ),
        Task(
            task_key="bootstrap.master_outline",
            phase="2",
            agent_role="Plot Weaver",
            command="OUTLINE_MASTER",
            priority=20,
            depends_on=("bootstrap.timeline",),
            input_paths=(
                "PROJECT_DNA.md",
                "database/characters/",
                "database/worldbuilding/",
                "database/systems/",
                "database/plot_threads/",
                "database/timeline/",
                "GOAL_TRACKER.md",
                SHARED_WORLDBUILDING_GUIDE_TOKEN,
            ),
            output_paths=("outlines/master_outline.md",),
            context_query="master outline act structure arcs active plot seeds",
        ),
    ]
    if mode == "compass":
        specs.append(
            Task(
                task_key="bootstrap.compass",
                phase="2",
                agent_role="Plot Weaver",
                command="CREATE_COMPASS",
                priority=21,
                depends_on=("bootstrap.master_outline",),
                input_paths=(
                    "PROJECT_DNA.md",
                    "outlines/master_outline.md",
                    "database/characters/",
                    "database/worldbuilding/",
                    "database/systems/",
                    "database/plot_threads/",
                    "database/timeline/",
                    "GOAL_TRACKER.md",
                    SHARED_WORLDBUILDING_GUIDE_TOKEN,
                ),
                output_paths=(
                    "outlines/compass.md",
                    "outlines/layered_outline.json",
                    "outlines/arc_map.json",
                ),
                context_query=(
                    "story compass ending direction long threads scale "
                    "volume arc skeleton"
                ),
            )
        )
    return specs


def build_task_specs(
    start_chapter: int,
    end_chapter: int,
    arc_size: int = ARC_SIZE,
    *,
    mode: str = "compass",
    arc_map: Optional["ArcMap"] = None,
) -> list[Task]:
    """Build the task DAG for chapters ``[start_chapter, end_chapter]``.

    Includes the bootstrap tasks only when ``start_chapter == 1`` (the initial
    seed); rolling-window seeds for later chapters omit them. Dependency edges
    encode Property P1: outline→write→review→sync, and outline.N waits on the
    sync/character barrier of chapter N-1 (or the master outline when N==1).
    """
    specs: list[Task] = []
    if start_chapter <= 1:
        specs.extend(_bootstrap_specs(mode))

    for chapter in range(start_chapter, end_chapter + 1):
        arc = compute_arc(chapter, arc_size, arc_map=arc_map)
        previous_barrier = (
            "bootstrap.master_outline"
            if chapter == 1
            else chapter_state_barrier_task_key(chapter - 1, arc_size, arc_map=arc_map)
        )
        outline_path = f"outlines/arc_{arc}/chapter_{chapter:03d}_outline.md"
        draft_path = f"drafts/chapter_{chapter:04d}.md"
        self_check_path = f"drafts/chapter_{chapter:04d}.check.json"
        chapter_path = f"chapters/chapter_{chapter:03d}.md"
        review_json_path = f"reviews/chapter_{chapter:04d}_review.json"
        review_md_path = f"reviews/chapter_{chapter:04d}_review.md"
        character_snapshot_path = (
            f"memory/character_snapshots/chapter_{chapter:03d}_character_state.md"
        )

        specs.append(
            Task(
                task_key=f"chapter.{chapter:04d}.outline",
                phase="2",
                chapter=chapter,
                arc=arc,
                agent_role="Plot Weaver",
                command="OUTLINE_CHAPTER",
                priority=100 + chapter * 10,
                depends_on=(previous_barrier,),
                input_paths=(
                    "PROJECT_DNA.md",
                    "outlines/master_outline.md",
                    "database/characters/",
                    "database/worldbuilding/",
                    "database/systems/",
                    "database/plot_threads/",
                    "GOAL_TRACKER.md",
                    "memory/Memory.md",
                    SHARED_CANON_TOKEN,
                    SHARED_CANON_SECONDARY_TOKEN,
                    SHARED_WORLDBUILDING_GUIDE_TOKEN,
                ),
                output_paths=(outline_path,),
                context_query=(
                    f"chapter {chapter} next beats active plot threads canon "
                    "limits unresolved seeds"
                ),
            )
        )
        specs.append(
            Task(
                task_key=f"chapter.{chapter:04d}.write",
                phase="3",
                chapter=chapter,
                arc=arc,
                agent_role="Prose Writer",
                command="WRITE_CHAPTER",
                priority=101 + chapter * 10,
                depends_on=(f"chapter.{chapter:04d}.outline",),
                input_paths=(
                    "PROJECT_DNA.md",
                    outline_path,
                    "memory/Memory.md",
                    "style_vault/",
                    SHARED_CANON_TOKEN,
                    SHARED_CANON_SECONDARY_TOKEN,
                    SHARED_WORLDBUILDING_GUIDE_TOKEN,
                ),
                output_paths=(draft_path,),
                context_query=(
                    f"chapter {chapter} outline current character states injuries "
                    "active threads style references"
                ),
            )
        )
        specs.append(
            Task(
                task_key=f"chapter.{chapter:04d}.self_check",
                phase="self_check",
                chapter=chapter,
                arc=arc,
                agent_role="Self Check",
                command="SELF_CHECK_CHAPTER",
                priority=102 + chapter * 10,
                depends_on=(f"chapter.{chapter:04d}.write",),
                input_paths=(
                    "PROJECT_DNA.md",
                    draft_path,
                    outline_path,
                ),
                output_paths=(self_check_path,),
                context_query=(
                    f"deterministic self-check chapter {chapter} draft contract "
                    "beats language format"
                ),
            )
        )
        specs.append(
            Task(
                task_key=f"chapter.{chapter:04d}.review",
                phase="4",
                chapter=chapter,
                arc=arc,
                agent_role="Quality Auditor",
                command="REVIEW_CHAPTER",
                priority=103 + chapter * 10,
                depends_on=(f"chapter.{chapter:04d}.self_check",),
                input_paths=(
                    "PROJECT_DNA.md",
                    draft_path,
                    self_check_path,
                    "database/characters/",
                    "database/worldbuilding/",
                    "database/systems/",
                    "database/timeline/",
                    "database/plot_threads/",
                    "memory/Memory.md",
                    SHARED_CANON_TOKEN,
                    SHARED_CANON_SECONDARY_TOKEN,
                    SHARED_WORLDBUILDING_GUIDE_TOKEN,
                ),
                output_paths=(review_json_path, review_md_path),
                context_query=(
                    f"review chapter {chapter} for canon timeline ooc style and "
                    "unresolved conflicts primary and secondary canon rules"
                ),
            )
        )
        specs.append(
            Task(
                task_key=f"chapter.{chapter:04d}.sync",
                phase="sync",
                chapter=chapter,
                arc=arc,
                agent_role="Lãng Khách",
                command="SYNC_CHAPTER_STATE",
                priority=104 + chapter * 10,
                depends_on=(f"chapter.{chapter:04d}.review",),
                input_paths=(
                    "PROJECT_DNA.md",
                    draft_path,
                    self_check_path,
                    review_json_path,
                    review_md_path,
                    chapter_path,
                    "PLAN.md",
                    "GOAL_TRACKER.md",
                    "memory/Memory.md",
                    "logs/pipeline_status.json",
                    SHARED_WORLDBUILDING_GUIDE_TOKEN,
                ),
                output_paths=(
                    chapter_path,
                    "PLAN.md",
                    "GOAL_TRACKER.md",
                    "memory/Memory.md",
                    "logs/pipeline_status.json",
                ),
                context_query=(
                    f"sync chapter {chapter} plan goals artifacts indexes and long "
                    "term memory"
                ),
            )
        )

        if should_schedule_character_update(chapter, arc_size, arc_map=arc_map):
            specs.append(
                Task(
                    task_key=character_update_task_key(chapter),
                    phase="state",
                    chapter=chapter,
                    arc=arc,
                    agent_role="Character Architect",
                    command="UPDATE_CHARACTERS",
                    priority=105 + chapter * 10,
                    depends_on=(f"chapter.{chapter:04d}.sync",),
                    input_paths=(
                        "PROJECT_DNA.md",
                        chapter_path,
                        review_json_path,
                        review_md_path,
                        "database/characters/",
                        "database/plot_threads/",
                        "database/timeline/",
                        "PLAN.md",
                        "GOAL_TRACKER.md",
                        "memory/Memory.md",
                        SHARED_CANON_TOKEN,
                        SHARED_CANON_SECONDARY_TOKEN,
                        SHARED_WORLDBUILDING_GUIDE_TOKEN,
                    ),
                    output_paths=("database/characters/", character_snapshot_path),
                    context_query=(
                        f"update character state after chapter {chapter}: injuries "
                        "relationships power progression voice shifts debts promises"
                    ),
                )
            )

    return specs


# --------------------------------------------------------------------------- #
# Pipeline state (durable, serialisable; replaces the SQLite control plane)
# --------------------------------------------------------------------------- #


@dataclass
class PipelineState:
    """Durable pipeline state — the session-store payload (replaces SQLite, D2).

    Holds the ordered task table (keyed by ``task_key``), the circuit-breaker
    counters, the seeding metadata (``target_chapters`` / ``arc_size`` / window
    sizes), and the rolling seed log. It is fully serialisable so a Hermes
    session store can persist/restore it and ``resume`` can reconstruct an
    engine from disk.
    """

    schema_version: int = PIPELINE_SCHEMA_VERSION
    state_version: int = 0
    state_digest: str = ""
    novel: str = ""
    tasks: dict[str, Task] = field(default_factory=dict)
    breaker: BreakerState = field(default_factory=BreakerState)
    creative: CreativeState = field(default_factory=CreativeState)
    target_chapters: Optional[int] = None
    arc_size: int = ARC_SIZE
    window_size: int = ROLLING_WINDOW_SIZE
    min_remaining: int = ROLLING_WINDOW_MIN_REMAINING
    last_rolling_seed: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "state_version": self.state_version,
            "novel": self.novel,
            "tasks": [t.to_dict() for t in self.ordered_tasks()],
            "breaker": self.breaker.to_dict(),
            "creative": self.creative.to_dict(),
            "target_chapters": self.target_chapters,
            "arc_size": self.arc_size,
            "window_size": self.window_size,
            "min_remaining": self.min_remaining,
            "last_rolling_seed": self.last_rolling_seed,
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        # Pure serializer: compute the digest into a local rather than writing
        # back to ``self.state_digest``. A ``to_dict`` that mutates ``self`` is a
        # surprising side effect and makes two threads serialising the same state
        # race on the field; the digest is a derived value, not stored state.
        digest = f"sha256:{hashlib.sha256(canonical).hexdigest()}"
        return {**payload, "state_digest": digest}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineState":
        state = cls(
            schema_version=int(data.get("schema_version", PIPELINE_SCHEMA_VERSION)),
            state_version=int(data.get("state_version", 0)),
            state_digest=str(data.get("state_digest") or ""),
            novel=data.get("novel", ""),
            breaker=BreakerState.from_dict(data.get("breaker") or {}),
            creative=CreativeState.from_dict(data.get("creative") or {}),
            target_chapters=data.get("target_chapters"),
            arc_size=int(data.get("arc_size", ARC_SIZE)),
            window_size=int(data.get("window_size", ROLLING_WINDOW_SIZE)),
            min_remaining=int(data.get("min_remaining", ROLLING_WINDOW_MIN_REMAINING)),
            last_rolling_seed=data.get("last_rolling_seed"),
        )
        for raw in data.get("tasks") or []:
            task = Task.from_dict(raw)
            state.tasks[task.task_key] = task
        return state

    # ---- task table helpers ----
    def ordered_tasks(self) -> list[Task]:
        """Tasks in scheduling order: (priority, chapter, insertion)."""
        return sorted(
            self.tasks.values(),
            key=lambda t: (t.priority, t.chapter if t.chapter is not None else -1),
        )

    def add_specs(self, specs: list[Task]) -> int:
        """Insert specs that are not already present. Returns inserted count."""
        inserted = 0
        for spec in specs:
            if spec.task_key not in self.tasks:
                self.tasks[spec.task_key] = replace(spec)
                inserted += 1
        return inserted

    def chapter_numbers(self) -> list[int]:
        return sorted({t.chapter for t in self.tasks.values() if t.chapter is not None})

    def highest_completed_sync(self) -> int:
        """Highest chapter whose sync-phase barrier is done (ported)."""
        synced = [
            t.chapter
            for t in self.tasks.values()
            if t.phase == "sync"
            and t.status == TaskStatus.DONE.value
            and t.chapter is not None
        ]
        return max(synced) if synced else 0


def migrate_state(payload: dict[str, Any]) -> dict[str, Any]:
    """Upgrade a persisted PipelineState payload to the current schema (v2→v3).

    Additive, lossless, and **idempotent** (Property P24):
    ``migrate_state(migrate_state(x)) == migrate_state(x)``. Legacy v2 payloads
    (no compass / arc_map / steer fields) load unchanged in their existing
    ``mode``; the long-form flow is only reached when ``mode == "compass"``.

    ``expanded_through_chapter`` is defaulted to the highest seeded chapter when
    unset, giving a sane baseline for a later opt-in to compass mode without
    changing legacy (full_plan/rolling) behaviour.
    """
    state = PipelineState.from_dict(payload)
    state.schema_version = PIPELINE_SCHEMA_VERSION
    if state.creative.expanded_through_chapter == 0:
        chapters = state.chapter_numbers()
        if chapters:
            state.creative.expanded_through_chapter = max(chapters)
    return state.to_dict()


# --------------------------------------------------------------------------- #
# Engine — the four design interfaces (plan_next / record_result / rolling_seed
# / resume)
# --------------------------------------------------------------------------- #


class PipelineEngine:
    """Stateless-over-``PipelineState`` orchestrator (design §Components #1)."""

    def __init__(self, state: PipelineState):
        self.state = state

    def _touch(self) -> None:
        self.state.state_version += 1
        self.state.state_digest = ""

    # ---- construction helpers ----
    @classmethod
    def create(
        cls,
        *,
        target_chapters: Optional[int] = None,
        arc_size: int = ARC_SIZE,
        novel: str = "",
        initial_window: Optional[int] = None,
        window_size: int = ROLLING_WINDOW_SIZE,
        min_remaining: int = ROLLING_WINDOW_MIN_REMAINING,
        mode: str = "compass",
    ) -> "PipelineEngine":
        """Seed a fresh pipeline.

        ``full_plan``/``rolling``: seeds bootstrap + chapters ``[1,
        initial_window]`` (legacy behaviour). ``compass``: seeds bootstrap only
        (incl. ``bootstrap.compass``); chapters are seeded on demand by arc
        expansion and gated by ``expanded_through_chapter`` (Req 2; P13).
        """
        state = PipelineState(
            state_version=1,
            novel=novel,
            target_chapters=target_chapters,
            arc_size=arc_size,
            window_size=window_size,
            min_remaining=min_remaining,
        )
        state.creative.mode = mode
        if mode == "compass":
            state.add_specs(build_task_specs(1, 0, arc_size, mode=mode))
            return cls(state)
        window = initial_window if initial_window is not None else window_size
        if target_chapters is not None:
            window = min(window, target_chapters)
        if window >= 1:
            state.add_specs(build_task_specs(1, window, arc_size, mode=mode))
        return cls(state)

    # ---- P1 / P12 : plan_next ----
    def dependencies_satisfied(self, task: Task) -> bool:
        """All ``depends_on`` tasks exist and are done (ported, simplified).

        The legacy artifact-provenance / bootstrap-verification checks belong to
        the sync + doctor tools (Task 10); here we model the pure DAG edge: a
        task is ready only when every dependency is ``done``.
        """
        for dep_key in task.depends_on:
            dep = self.state.tasks.get(dep_key)
            if dep is None or dep.status != TaskStatus.DONE.value:
                return False
        return True

    def ready_tasks(self) -> list[Task]:
        if self.state.creative.paused:
            return []
        if self.state.creative.budget_state == "blocked":
            return []
        if self.state.breaker.is_open:
            return []
        ready = []
        for task in self.state.ordered_tasks():
            if task.status not in (
                TaskStatus.PENDING.value,
                TaskStatus.RETRYABLE.value,
            ):
                continue
            if not self._chapter_is_expanded(task):
                continue
            if self.dependencies_satisfied(task):
                ready.append(task)
        return ready

    def _chapter_is_expanded(self, task: Task) -> bool:
        """Compass-mode gating (P13): a chapter task is ready only when its
        chapter has been expanded. Non-compass modes and chapterless tasks are
        always considered expanded (no behaviour change for legacy novels)."""
        if self.state.creative.mode != "compass" or task.chapter is None:
            return True
        return task.chapter <= self.state.creative.expanded_through_chapter

    def advance_expansion(
        self,
        through_chapter: int,
        *,
        arc_size: Optional[int] = None,
        arc_map: Optional["ArcMap"] = None,
    ) -> int:
        """Seed chapter tasks up to ``through_chapter`` and move the expansion
        frontier (Req 2.4). Idempotent: a non-advancing call is a no-op (P14).

        This is the seam the ``arc.*.expand`` stage calls once the Plot Weaver
        has authored the detailed chapter outlines for the next arc.
        """
        arc_size = arc_size or self.state.arc_size
        # Never seed past the target (Req 2): overshooting would leave open
        # tasks beyond the intended end so book_complete could never be reached.
        if self.state.target_chapters is not None:
            through_chapter = min(through_chapter, self.state.target_chapters)
        current = self.state.creative.expanded_through_chapter
        if through_chapter <= current:
            return 0
        start = max(1, current + 1)
        inserted = self.state.add_specs(
            build_task_specs(start, through_chapter, arc_size, mode="compass", arc_map=arc_map)
        )
        self.state.creative.expanded_through_chapter = through_chapter
        self._touch()
        return inserted

    def set_paused(self, paused: bool, *, reason: Optional[str] = None) -> bool:
        """Set step-boundary pause state. Returns True when state changed."""
        if self.state.creative.paused == paused and self.state.creative.pause_reason == reason:
            return False
        self.state.creative.paused = paused
        self.state.creative.pause_reason = reason if paused else None
        self._touch()
        return True

    def recover_breaker(self) -> dict[str, Any]:
        """Clear an open circuit breaker so the pipeline can make progress again.

        When the breaker trips (repeated soft/hard failures), ``record_result``
        parks the failing task as ``BLOCKED`` and ``ready_tasks`` short-circuits
        to ``[]`` — so *no* task is ready and neither ``resume`` (which only
        releases orphaned ``in_progress`` claims) nor ``plan_next`` can make
        progress. Without an explicit reset the run is wedged. This is the
        operator's "try again" valve: it resets the breaker counters, releases
        every ``BLOCKED`` task back to ``retryable`` so the next run re-attempts
        it, and lifts a pause. Returns a small summary for the caller/UI.
        """
        breaker = self.state.breaker
        was_open = breaker.is_open
        breaker.hard_fail_count = 0
        breaker.soft_fail_count = 0
        breaker.total_attempts = 0
        breaker.failure_signature = None
        released = 0
        for task in self.state.tasks.values():
            if task.status == TaskStatus.BLOCKED.value:
                task.status = TaskStatus.RETRYABLE.value
                released += 1
        was_paused = self.state.creative.paused
        self.state.creative.paused = False
        self.state.creative.pause_reason = None
        self.state.creative.stop_block_count = 0
        self._touch()
        next_task = self.plan_next(claim=False)
        return {
            "recovered": was_open or released > 0 or was_paused,
            "breaker_was_open": was_open,
            "released_tasks": released,
            "next_task_key": next_task.task_key if next_task else None,
        }

    def approve_chapter(self, chapter: int) -> dict[str, Any]:
        """Human-approve a chapter stuck at a PRE-SYNC quality gate, then recover.

        ``recover_breaker`` alone only unblocks tasks so they re-run — a chapter
        parked at ``self_check`` (e.g. a repeated-sentence soft-fail) just fails
        again on the unchanged draft, so "Duyệt tay" appeared to do nothing. The
        review-JSON ``human_approved`` flag (written by the service) only lets the
        *sync* gate through; it never reaches ``self_check`` or ``review``, which
        run earlier in the DAG.

        Here we force the not-yet-done PRE-sync gate tasks (``self_check`` and
        ``review``) to DONE so approval covers the stage actually blocking. The
        ``sync`` task is deliberately LEFT to run: sync promotes the draft into
        canon (``chapters/``) — forcing it DONE would "approve" a chapter that was
        never committed. Sync passes on the human-approved review JSON the service
        writes. Each forced gate already wrote its artifact before failing, so
        downstream tasks still have valid inputs. Returns a small summary."""
        pre_sync_gate_phases = {"self_check", "4"}
        approved: list[str] = []
        for task in self.state.tasks.values():
            if (
                task.chapter == chapter
                and task.phase in pre_sync_gate_phases
                and task.status != TaskStatus.DONE.value
            ):
                task.status = TaskStatus.DONE.value
                approved.append(task.task_key)
        recover = self.recover_breaker()
        return {"approved_tasks": approved, "chapter": chapter, "recover": recover}

    def plan_next(self, *, claim: bool = False) -> Optional[Task]:
        """Return the next ready task per the DAG, or ``None``.

        When ``claim`` is True the task is transitioned to ``in_progress`` (the
        legacy claim). Returns ``None`` when the breaker is open or nothing is
        ready (Property P1 / P12).
        """
        ready = self.ready_tasks()
        if not ready:
            return None
        selected = ready[0]
        if claim:
            selected.status = TaskStatus.IN_PROGRESS.value
            self._touch()
        return selected

    # ---- P3 : record_result + circuit breaker ----
    def record_result(
        self,
        task_key: str,
        result: str,
        *,
        score: Optional[float] = None,
        failure_signature: Optional[str] = None,
    ) -> BreakerState:
        """Record a task result and update the circuit breaker (Requirement 10.1).

        ``result`` is one of :data:`RESULT_CHOICES`. The task status is updated
        (done/blocked/retryable) and the scope-aware breaker counters advance.
        """
        if result not in RESULT_CHOICES:
            raise ValueError(f"unknown result {result!r}; expected {RESULT_CHOICES}")
        task = self.state.tasks.get(task_key)
        if task is None:
            raise KeyError(f"unknown task {task_key!r}")

        task.attempt_count += 1
        if score is not None:
            task.score = score

        self._update_breaker(task, result, failure_signature)

        if result in ("done", "skipped"):
            task.status = TaskStatus.DONE.value
        elif result == "blocked":
            task.status = TaskStatus.BLOCKED.value
        else:  # soft_fail / hard_fail
            # A chapter that fails the quality gate at SYNC (score < pass) is
            # sent back through review so critique can revise the draft again —
            # a real rewrite cycle — instead of retrying sync against the same
            # sub-bar review forever (the loop that made "Thử lại" useless).
            if (
                result == "hard_fail"
                and task.phase == "sync"
                and self._recycle_chapter_for_rewrite(task)
            ):
                pass  # recycle scheduled: review+sync reset, breaker streak cleared
            else:
                # Open breaker blocks the task; otherwise it is retryable.
                task.status = (
                    TaskStatus.BLOCKED.value
                    if self.state.breaker.is_open
                    else TaskStatus.RETRYABLE.value
                )
                self._enqueue_review_action(task, result)

        self._touch()
        return self.state.breaker

    def _recycle_chapter_for_rewrite(self, sync_task: Task) -> bool:
        """Send a gate-failed chapter back through review for a real rewrite.

        The sync gate blocks a chapter whose review score is below
        :data:`REVIEW_PASS_SCORE`. Retrying the *sync* task alone is futile: it
        re-reads the same sub-bar review and fails identically, so after
        ``MAX_HARD_FAIL`` repeats the breaker trips and "Thử lại" only clears the
        breaker to hit the same wall. Instead, reset the chapter's ``review`` and
        ``sync`` tasks to ``pending`` so critique re-runs and revises the draft
        (its bounded auto-revise loop is the actual rewrite), then sync re-checks
        the fresh review.

        Bounded by :data:`MAX_REWRITE_CYCLES` cycles per chapter, counted on the
        review task's ``attempt_count`` (which survives serialization and is not
        reset by the breaker). When the budget is spent the chapter is left to
        block so a human can approve it manually. Returns True when a recycle was
        scheduled (caller then skips the normal block/retry path)."""
        chapter = sync_task.chapter
        if chapter is None:
            return False
        review_key = f"chapter.{chapter:04d}.review"
        review_task = self.state.tasks.get(review_key)
        if review_task is None:
            return False
        # The initial review is attempt_count == 1; each extra rewrite cycle adds
        # one more. Allow up to MAX_REWRITE_CYCLES *additional* runs beyond the
        # first, then stop and let the chapter block for manual approval.
        if review_task.attempt_count > MAX_REWRITE_CYCLES:
            return False

        review_task.status = TaskStatus.PENDING.value
        sync_task.status = TaskStatus.PENDING.value
        # Clear the breaker streak so re-running review→sync is not counted as a
        # repeated identical failure (the recycle IS the corrective action).
        breaker = self.state.breaker
        breaker.hard_fail_count = 0
        breaker.soft_fail_count = 0
        breaker.total_attempts = 0
        breaker.failure_signature = None
        return True

    def _enqueue_review_action(self, task: Task, result: str) -> None:
        if task.phase != "4" or task.chapter is None:
            return
        if result == "soft_fail":
            kind = "polish"
            queue = self.state.creative.polish_queue
            priority = 10
        elif result == "hard_fail":
            kind = "rewrite"
            queue = self.state.creative.rewrite_queue
            priority = 20
        else:
            return
        queue_id = f"{kind}_chapter_{task.chapter:04d}_r{task.attempt_count}"
        if any(item.get("queue_id") == queue_id for item in queue):
            return
        queue.append(
            {
                "queue_id": queue_id,
                "kind": kind,
                "chapter": task.chapter,
                "source_review": f"reviews/chapter_{task.chapter:04d}_review.json",
                "reason_codes": [result],
                "priority": priority,
                "attempt": task.attempt_count,
                "max_attempts": 3,
                "status": "pending",
                "created_at": _now_iso(),
            }
        )

    def _update_breaker(
        self, task: Task, result: str, failure_signature: Optional[str]
    ) -> None:
        """Ported from control_plane.update_breaker_state (Requirement 10.1)."""
        state = self.state.breaker
        scope = f"chapter:{task.chapter}" if task.chapter is not None else "bootstrap"

        if state.scope != scope:
            state.hard_fail_count = 0
            state.soft_fail_count = 0
            state.total_attempts = 0
            state.scope = scope
            state.failure_signature = None

        if result in ("done", "skipped", "blocked"):
            state.hard_fail_count = 0
            state.soft_fail_count = 0
            state.total_attempts = 0
            state.failure_signature = None
            return

        # soft_fail / hard_fail — a *new* failure signature resets the streak
        # because the breaker only trips on repeated identical failures.
        if state.failure_signature != failure_signature:
            state.hard_fail_count = 0
            state.soft_fail_count = 0
            state.total_attempts = 0
            state.failure_signature = failure_signature

        if result == "soft_fail":
            state.soft_fail_count += 1
        else:  # hard_fail
            state.hard_fail_count += 1
        state.total_attempts += 1

    # ---- P4 : rolling_seed ----
    def rolling_window_plan(self) -> SeedPlan:
        """Compute the next rolling-window seed (ported rolling_window_plan)."""
        seeded = self.state.chapter_numbers()
        target = self.state.target_chapters
        if not seeded or target is None:
            return SeedPlan(seeded=False, target_chapters=target)

        window = self.state.window_size
        min_remaining = self.state.min_remaining
        max_seeded = max(seeded)
        highest_synced = self.state.highest_completed_sync()
        remaining_window = max_seeded - highest_synced

        if max_seeded >= target or remaining_window >= min_remaining:
            return SeedPlan(
                seeded=False,
                target_chapters=target,
                window_size=window,
                remaining_window=remaining_window,
            )

        start_chapter = max_seeded + 1
        desired_max = min(target, highest_synced + window)
        if desired_max < start_chapter:
            return SeedPlan(
                seeded=False,
                target_chapters=target,
                window_size=window,
                remaining_window=remaining_window,
            )

        return SeedPlan(
            seeded=True,
            start_chapter=start_chapter,
            end_chapter=desired_max,
            arc_size=self.state.arc_size,
            target_chapters=target,
            window_size=window,
            remaining_window=remaining_window,
        )

    def rolling_seed(self) -> SeedPlan:
        """Evaluate and *apply* the rolling-window seed (Requirement 10.3)."""
        plan = self.rolling_window_plan()
        if not plan.seeded:
            return plan
        inserted = self.state.add_specs(
            build_task_specs(plan.start_chapter, plan.end_chapter, plan.arc_size)
        )
        self.state.last_rolling_seed = {
            "chapter_range": [plan.start_chapter, plan.end_chapter],
            "inserted_tasks": inserted,
            "created_at": _now_iso(),
        }
        self._touch()
        return replace(plan, inserted_tasks=inserted)

    # ---- P12 : resume ----
    def resume(self) -> ResumeReport:
        """Resume safely: reset stale in-progress claims and report next task.

        No ``done`` task is ever re-run (its status stays done and it is not
        re-selected). In-progress tasks (orphaned by a crash) are released back
        to ``retryable`` so the next runner can pick them up (Property P12).
        """
        reset = 0
        for task in self.state.tasks.values():
            if task.status == TaskStatus.IN_PROGRESS.value:
                task.status = TaskStatus.RETRYABLE.value
                reset += 1

        if reset:
            self._touch()
        next_task = self.plan_next(claim=False)
        done_count = sum(
            1 for t in self.state.tasks.values() if t.status == TaskStatus.DONE.value
        )
        pending_count = sum(
            1
            for t in self.state.tasks.values()
            if t.status in (TaskStatus.PENDING.value, TaskStatus.RETRYABLE.value)
        )
        return ResumeReport(
            next_task_key=next_task.task_key if next_task else None,
            next_task=next_task,
            done_count=done_count,
            pending_count=pending_count,
            in_progress_reset=reset,
            breaker_open=self.state.breaker.is_open,
        )

    # ---- status snapshot (Task 5.2 — doctor compatibility) ----
    def status_snapshot(self) -> dict[str, Any]:
        """Build a ``logs/pipeline_status.json``-compatible payload.

        Kept structurally identical to the legacy ``PIPELINE_STATUS_TEMPLATE``
        so the existing doctor tooling reads it unchanged (Task 5.2).
        """
        tasks = self.state.ordered_tasks()
        payload: dict[str, Any] = json.loads(json.dumps(PIPELINE_STATUS_TEMPLATE))
        payload["novel"] = self.state.novel
        payload["last_updated"] = _now_iso()
        source_state = self.state.to_dict()
        payload["source_state_version"] = source_state["state_version"]
        payload["source_state_digest"] = source_state["state_digest"]
        payload["circuit_breaker"] = self.state.breaker.to_dict()

        in_progress = next(
            (t for t in tasks if t.status == TaskStatus.IN_PROGRESS.value), None
        )
        blocked = next((t for t in tasks if t.status == TaskStatus.BLOCKED.value), None)
        pending = next(
            (
                t
                for t in tasks
                if t.status in (TaskStatus.PENDING.value, TaskStatus.RETRYABLE.value)
            ),
            None,
        )
        current = blocked or in_progress or pending
        payload["current_phase"] = current.phase if current else None
        payload["current_chapter"] = current.chapter if current else None
        payload["current_arc"] = current.arc if current else None
        payload["active_agents"] = sorted(
            {t.agent_role for t in tasks if t.status == TaskStatus.IN_PROGRESS.value}
        )

        if blocked or self.state.breaker.is_open:
            payload["status"] = "blocked"
        elif in_progress:
            payload["status"] = "running"
        elif pending:
            payload["status"] = "queued"
        elif not tasks:
            payload["status"] = "idle"
        else:
            payload["status"] = "completed"

        scores = [t.score for t in tasks if t.phase == "4" and t.score is not None]
        payload["stats"]["total_chapters_written"] = sum(
            1 for t in tasks if t.phase == "3" and t.status == TaskStatus.DONE.value
        )
        payload["stats"]["total_chapters_passed"] = sum(
            1
            for t in tasks
            if t.phase == "4"
            and t.status == TaskStatus.DONE.value
            and (t.score or 0) >= REVIEW_PASS_SCORE
        )
        payload["stats"]["average_score"] = (
            round(sum(scores) / len(scores), 2) if scores else None
        )
        payload["stats"]["total_retries"] = sum(
            max(t.attempt_count - 1, 0) for t in tasks
        )
        # Escalations = number of tasks that exhausted retries into a blocked
        # state, a cumulative count rather than the breaker's current 0/1 open
        # flag (which reported at most one and reset when the breaker closed).
        payload["stats"]["escalations"] = sum(
            1 for t in tasks if t.status == TaskStatus.BLOCKED.value
        )
        payload["chapter_history"] = [
            {
                "chapter": t.chapter,
                "phase": t.phase,
                "status": t.status,
                "score": t.score,
                "task_key": t.task_key,
            }
            for t in tasks
            if t.chapter is not None and t.status == TaskStatus.DONE.value
        ][-CHAPTER_HISTORY_LIMIT:]
        return payload

    def write_status_snapshot(self, novel_path: "str | Path") -> Path:
        """Persist the status snapshot to ``<novel>/logs/pipeline_status.json``."""
        path = Path(novel_path) / PIPELINE_STATUS_REL_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.status_snapshot(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path


# --------------------------------------------------------------------------- #
# Tool entrypoint + self-registration (Requirement 6.2)
# --------------------------------------------------------------------------- #

_PIPELINE_TOOL_SCHEMA = {
    "name": "novelkit_pipeline",
    "description": (
        "Pipeline DAG & orchestration: plan the next ready task, record task "
        "results (circuit breaker), seed the rolling window, and resume safely."
    ),
    "input": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["plan_next", "record_result", "rolling_seed", "resume"],
            },
            "state": {"type": "object", "description": "Serialised PipelineState"},
            "task_key": {"type": "string"},
            "result": {"type": "string", "enum": list(RESULT_CHOICES)},
            "score": {"type": ["number", "null"]},
            "failure_signature": {"type": ["string", "null"]},
            "claim": {"type": "boolean"},
        },
        "required": ["action", "state"],
    },
    "output": {
        "type": "object",
        "properties": {
            "result": {"type": "object"},
            "state": {"type": "object", "description": "Updated PipelineState"},
        },
        "required": ["state"],
    },
}


def pipeline_tool(
    action: str,
    state: dict[str, Any],
    *,
    task_key: Optional[str] = None,
    result: Optional[str] = None,
    score: Optional[float] = None,
    failure_signature: Optional[str] = None,
    claim: bool = False,
    chapter: Optional[int] = None,
) -> dict[str, Any]:
    """Stateless tool entrypoint: ``(action, state) -> {result, state}``.

    The pipeline state is passed in and returned out so a Hermes session store
    owns persistence (no hidden SQLite, finding D2). Idempotent for read actions
    (``plan_next``/``resume`` with ``claim=False``).
    """
    engine = PipelineEngine(PipelineState.from_dict(state))

    if action == "plan_next":
        task = engine.plan_next(claim=claim)
        out: Any = task.to_dict() if task else None
    elif action == "record_result":
        if task_key is None or result is None:
            raise ValueError("record_result requires task_key and result")
        out = engine.record_result(
            task_key,
            result,
            score=score,
            failure_signature=failure_signature,
        ).to_dict()
    elif action == "rolling_seed":
        out = engine.rolling_seed().to_dict()
    elif action == "resume":
        out = engine.resume().to_dict()
    elif action == "recover":
        out = engine.recover_breaker()
    elif action == "approve_chapter":
        if chapter is None:
            raise ValueError("approve_chapter requires chapter")
        out = engine.approve_chapter(int(chapter))
    else:
        raise ValueError(
            f"unknown action {action!r}; expected "
            "plan_next|record_result|rolling_seed|resume|recover|approve_chapter"
        )

    return {"result": out, "state": engine.state.to_dict()}


# Self-register at import time (Requirement 6.2 — self-registering tool).
registry.register(
    "novelkit_pipeline",
    pipeline_tool,
    schema=_PIPELINE_TOOL_SCHEMA,
    module=__name__,
)
