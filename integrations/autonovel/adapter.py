"""AutoNovel integration adapter — splice NovelKit's pipeline into AutoNovel's loop.

Phase 5 of the migration (Task 12.1). Resolved Decision #1 (requirements §5)
makes AutoNovel the **starting framework**: NovelKit must *reuse* AutoNovel's
existing chapter-writing loop and merely **extend/configure** it with creative
tools, rather than running a parallel pipeline (Requirement 7.2).

There is no AutoNovel package vendored in this repo, so this module defines the
clean **integration seam** that a real AutoNovel loop would plug into:

- :class:`AutoNovelLoop` — an abstract model of AutoNovel's chapter-writing loop.
  Its stages (worldbuild → outline → draft → critique → synchronise) are the
  generic AutoNovel loop steps. A real deployment subclasses it and routes each
  stage to AutoNovel's own generators.
- :class:`AutoNovelAdapter` — the driver. It owns a NovelKit
  :class:`~tools.novelkit_pipeline_tool.PipelineEngine` and uses its
  ``plan_next`` / ``record_result`` interface as the **scheduler** for the
  AutoNovel loop. NovelKit therefore *configures* AutoNovel's loop (what to
  write next, in what order, with which dependencies, behind the circuit
  breaker) instead of duplicating the loop. This is the "extend, don't
  parallel" contract made concrete.
- :class:`InMemoryAutoNovelLoop` — a concrete reference implementation that
  materialises plausible artifacts into a workspace so the seam is testable end
  to end (drive a sample novel bootstrap → 1 chapter), and that **reuses** the
  real ``novelkit_dna`` (bootstrap docs) and ``novelkit_sync`` (commit + doctor)
  tools for the bootstrap and synchronise stages.

The artifact-layout reconciliation (Task 12.2) lives in :mod:`.layout`; the
workspace below is NovelKit-native on disk (the NovelKit tools require that
layout) and exposes the AutoNovel path *view* through that mapping.

Design references: design.md §"Migration Strategy" Phase 5, §Architecture
(runtime diagram); requirements.md Requirement 7.
"""

from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

_LOG = logging.getLogger("novelkit.autonovel.adapter")

from tools.novelkit_pipeline_tool import (
    ARC_SIZE,
    PipelineEngine,
    Task,
)
from tools.novelkit_pipeline_state_store import PipelineStateStore
from tools.novelkit_rules_tool import current_rules_digest

from .layout import LAYOUT, ArtifactLayoutMap, to_autonovel


# --------------------------------------------------------------------------- #
# Loop stages — the generic AutoNovel chapter-writing loop vocabulary
# --------------------------------------------------------------------------- #


class LoopStage(str, Enum):
    """The stages of a generic AutoNovel-style chapter-writing loop.

    NovelKit's pipeline phases map *onto* these stages — that is the whole point
    of the integration: NovelKit does not introduce a second loop, it drives
    AutoNovel's stages in the order its DAG dictates.
    """

    WORLDBUILD = "worldbuild"   # NovelKit bootstrap.* + character-state updates
    OUTLINE = "outline"         # NovelKit outline / master_outline
    DRAFT = "draft"             # NovelKit write
    SELF_CHECK = "self_check"    # NovelKit deterministic draft check
    CRITIQUE = "critique"       # NovelKit review
    SYNCHRONISE = "synchronise"  # NovelKit sync
    # Long-form GA (compass mode)
    COMPASS = "compass"             # NovelKit bootstrap.compass (story compass)
    ARC_SUMMARY = "arc_summary"      # arc-boundary summary
    VOLUME_SUMMARY = "volume_summary"  # volume-boundary summary


#: NovelKit pipeline phase → AutoNovel loop stage. Phases come from
#: ``build_task_specs`` ("1" bootstrap, "2" outline, "3" write, "4" review,
#: "sync", "state" character-update barrier).
_PHASE_TO_STAGE: dict[str, LoopStage] = {
    "1": LoopStage.WORLDBUILD,
    "2": LoopStage.OUTLINE,
    "3": LoopStage.DRAFT,
    "self_check": LoopStage.SELF_CHECK,
    "4": LoopStage.CRITIQUE,
    "sync": LoopStage.SYNCHRONISE,
    "state": LoopStage.WORLDBUILD,
}

_STAGE_TO_CHECKPOINT_STEP: dict[LoopStage, str] = {
    LoopStage.WORLDBUILD: "plan_completed",
    LoopStage.OUTLINE: "plan_completed",
    LoopStage.DRAFT: "draft_completed",
    LoopStage.SELF_CHECK: "self_check_completed",
    LoopStage.CRITIQUE: "review_completed",
    LoopStage.SYNCHRONISE: "sync_completed",
    LoopStage.COMPASS: "compass_updated",
    LoopStage.ARC_SUMMARY: "arc_summary_written",
    LoopStage.VOLUME_SUMMARY: "volume_summary_written",
}


def stage_for_task(task: Task) -> LoopStage:
    """Map a NovelKit :class:`Task` onto an AutoNovel loop stage."""
    if task.command == "CREATE_COMPASS":
        return LoopStage.COMPASS  # bootstrap.compass shares phase "2" with outlines
    try:
        return _PHASE_TO_STAGE[task.phase]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(
            f"task {task.task_key!r} has phase {task.phase!r} with no AutoNovel "
            "loop stage mapping"
        ) from exc


# --------------------------------------------------------------------------- #
# Step + result data models
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LoopStep:
    """A single unit of work handed to AutoNovel's loop, derived from a Task.

    It carries everything AutoNovel's loop needs to do the creative work for one
    pipeline task, but nothing about scheduling — ordering belongs to NovelKit's
    pipeline engine.
    """

    task_key: str
    stage: LoopStage
    phase: str
    command: str
    agent_role: str
    chapter: Optional[int]
    arc: Optional[int]
    input_paths: tuple[str, ...]
    output_paths: tuple[str, ...]
    context_query: Optional[str]

    @classmethod
    def from_task(cls, task: Task) -> "LoopStep":
        return cls(
            task_key=task.task_key,
            stage=stage_for_task(task),
            phase=task.phase,
            command=task.command,
            agent_role=task.agent_role,
            chapter=task.chapter,
            arc=task.arc,
            input_paths=tuple(task.input_paths),
            output_paths=tuple(task.output_paths),
            context_query=task.context_query,
        )

    def autonovel_outputs(self) -> tuple[str, ...]:
        """The step's output paths expressed in the AutoNovel workspace layout."""
        return tuple(to_autonovel(p) for p in self.output_paths)


@dataclass
class StepResult:
    """The outcome AutoNovel's loop reports back for a step.

    ``outcome`` is fed straight into the pipeline's ``record_result`` (it is one
    of the pipeline ``RESULT_CHOICES``); ``score`` feeds the review gate.
    """

    outcome: str = "done"
    score: Optional[float] = None
    artifacts: list[str] = field(default_factory=list)
    failure_signature: Optional[str] = None
    notes: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "score": self.score,
            "artifacts": list(self.artifacts),
            "failure_signature": self.failure_signature,
            "notes": self.notes,
            "details": self.details,
        }


# --------------------------------------------------------------------------- #
# Workspace — NovelKit-native on disk, AutoNovel view via the layout map
# --------------------------------------------------------------------------- #


@dataclass
class AutoNovelWorkspace:
    """A novel workspace shared by NovelKit tools and AutoNovel's loop.

    On disk the workspace is **NovelKit-native** (the NovelKit tools read/write
    that fixed layout). The AutoNovel *view* of any artifact is obtained through
    the :mod:`.layout` bijection, so an AutoNovel loop can address artifacts in
    its own vocabulary while the bytes live in one place (Task 12.2).
    """

    root: Path
    layout: ArtifactLayoutMap = field(default_factory=lambda: LAYOUT)

    def __post_init__(self) -> None:
        self.root = Path(self.root)

    # ---- path resolution ----
    def resolve(self, novelkit_rel: str) -> Path:
        """Absolute on-disk path for a NovelKit-relative artifact path."""
        return self.root / novelkit_rel

    def autonovel_rel(self, novelkit_rel: str) -> str:
        """The AutoNovel-layout name for a NovelKit-relative artifact path."""
        return self.layout.to_autonovel(novelkit_rel)

    def resolve_autonovel(self, autonovel_rel: str) -> Path:
        """Absolute on-disk path for an AutoNovel-relative artifact path."""
        return self.root / self.layout.to_novelkit(autonovel_rel)

    # ---- io helpers ----
    def write(self, novelkit_rel: str, text: str) -> Path:
        path = self.resolve(novelkit_rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def read(self, novelkit_rel: str) -> str:
        return self.resolve(novelkit_rel).read_text(encoding="utf-8")

    def exists(self, novelkit_rel: str) -> bool:
        return self.resolve(novelkit_rel).exists()


# --------------------------------------------------------------------------- #
# The AutoNovel loop interface
# --------------------------------------------------------------------------- #


class AutoNovelLoop(ABC):
    """Abstract model of AutoNovel's existing chapter-writing loop.

    A real integration subclasses this and routes each stage to AutoNovel's own
    generators/agents. NovelKit never re-implements these stages — it only
    *schedules* them (via the pipeline engine) and *augments* them with creative
    tools. :meth:`run_stage` is the single dispatch entrypoint the adapter calls.
    """

    def prepare(self, workspace: AutoNovelWorkspace) -> None:
        """Hook before the run begins (default: no-op)."""

    def run_stage(
        self, stage: LoopStage, step: LoopStep, workspace: AutoNovelWorkspace
    ) -> StepResult:
        """Dispatch a step to the matching stage handler."""
        handler = {
            LoopStage.WORLDBUILD: self.worldbuild,
            LoopStage.OUTLINE: self.outline,
            LoopStage.DRAFT: self.draft,
            LoopStage.SELF_CHECK: self.self_check,
            LoopStage.CRITIQUE: self.critique,
            LoopStage.SYNCHRONISE: self.synchronise,
            LoopStage.COMPASS: self.compass,
            LoopStage.ARC_SUMMARY: self.arc_summary,
            LoopStage.VOLUME_SUMMARY: self.volume_summary,
        }[stage]
        return handler(step, workspace)

    @abstractmethod
    def worldbuild(self, step: LoopStep, workspace: AutoNovelWorkspace) -> StepResult:
        """Bootstrap / character-state stage (codex)."""

    @abstractmethod
    def outline(self, step: LoopStep, workspace: AutoNovelWorkspace) -> StepResult:
        """Outline stage (beats)."""

    @abstractmethod
    def draft(self, step: LoopStep, workspace: AutoNovelWorkspace) -> StepResult:
        """Draft / prose stage (manuscript)."""

    @abstractmethod
    def self_check(self, step: LoopStep, workspace: AutoNovelWorkspace) -> StepResult:
        """Deterministic draft self-check stage."""

    @abstractmethod
    def critique(self, step: LoopStep, workspace: AutoNovelWorkspace) -> StepResult:
        """Review / critique stage."""

    @abstractmethod
    def synchronise(self, step: LoopStep, workspace: AutoNovelWorkspace) -> StepResult:
        """Synchronise / commit stage."""

    # ---- long-form GA stages (non-abstract defaults so existing loops that
    # predate compass mode keep working without changes) ----

    def compass(self, step: LoopStep, workspace: AutoNovelWorkspace) -> StepResult:
        """Author the Story Compass + an initial skeleton arc map (Req 1, 2).

        Default impl writes a minimal compass + one skeleton arc so the
        compass-mode flow can proceed; a real loop overrides this to author the
        full Thiên Mệnh Thư and the volume/arc skeleton.
        """
        from tools.novelkit_compass_tool import update_compass, upsert_arc

        update_compass(
            workspace.root,
            ending_direction="(auto — cập nhật ở ranh giới Cuốn)",
            active_long_threads=[],
            scale_estimate={},
            current_volume_id="vol_001",
            current_arc_id="arc_001",
        )
        upsert_arc(
            workspace.root,
            {"arc_id": "arc_001", "start_chapter": None, "end_chapter": None,
             "estimated_chapters": 8, "arc_type": "growth_breakthrough",
             "status": "skeleton", "volume_id": "vol_001"},
        )
        return StepResult(
            outcome="done",
            artifacts=["outlines/compass.md", "outlines/arc_map.json"],
        )

    def arc_summary(self, step: LoopStep, workspace: AutoNovelWorkspace) -> StepResult:
        """Write the arc-boundary summary artifact (Req 3)."""
        written: list[str] = []
        for rel in step.output_paths:
            workspace.write(
                rel,
                f"# Tóm tắt Hồi\n\nTóm tắt diễn biến tới chương {step.chapter}.\n",
            )
            written.append(rel)
        return StepResult(outcome="done", artifacts=written)

    def volume_summary(self, step: LoopStep, workspace: AutoNovelWorkspace) -> StepResult:
        """Write the volume-boundary summary artifact (Req 3)."""
        written: list[str] = []
        for rel in step.output_paths:
            workspace.write(rel, f"# Tóm tắt Cuốn\n\nTới chương {step.chapter}.\n")
            written.append(rel)
        return StepResult(outcome="done", artifacts=written)


# --------------------------------------------------------------------------- #
# Run report
# --------------------------------------------------------------------------- #


@dataclass
class RunReport:
    """Summary of an adapter-driven run."""

    steps: list[dict[str, Any]] = field(default_factory=list)
    tasks_completed: int = 0
    chapters_drafted: int = 0
    chapters_synced: int = 0
    blocked: bool = False
    breaker_open: bool = False
    final_status: Optional[str] = None
    stopped_reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps": self.steps,
            "tasks_completed": self.tasks_completed,
            "chapters_drafted": self.chapters_drafted,
            "chapters_synced": self.chapters_synced,
            "blocked": self.blocked,
            "breaker_open": self.breaker_open,
            "final_status": self.final_status,
            "stopped_reason": self.stopped_reason,
        }


# --------------------------------------------------------------------------- #
# The adapter — drives the AutoNovel loop via the pipeline tool
# --------------------------------------------------------------------------- #


class AutoNovelAdapter:
    """Drive an :class:`AutoNovelLoop` with a NovelKit :class:`PipelineEngine`.

    The adapter is the splice point: it repeatedly asks the pipeline for the
    next ready task (``plan_next``), hands it to AutoNovel's loop as a
    :class:`LoopStep`, then records the loop's outcome back into the pipeline
    (``record_result``). The pipeline owns ordering, dependencies, the circuit
    breaker and the rolling window; AutoNovel's loop owns the creative work.
    """

    def __init__(
        self,
        engine: PipelineEngine,
        loop: AutoNovelLoop,
        workspace: AutoNovelWorkspace,
        *,
        state_store: Optional[PipelineStateStore] = None,
    ):
        self.engine = engine
        self.loop = loop
        self.workspace = workspace
        self.state_store = state_store or PipelineStateStore(workspace.root)

    @classmethod
    def create(
        cls,
        *,
        workspace: AutoNovelWorkspace,
        loop: AutoNovelLoop,
        target_chapters: int,
        arc_size: int = ARC_SIZE,
        novel: str = "",
        state_store: Optional[PipelineStateStore] = None,
        mode: str = "compass",
    ) -> "AutoNovelAdapter":
        """Build an adapter with a freshly seeded pipeline for ``target_chapters``.

        ``mode="compass"`` seeds bootstrap (incl. ``bootstrap.compass``) only;
        chapters are unlocked on demand by arc expansion at boundaries.
        """
        engine = PipelineEngine.create(
            target_chapters=target_chapters,
            arc_size=arc_size,
            novel=novel or workspace.root.name,
            initial_window=None if mode == "compass" else target_chapters,
            mode=mode,
        )
        return cls(engine, loop, workspace, state_store=state_store)

    def _persist_boundary_state(self, *, expected_version: Optional[int] = None) -> None:
        self.state_store.save(self.engine.state, expected_version=expected_version)

    def _checkpoint_step(
        self,
        step: LoopStep,
        result: StepResult,
        *,
        input_digest: str,
    ) -> None:
        artifacts: list[str] = []
        for rel in result.artifacts:
            path = self.workspace.resolve(rel)
            if path.is_file():
                artifacts.append(rel)
        self.state_store.append_checkpoint(
            task_key=step.task_key,
            step=_STAGE_TO_CHECKPOINT_STEP[step.stage],
            state=self.engine.state,
            input_digest=input_digest,
            artifacts=artifacts,
        )

    # ---- long-form GA: compass boundary maintenance (Req 1, 2, 3, 6) ----

    def _compass_post_step(self, step: LoopStep, result: StepResult) -> None:
        """Post-step hooks. Minor-cast roster runs in any mode (flag-gated); the
        compass boundary maintenance (expand arc-1 after the compass is authored,
        arc/volume summaries + expansion at boundaries) runs in compass mode."""
        if result.outcome != "done":
            return
        # Minor-cast roster: any mode, on a completed sync (flag-gated internally).
        if step.stage is LoopStage.SYNCHRONISE and step.chapter is not None:
            self._commit_minor_cast(step.chapter)
        if self.engine.state.creative.mode != "compass":
            return
        if step.stage is LoopStage.COMPASS:
            self._compass_expand_next()
        elif step.stage is LoopStage.SYNCHRONISE and step.chapter is not None:
            self._compass_boundary_after_sync(step.chapter)

    def _compass_expand_next(self) -> Optional[int]:
        """Place the next skeleton arc on the timeline + advance the expansion
        frontier so its chapters become ready (Req 2; checkpoint ``arc_expanded``)."""
        from tools.novelkit_compass_tool import read_arc_map, upsert_arc

        arc_map = read_arc_map(self.workspace.root)
        skeleton = next((a for a in arc_map.arcs if a.status == "skeleton"), None)
        if skeleton is None:
            return None
        start = self.engine.state.creative.expanded_through_chapter + 1
        end = start + max(1, skeleton.estimated_chapters) - 1
        upsert_arc(
            self.workspace.root,
            {**skeleton.to_dict(), "start_chapter": start, "end_chapter": end,
             "status": "detailed"},
        )
        before = self.engine.state.state_version
        self.engine.advance_expansion(end)
        self._persist_boundary_state(expected_version=before)
        self.state_store.append_checkpoint(
            task_key=f"arc.{skeleton.arc_id}.expand",
            step="arc_expanded",
            state=self.engine.state,
            input_digest=self.engine.state.to_dict()["state_digest"],
            artifacts=[],
        )
        return end

    def _compass_boundary_after_sync(self, chapter: int) -> None:
        from tools.novelkit_compass_tool import boundary_check, read_arc_map, upsert_arc

        bc = boundary_check(self.workspace.root, chapter)
        if not bc.get("at_arc_end"):
            return
        arc_id = bc.get("arc_id")
        summary_rel = f"summaries/arc_{arc_id}.md"
        summary_step = LoopStep(
            task_key=f"arc.{arc_id}.summary", stage=LoopStage.ARC_SUMMARY,
            phase="arc_summary", command="SUMMARISE_ARC",
            agent_role="Quality Auditor", chapter=chapter, arc=None,
            input_paths=(), output_paths=(summary_rel,), context_query=None,
        )
        res = self.loop.arc_summary(summary_step, self.workspace)
        arts = [r for r in res.artifacts if self.workspace.resolve(r).is_file()]
        self.state_store.append_checkpoint(
            task_key=summary_step.task_key, step="arc_summary_written",
            state=self.engine.state,
            input_digest=self.engine.state.to_dict()["state_digest"], artifacts=arts,
        )
        arc_map = read_arc_map(self.workspace.root)
        arc = next((a for a in arc_map.arcs if a.arc_id == arc_id), None)
        if arc is not None:
            upsert_arc(self.workspace.root, {**arc.to_dict(), "status": "done"})
        if bc.get("at_volume_end") and bc.get("volume_id"):
            self._compass_volume_boundary(str(bc["volume_id"]), chapter)
        self._compass_expand_next()
        # Boundary maintenance wrote canon (arc_summary, arc_map status, and at a
        # volume end the volume_summary + refreshed compass.md) AFTER the sync
        # that reindexed. Without a reindex here the derivative RAG index is left
        # stale against those files, so a run that ends exactly on an arc/volume
        # boundary makes `doctor` report a blocking `rag_index_stale`. Refresh the
        # index so the health check stays clean. Derivative-only (never canon),
        # best-effort so boundary upkeep never fails on an index hiccup.
        try:
            from tools.novelkit_sync_tool import reindex

            reindex(self.workspace.root)
        except Exception:  # noqa: BLE001 — index refresh is best-effort
            _LOG.warning(
                "compass: post-boundary reindex failed at chapter %d; "
                "run `doctor`/reindex to refresh the retrieval index",
                chapter, exc_info=True,
            )

    def _compass_volume_boundary(self, volume_id: str, chapter: int) -> None:
        """At a volume's last arc: write the volume summary + refresh the compass
        (Req 1.4, 3.2). Advances ``current_volume_id`` to the next volume."""
        from tools.novelkit_compass_tool import read_compass, update_compass

        summary_rel = f"summaries/volume_{volume_id}.md"
        vstep = LoopStep(
            task_key=f"volume.{volume_id}.summary", stage=LoopStage.VOLUME_SUMMARY,
            phase="volume_summary", command="SUMMARISE_VOLUME",
            agent_role="Quality Auditor", chapter=chapter, arc=None,
            input_paths=(), output_paths=(summary_rel,), context_query=None,
        )
        res = self.loop.volume_summary(vstep, self.workspace)
        arts = [r for r in res.artifacts if self.workspace.resolve(r).is_file()]
        self.state_store.append_checkpoint(
            task_key=vstep.task_key, step="volume_summary_written",
            state=self.engine.state,
            input_digest=self.engine.state.to_dict()["state_digest"], artifacts=arts,
        )
        try:
            n = int(volume_id.split("_")[-1])
            next_vol = f"vol_{n + 1:03d}"
        except (ValueError, IndexError):
            next_vol = volume_id
        compass = read_compass(self.workspace.root) or {}
        update_compass(
            self.workspace.root,
            ending_direction=compass.get("ending_direction", ""),
            active_long_threads=compass.get("active_long_threads", []),
            scale_estimate=compass.get("scale_estimate", {}),
            current_volume_id=next_vol,
            current_arc_id=compass.get("current_arc_id"),
        )
        # Advance the in-memory volume pointer, then persist it. The compass
        # file was just written with next_vol; without this save the durable
        # pipeline state would still point at the old volume, so a crash here
        # would leave state and compass disagreeing on current_volume_id.
        self.engine.state.creative.current_volume_id = next_vol
        self._persist_boundary_state()
        self.state_store.append_checkpoint(
            task_key=f"volume.{volume_id}.compass", step="compass_updated",
            state=self.engine.state,
            input_digest=self.engine.state.to_dict()["state_digest"],
            artifacts=["outlines/compass.md"],
        )

    def _commit_minor_cast(self, chapter: int) -> None:
        """Promote declared ``cast_intros`` (sidecar) into the minor-cast roster
        and bump appearance counts for known names present in the chapter
        (Req 6). Flag-gated — a no-op unless ``minor_cast`` is enabled."""
        try:
            from tools.novelkit_longform_config import flag_enabled

            if not flag_enabled("minor_cast", self.workspace.root):
                return
            from plugins.memory.novelkit_memory import get_provider, recent_cast
        except Exception:  # noqa: BLE001 — never break sync on optional wiring
            _LOG.debug(
                "minor_cast wiring unavailable for chapter %d; skipping roster bump",
                chapter, exc_info=True,
            )
            return
        root = self.workspace.root
        facts: list[dict] = []
        sidecar = root / "drafts" / f"chapter_{chapter:04d}.cast.json"
        if sidecar.is_file():
            try:
                for intro in json.loads(sidecar.read_text("utf-8")) or []:
                    name = (intro or {}).get("name")
                    if not name:
                        continue
                    facts.append({
                        "category": "minor_cast", "subject": name, "field": "profile",
                        "value": intro.get("brief_role", "") or name,
                        "payload": {"brief_role": intro.get("brief_role", ""),
                                    "first_seen": chapter, "last_seen": chapter,
                                    "appearance_count": 1},
                    })
            except (OSError, ValueError):
                pass
        chapter_file = root / "chapters" / f"chapter_{chapter:03d}.md"
        if chapter_file.is_file():
            text = chapter_file.read_text("utf-8")
            for item in recent_cast(root):
                # Idempotent per chapter: only bump when this chapter is newer
                # than the last recorded appearance (avoids double-count on
                # a re-sync / retry of the same chapter).
                if item.subject and item.subject in text and (
                    (item.payload.get("last_seen") or 0) < chapter
                ):
                    facts.append({
                        "category": "minor_cast", "subject": item.subject,
                        "field": "profile", "value": item.value,
                        "payload": {"last_seen": chapter,
                                    "appearance_count": (item.payload.get("appearance_count") or 0) + 1},
                    })
        if facts:
            get_provider().commit_episodic(
                scope=root, memory_facts=facts, chapter=chapter,
                commit_id=f"cast_{chapter}",
            )

    def run(
        self,
        *,
        max_steps: Optional[int] = None,
        max_chapters: Optional[int] = None,
    ) -> RunReport:
        """Drive the loop until no task is ready (or a budget is reached).

        Each iteration: claim the next ready task → run the matching AutoNovel
        stage → record the result → refresh the doctor-compatible status
        snapshot. Stops when the pipeline has nothing ready (done or breaker
        open), the step budget is exhausted, or — when ``max_chapters`` is set —
        that many chapters have finished syncing this run. ``max_chapters`` lets
        callers ask for "write N more chapters" without knowing how many
        retries/rewrites each chapter will cost; ``max_steps`` still acts as a
        hard safety ceiling so a stuck chapter can never loop forever.
        """
        report = RunReport()
        self.loop.prepare(self.workspace)

        while True:
            if max_steps is not None and len(report.steps) >= max_steps:
                report.stopped_reason = "max_steps"
                break
            if max_chapters is not None and report.chapters_synced >= max_chapters:
                report.stopped_reason = "max_chapters"
                break

            before_claim_version = self.engine.state.state_version
            task = self.engine.plan_next(claim=True)
            if task is None:
                report.stopped_reason = (
                    "breaker_open" if self.engine.state.breaker.is_open else "drained"
                )
                break
            self._persist_boundary_state(expected_version=before_claim_version)
            step_input_digest = self.engine.state.to_dict()["state_digest"]

            step = LoopStep.from_task(task)
            result = self.loop.run_stage(step.stage, step, self.workspace)
            before_result_version = self.engine.state.state_version
            self.engine.record_result(
                task.task_key,
                result.outcome,
                score=result.score,
                failure_signature=result.failure_signature,
            )

            self._persist_boundary_state(expected_version=before_result_version)
            self._checkpoint_step(step, result, input_digest=step_input_digest)
            self._compass_post_step(step, result)

            if result.outcome == "done":
                report.tasks_completed += 1
                if step.stage is LoopStage.DRAFT:
                    report.chapters_drafted += 1
                if step.stage is LoopStage.SYNCHRONISE:
                    report.chapters_synced += 1
            if result.outcome in ("hard_fail", "soft_fail", "blocked"):
                report.blocked = True

            report.steps.append(
                {
                    "task_key": step.task_key,
                    "stage": step.stage.value,
                    "phase": step.phase,
                    "chapter": step.chapter,
                    "outcome": result.outcome,
                    "score": result.score,
                    "artifacts": list(result.artifacts),
                }
            )

        report.breaker_open = self.engine.state.breaker.is_open
        report.final_status = self.engine.status_snapshot().get("status")
        return report

    def step(self) -> Optional[dict[str, Any]]:
        """Run exactly ONE ready task (claim → stage → record). 

        Returns the step dict, or ``None`` when nothing is ready (the caller may
        then seed the next window and retry). Enables realtime, per-step driving
        from the web surface instead of one long blocking run.
        """
        before_claim_version = self.engine.state.state_version
        task = self.engine.plan_next(claim=True)
        if task is None:
            return None
        self._persist_boundary_state(expected_version=before_claim_version)
        step_input_digest = self.engine.state.to_dict()["state_digest"]
        step = LoopStep.from_task(task)
        result = self.loop.run_stage(step.stage, step, self.workspace)
        before_result_version = self.engine.state.state_version
        self.engine.record_result(
            task.task_key,
            result.outcome,
            score=result.score,
            failure_signature=result.failure_signature,
        )
        self._persist_boundary_state(expected_version=before_result_version)
        self._checkpoint_step(step, result, input_digest=step_input_digest)
        self._compass_post_step(step, result)
        return {
            "task_key": step.task_key,
            "stage": step.stage.value,
            "phase": step.phase,
            "chapter": step.chapter,
            "outcome": result.outcome,
            "score": result.score,
            "artifacts": list(result.artifacts),
        }


# --------------------------------------------------------------------------- #
# Reference in-memory loop — concrete, testable, reuses the real tools
# --------------------------------------------------------------------------- #


_REFERENCE_CHAPTER = (
    "Hắn dừng chân trước cánh cổng đá phủ rêu, hơi thở còn vương mùi tuyết tan.\n\n"
    "Phía sau, tiếng bước chân quen thuộc chậm lại. Hắn không quay đầu, chỉ siết "
    "chặt thanh kiếm cũ, nhớ về lời hứa năm xưa chưa kịp trả.\n\n"
    "Gió lùa qua khe cửa, mang theo tiếng chuông xa vọng. Một chương mới của núi "
    "sông bắt đầu, và hắn biết mình không còn đường lui."
)

#: Review verdict bands — must match the canonical gate thresholds
#: (REVIEW_PASS_SCORE=85; REVIEW_SOFT_FAIL_SCORE=70). >=85 PASS, 70-84
#: SOFT-FAIL, <70 HARD-FAIL. The reviewer writes a verdict consistent with the
#: score it emits, so the real sync gate (which parses the review FILE, not the
#: StepResult) sees a coherent (score, verdict) pair.
def _verdict_for_score(score: Optional[float]) -> str:
    """The review verdict label consistent with ``score`` (gate-aligned)."""
    if score is None:
        return "HARD-FAIL"
    if score >= 85:
        return "PASS"
    if score >= 70:
        return "SOFT-FAIL"
    return "HARD-FAIL"


def _format_score(score: float) -> str:
    """Render a score as an integer when whole, else with its fractional part."""
    return str(int(score)) if float(score).is_integer() else str(score)


def _render_review(score: Optional[float]) -> str:
    """Render a review document whose score + verdict reflect ``score``.

    The body is parsed by the real sync gate (``parse_review_file``), so the
    labelled total and the ``Trạng thái`` verdict must agree with ``score``.
    Only the labelled total is emitted (no full 7-criterion table) so the gate
    reads exactly the score the reviewer reported, with no rubric divergence.
    """
    verdict = _verdict_for_score(score)
    score_line = (
        f"**Điểm:** {_format_score(score)}/100" if score is not None else "**Điểm:** N/A"
    )
    return f"# Review\n\n**Trạng thái:** {verdict}\n\n{score_line}\n"


#: The reference loop's default passing review (score 91 → PASS).
_REFERENCE_REVIEW = _render_review(91.0)


class InMemoryAutoNovelLoop(AutoNovelLoop):
    """A self-contained AutoNovel loop that materialises real artifacts.

    It writes plausible content for every stage so the full pipeline can run
    bootstrap → 1 chapter against the real NovelKit tools. The worldbuild
    bootstrap reuses ``novelkit_dna.bootstrap_docs`` and the synchronise stage
    reuses ``novelkit_sync.commit`` — demonstrating that NovelKit *extends*
    AutoNovel's loop with its tools rather than re-implementing them.
    """

    def __init__(
        self,
        *,
        dna_text: Optional[str] = None,
        review_score: float = 91.0,
        use_real_sync: bool = True,
    ):
        self.dna_text = dna_text or (
            "---\n"
            "title: Demo Novel\n"
            "genre: xianxia\n"
            "sub_agents_squad: khoa_huyen\n"
            "target_chapters: 1\n"
            "---\n\n# Demo Novel\n\nMột câu chuyện tu tiên thử nghiệm.\n"
        )
        self.review_score = review_score
        self.use_real_sync = use_real_sync

    # ---- preparation: PROJECT_DNA + planning docs (reuse novelkit_dna) ----
    def prepare(self, workspace: AutoNovelWorkspace) -> None:
        if not workspace.exists("PROJECT_DNA.md"):
            workspace.write("PROJECT_DNA.md", self.dna_text)
        from tools.novelkit_dna_tool import bootstrap_docs

        bootstrap_docs(str(workspace.root))

    # ---- stages ----
    def compass(self, step: LoopStep, workspace: AutoNovelWorkspace) -> StepResult:
        from tools.novelkit_compass_tool import update_compass, upsert_arc

        update_compass(
            workspace.root,
            ending_direction="MC đạt đỉnh tu luyện; trả xong nợ nhân quả",
            active_long_threads=[{"id": "T-001", "name": "thân thế", "status": "open"}],
            scale_estimate={"volumes": 1, "arcs": 2, "chapters": 16},
            current_volume_id="vol_001", current_arc_id="arc_001",
        )
        for aid in ("arc_001", "arc_002"):
            upsert_arc(workspace.root, {
                "arc_id": aid, "start_chapter": None, "end_chapter": None,
                "estimated_chapters": 8, "arc_type": "growth_breakthrough",
                "status": "skeleton", "volume_id": "vol_001",
            })
        return StepResult(
            outcome="done",
            artifacts=["outlines/compass.md", "outlines/arc_map.json"],
        )

    def worldbuild(self, step: LoopStep, workspace: AutoNovelWorkspace) -> StepResult:
        artifacts = self._materialise_outputs(
            step,
            workspace,
            file_body=f"# {step.command}\n\nGenerated by AutoNovel worldbuild stage.\n",
            dir_stub_name="index.md",
        )
        return StepResult(outcome="done", artifacts=artifacts)

    def outline(self, step: LoopStep, workspace: AutoNovelWorkspace) -> StepResult:
        ch = step.chapter
        title = f"Chapter {ch} outline" if ch else "Master outline"
        artifacts = self._materialise_outputs(
            step,
            workspace,
            file_body=f"# {title}\n\n- Beat 1\n- Beat 2\n- Beat 3\n",
            dir_stub_name="outline.md",
        )
        return StepResult(outcome="done", artifacts=artifacts)

    def draft(self, step: LoopStep, workspace: AutoNovelWorkspace) -> StepResult:
        artifacts = self._materialise_outputs(
            step, workspace, file_body=_REFERENCE_CHAPTER, dir_stub_name="draft.md"
        )
        return StepResult(outcome="done", artifacts=artifacts)

    def self_check(self, step: LoopStep, workspace: AutoNovelWorkspace) -> StepResult:
        draft_rel = f"drafts/chapter_{step.chapter:04d}.md" if step.chapter else None
        draft_text = workspace.read(draft_rel) if draft_rel and workspace.exists(draft_rel) else ""
        payload = {
            "schema_version": 1,
            "chapter": step.chapter,
            "attempt": 1,
            "rules_digest": current_rules_digest(workspace.root),
            "checks": {
                "word_range": "met" if draft_text.strip() else "missed",
                "required_beats": "met",
                "required_contracts": "met",
                "forbidden_outcomes": "met",
                "language_guard": "met",
                "format_integrity": "met" if draft_text.strip() else "missed",
            },
            "misses": [] if draft_text.strip() else ["empty_draft"],
            "warnings": [],
            "draft_sha256": hashlib.sha256(draft_text.encode("utf-8")).hexdigest(),
        }
        artifacts = self._materialise_outputs(
            step,
            workspace,
            file_body=json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            dir_stub_name="check.json",
        )
        return StepResult(
            outcome="done" if draft_text.strip() else "hard_fail",
            artifacts=artifacts,
            failure_signature=None if draft_text.strip() else "self_check_empty_draft",
        )

    def critique(self, step: LoopStep, workspace: AutoNovelWorkspace) -> StepResult:
        # Render the review FILE from this loop's configured score so the real
        # sync gate (which parses the file, not the StepResult) sees a coherent
        # (score, verdict) pair — a low score writes a HARD-FAIL/SOFT-FAIL review
        # that the gate then blocks on.
        from tools.novelkit_gate_tool import derive_typed_review

        chapter = step.chapter or 0
        draft_rel = f"drafts/chapter_{chapter:04d}.md"
        draft_text = workspace.read(draft_rel) if workspace.exists(draft_rel) else ""
        draft_sha = hashlib.sha256(draft_text.encode("utf-8")).hexdigest()
        score = max(0, min(100, int(round(self.review_score))))
        dimensions = {
            "plot_progression": score,
            "character_consistency": score,
            "continuity": score,
            "prose_quality": score,
            "dialogue_voice": score,
            "world_consistency": score,
            "reader_momentum": score,
        }
        review_json = derive_typed_review(
            review_id=f"chapter_{chapter:04d}_attempt_01",
            chapter=chapter,
            attempt=1,
            draft_sha256=draft_sha,
            dimensions=dimensions,
            rules_digest=current_rules_digest(workspace.root),
            reviewer_model_fingerprint="in_memory:test",
        )
        artifacts: list[str] = []
        for rel in step.output_paths:
            if rel.endswith(".json"):
                workspace.write(
                    rel,
                    json.dumps(review_json, ensure_ascii=False, indent=2) + "\n",
                )
            else:
                workspace.write(rel, _render_review(self.review_score))
            artifacts.append(rel)
        return StepResult(
            outcome="done", score=self.review_score, artifacts=artifacts
        )

    def synchronise(self, step: LoopStep, workspace: AutoNovelWorkspace) -> StepResult:
        if not self.use_real_sync or step.chapter is None:
            return StepResult(outcome="done", score=self.review_score)

        # Reuse the real NovelKit sync tool (review gate → ledger → reindex →
        # episodic → doctor → provenance). This is the "extend AutoNovel's loop
        # with NovelKit tools" contract in action.
        from tools.novelkit_sync_tool import commit as sync_commit

        sync_report = sync_commit(
            workspace.root,
            step.chapter,
            arc=step.arc,
            pipeline_state=None,
        )
        outcome = "done"
        if sync_report.blocked:
            outcome = "hard_fail" if not sync_report.gate_passed else "blocked"
        return StepResult(
            outcome=outcome,
            score=sync_report.gate_score,
            artifacts=list(sync_report.updated_docs),
            failure_signature=(None if outcome == "done" else "sync_blocked"),
            details={"sync": sync_report.to_dict()},
        )

    # ---- helpers ----
    @staticmethod
    def _materialise_outputs(
        step: LoopStep,
        workspace: AutoNovelWorkspace,
        *,
        file_body: str,
        dir_stub_name: str,
    ) -> list[str]:
        """Write each declared output path; directory outputs get a stub file."""
        written: list[str] = []
        for rel in step.output_paths:
            if rel.endswith("/"):
                target = f"{rel}{dir_stub_name}"
            else:
                target = rel
            workspace.write(target, file_body)
            written.append(target)
        return written


__all__ = [
    "LoopStage",
    "LoopStep",
    "StepResult",
    "AutoNovelWorkspace",
    "AutoNovelLoop",
    "AutoNovelAdapter",
    "InMemoryAutoNovelLoop",
    "RunReport",
    "stage_for_task",
]
