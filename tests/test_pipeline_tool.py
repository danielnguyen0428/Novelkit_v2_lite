"""Tests for the pipeline DAG & orchestration tool (Task 5, Requirements 8/10/19).

Property-based tests cover the four headline correctness properties from
design.md §"Correctness Properties":

- **P1 — DAG ordering**: ``chapter.N.write`` is never ready before
  ``chapter.N.outline`` is done; self-check after write; review after
  self-check; sync after review;
  ``chapter.N.outline`` after ``chapter.N-1`` barrier (N>1).
  **Validates: Requirements 8.2**
- **P3 — Circuit breaker bound**: within a scope the breaker opens only once a
  bound is hit (hard≤2, soft≤3, total≤5) and resets on scope change.
  **Validates: Requirements 10.1**
- **P4 — Rolling window invariant**: after every sync,
  ``0 ≤ max_seeded − highest_synced ≤ WINDOW`` and the buffer ≥ MIN_REMAINING
  while the target is not yet reached.
  **Validates: Requirements 10.3**
- **P12 — Resume safety**: after resume no ``done`` task runs again and the next
  ready task is correct per the DAG.
  **Validates: Requirements 19.3**
  **Validates: Requirements 7.2**

Plus unit tests for the DAG builder, breaker reset semantics, the score→outcome
table, the output-contract integration (Task 5.3), the status snapshot
(Task 5.2), self-registration, and round-trip serialisation.
"""

from __future__ import annotations

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from tools import registry
from tools.novelkit_pipeline_tool import (
    ARC_SIZE,
    MAX_HARD_FAIL,
    MAX_REWRITE_CYCLES,
    MAX_SOFT_FAIL,
    MAX_TOTAL,
    REVIEW_PASS_SCORE,
    REVIEW_SOFT_FAIL_SCORE,
    ROLLING_WINDOW_MIN_REMAINING,
    ROLLING_WINDOW_SIZE,
    BreakerState,
    CreativeState,
    PipelineEngine,
    PipelineState,
    Task,
    TaskStatus,
    breaker_open,
    build_task_specs,
    compute_arc,
    pipeline_tool,
    review_gate_passes,
    score_to_outcome,
    should_schedule_character_update,
)
from tools.task_output_contracts import OutputContract


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _drive_to_done(engine: PipelineEngine, task_key: str) -> None:
    """Mark a task done via record_result (so the breaker stays consistent)."""
    engine.record_result(task_key, "done", score=REVIEW_PASS_SCORE)


def _complete_chapter(engine: PipelineEngine, chapter: int) -> None:
    """Drive a chapter through outline→write→self_check→review→sync."""
    for suffix in ("outline", "write", "self_check", "review", "sync"):
        _drive_to_done(engine, f"chapter.{chapter:04d}.{suffix}")
    char_key = f"chapter.{chapter:04d}.characters"
    if char_key in engine.state.tasks:
        _drive_to_done(engine, char_key)


def _complete_bootstrap(engine: PipelineEngine) -> None:
    for key in (
        "bootstrap.characters",
        "bootstrap.world",
        "bootstrap.plot_threads",
        "bootstrap.timeline",
        "bootstrap.master_outline",
    ):
        if key in engine.state.tasks:
            _drive_to_done(engine, key)


# --------------------------------------------------------------------------- #
# Property 1 — DAG ordering
# --------------------------------------------------------------------------- #


@settings(max_examples=200)
@given(
    target=st.integers(min_value=1, max_value=40),
    arc_size=st.sampled_from([3, 5, 10, 50]),
)
def test_property_dag_dependency_edges_enforce_phase_order(target, arc_size):
    """P1: dependency edges encode outline→write→self-check→review→sync and
    outline.N after the chapter N-1 barrier.

    **Validates: Requirements 8.2**
    """
    specs = {t.task_key: t for t in build_task_specs(1, target, arc_size)}

    for chapter in range(1, target + 1):
        write = specs[f"chapter.{chapter:04d}.write"]
        self_check = specs[f"chapter.{chapter:04d}.self_check"]
        review = specs[f"chapter.{chapter:04d}.review"]
        sync = specs[f"chapter.{chapter:04d}.sync"]

        assert f"chapter.{chapter:04d}.outline" in write.depends_on
        assert f"chapter.{chapter:04d}.write" in self_check.depends_on
        assert f"chapter.{chapter:04d}.self_check" in review.depends_on
        assert f"chapter.{chapter:04d}.review" in sync.depends_on

        outline = specs[f"chapter.{chapter:04d}.outline"]
        if chapter == 1:
            assert outline.depends_on == ("bootstrap.master_outline",)
        else:
            prev = chapter - 1
            expected = (
                f"chapter.{prev:04d}.characters"
                if should_schedule_character_update(prev, arc_size)
                else f"chapter.{prev:04d}.sync"
            )
            assert outline.depends_on == (expected,)
            # The barrier task must actually exist in the DAG.
            assert expected in specs


@settings(max_examples=150)
@given(
    target=st.integers(min_value=2, max_value=20),
    arc_size=st.sampled_from([5, 10, 50]),
)
def test_property_write_never_ready_before_outline_done(target, arc_size):
    """P1: walking the DAG via plan_next, a chapter's write/self-check/review/sync
    is never selected before its predecessor phase is done.

    **Validates: Requirements 8.2**
    """
    engine = PipelineEngine.create(target_chapters=target, arc_size=arc_size)
    # Seed the full range up front so ordering (not seeding) is under test.
    engine.state.add_specs(build_task_specs(1, target, arc_size))
    engine.state.creative.expanded_through_chapter = target

    guard = 0
    max_steps = len(engine.state.tasks) + 5
    while guard < max_steps:
        guard += 1
        task = engine.plan_next(claim=False)
        if task is None:
            break
        # Every dependency of a ready task must already be done.
        for dep_key in task.depends_on:
            dep = engine.state.tasks[dep_key]
            assert dep.status == TaskStatus.DONE.value, (
                f"{task.task_key} ready while dep {dep_key} is {dep.status}"
            )
        engine.record_result(task.task_key, "done", score=REVIEW_PASS_SCORE)

    # All tasks completed → nothing left ready.
    assert engine.plan_next() is None
    assert all(t.status == TaskStatus.DONE.value for t in engine.state.tasks.values())


# --------------------------------------------------------------------------- #
# Property 3 — Circuit breaker bound
# --------------------------------------------------------------------------- #


@settings(max_examples=200)
@given(results=st.lists(st.sampled_from(["soft_fail", "hard_fail"]), min_size=1, max_size=12))
def test_property_breaker_bounded_within_scope(results):
    """P3: feeding same-signature failures, counts never exceed the bounds and
    the breaker opens exactly when a bound is hit.

    **Validates: Requirements 10.1**
    """
    engine = PipelineEngine.create(target_chapters=5, arc_size=50, mode="full_plan")
    # A single chapter scope: drive the review task repeatedly.
    _complete_bootstrap(engine)
    _drive_to_done(engine, "chapter.0001.outline")
    _drive_to_done(engine, "chapter.0001.write")
    review_key = "chapter.0001.review"

    for result in results:
        state = engine.record_result(
            review_key, result, failure_signature="quality:fixed_sig"
        )
        # Counts always stay within their bounds.
        assert state.hard_fail_count <= MAX_HARD_FAIL
        assert state.soft_fail_count <= MAX_SOFT_FAIL
        assert state.total_attempts <= MAX_TOTAL
        # breaker_open iff a bound has been reached.
        opened = (
            state.hard_fail_count >= MAX_HARD_FAIL
            or state.soft_fail_count >= MAX_SOFT_FAIL
            or state.total_attempts >= MAX_TOTAL
        )
        assert state.is_open == opened
        if state.is_open:
            # Once open, the pipeline stops handing out work.
            assert engine.plan_next() is None
            break


@settings(max_examples=200)
@given(
    fails_a=st.integers(min_value=1, max_value=2),
    fails_b=st.integers(min_value=1, max_value=2),
)
def test_property_breaker_resets_on_scope_change(fails_a, fails_b):
    """P3: changing scope (different chapter) resets the breaker counters.

    **Validates: Requirements 10.1**
    """
    engine = PipelineEngine.create(target_chapters=10, arc_size=50)
    engine.state.add_specs(build_task_specs(1, 10, 50))

    # Fail chapter 1's review a few times (scope chapter:1).
    for _ in range(fails_a):
        engine.record_result("chapter.0001.review", "hard_fail", failure_signature="s1")
    assert engine.state.breaker.scope == "chapter:1"

    # A result on a different chapter switches scope and resets counters.
    state = engine.record_result(
        "chapter.0002.review", "soft_fail", failure_signature="s2"
    )
    assert state.scope == "chapter:2"
    assert state.hard_fail_count == 0  # carried-over hard fails were reset
    assert state.soft_fail_count == 1  # only the new scope's fail counts
    assert state.total_attempts == 1


def test_breaker_resets_on_signature_change_within_scope():
    """A new failure signature within the same scope restarts the streak."""
    engine = PipelineEngine.create(target_chapters=3, arc_size=50)
    engine.state.add_specs(build_task_specs(1, 3, 50))
    engine.record_result("chapter.0001.review", "hard_fail", failure_signature="A")
    state = engine.record_result(
        "chapter.0001.review", "hard_fail", failure_signature="B"
    )
    # Different signature → counters reset then incremented once.
    assert state.hard_fail_count == 1
    assert state.total_attempts == 1
    assert not state.is_open


def test_breaker_resets_on_success():
    engine = PipelineEngine.create(target_chapters=3, arc_size=50)
    engine.state.add_specs(build_task_specs(1, 3, 50))
    engine.record_result("chapter.0001.review", "hard_fail", failure_signature="A")
    state = engine.record_result("chapter.0001.review", "done", score=90)
    assert state.hard_fail_count == 0
    assert state.total_attempts == 0
    assert state.failure_signature is None


# --------------------------------------------------------------------------- #
# Property 4 — Rolling window invariant
# --------------------------------------------------------------------------- #


@settings(max_examples=150)
@given(
    target=st.integers(min_value=6, max_value=60),
    arc_size=st.sampled_from([10, 50]),
)
def test_property_rolling_window_invariant(target, arc_size):
    """P4: after every sync + rolling_seed, the buffer ahead of the last synced
    chapter stays within [0, WINDOW] and ≥ MIN_REMAINING until the target.

    **Validates: Requirements 10.3**
    """
    engine = PipelineEngine.create(
        target_chapters=target,
        arc_size=arc_size,
        initial_window=ROLLING_WINDOW_SIZE,
        mode="full_plan",
    )
    _complete_bootstrap(engine)

    def check_invariant():
        seeded = engine.state.chapter_numbers()
        max_seeded = max(seeded)
        highest_synced = engine.state.highest_completed_sync()
        remaining = max_seeded - highest_synced
        assert 0 <= remaining <= ROLLING_WINDOW_SIZE, (
            f"buffer {remaining} out of [0, {ROLLING_WINDOW_SIZE}]"
        )
        if max_seeded < target:
            assert remaining >= ROLLING_WINDOW_MIN_REMAINING, (
                f"buffer {remaining} below MIN_REMAINING while target not reached"
            )

    check_invariant()

    guard = 0
    while engine.state.highest_completed_sync() < target and guard < target + 10:
        guard += 1
        highest = engine.state.highest_completed_sync()
        chapter = highest + 1
        if f"chapter.{chapter:04d}.sync" not in engine.state.tasks:
            engine.rolling_seed()
            check_invariant()
            continue
        _complete_chapter(engine, chapter)
        engine.rolling_seed()
        check_invariant()

    assert engine.state.highest_completed_sync() == target


def test_rolling_seed_stops_at_target():
    engine = PipelineEngine.create(
        target_chapters=4, arc_size=50, initial_window=5, mode="full_plan"
    )
    # target 4 < window 5 → only chapters 1-4 seeded, never more.
    assert engine.state.chapter_numbers() == [1, 2, 3, 4]
    plan = engine.rolling_seed()
    assert plan.seeded is False
    assert engine.state.chapter_numbers() == [1, 2, 3, 4]


def test_rolling_seed_no_target_is_noop():
    engine = PipelineEngine.create(target_chapters=None, arc_size=50)
    assert engine.rolling_seed().seeded is False


# --------------------------------------------------------------------------- #
# Property 12 — Resume safety
# --------------------------------------------------------------------------- #


@settings(max_examples=150)
@given(
    target=st.integers(min_value=2, max_value=15),
    completed=st.integers(min_value=0, max_value=8),
)
def test_property_resume_does_not_rerun_done_tasks(target, completed):
    """P12: after a serialise/restore round-trip, resume never re-runs a done
    task and returns the correct next ready task per the DAG.

    **Validates: Requirements 19.3**
    **Validates: Requirements 7.2**
    """
    completed = min(completed, target)
    engine = PipelineEngine.create(target_chapters=target, arc_size=50)
    engine.state.add_specs(build_task_specs(1, target, 50))
    _complete_bootstrap(engine)
    for chapter in range(1, completed + 1):
        _complete_chapter(engine, chapter)

    done_before = {
        t.task_key for t in engine.state.tasks.values() if t.status == TaskStatus.DONE.value
    }
    # Simulate a crash mid-flight: claim the next task (in_progress) then drop.
    in_flight = engine.plan_next(claim=True)

    # Round-trip through the session store (serialise → restore).
    restored = PipelineEngine(PipelineState.from_dict(engine.state.to_dict()))
    report = restored.resume()

    # No done task lost its status or got re-selected.
    done_after = {
        t.task_key
        for t in restored.state.tasks.values()
        if t.status == TaskStatus.DONE.value
    }
    assert done_before <= done_after
    assert report.next_task_key not in done_before
    if report.next_task is not None:
        assert report.next_task.status != TaskStatus.DONE.value
        # The resumed task is genuinely ready (all deps done).
        for dep_key in report.next_task.depends_on:
            assert restored.state.tasks[dep_key].status == TaskStatus.DONE.value
    # The orphaned in-progress task was released, not lost.
    if in_flight is not None:
        assert report.in_progress_reset >= 1
        assert (
            restored.state.tasks[in_flight.task_key].status
            != TaskStatus.IN_PROGRESS.value
        )


def test_resume_returns_first_task_on_fresh_pipeline():
    engine = PipelineEngine.create(target_chapters=3, arc_size=50)
    report = engine.resume()
    assert report.next_task_key == "bootstrap.characters"
    assert report.done_count == 0
    assert report.in_progress_reset == 0


# --------------------------------------------------------------------------- #
# Unit tests — DAG builder
# --------------------------------------------------------------------------- #


def test_bootstrap_only_seeded_for_first_window():
    with_bootstrap = build_task_specs(1, 3, 50)
    keys = {t.task_key for t in with_bootstrap}
    assert "bootstrap.characters" in keys
    assert "bootstrap.master_outline" in keys

    later = build_task_specs(6, 10, 50)
    later_keys = {t.task_key for t in later}
    assert not any(k.startswith("bootstrap.") for k in later_keys)


def test_character_barrier_scheduled_on_tenth_chapter():
    specs = {t.task_key for t in build_task_specs(1, 10, 50)}
    assert "chapter.0010.characters" in specs
    assert "chapter.0005.characters" not in specs  # not arc boundary at arc_size 50


def test_character_barrier_on_arc_boundary():
    specs = {t.task_key for t in build_task_specs(1, 6, 3)}
    # arc_size 3 → chapter 3 and 6 are arc boundaries.
    assert "chapter.0003.characters" in specs
    assert "chapter.0006.characters" in specs


def test_compute_arc():
    assert compute_arc(1, 50) == 1
    assert compute_arc(50, 50) == 1
    assert compute_arc(51, 50) == 2


def test_should_schedule_character_update():
    assert should_schedule_character_update(10, 50) is True
    assert should_schedule_character_update(50, 50) is True
    assert should_schedule_character_update(7, 50) is False
    assert should_schedule_character_update(0, 50) is False


# --------------------------------------------------------------------------- #
# Unit tests — score/outcome + gate
# --------------------------------------------------------------------------- #


def test_score_to_outcome_bands():
    assert score_to_outcome(90) == "done"
    assert score_to_outcome(REVIEW_PASS_SCORE) == "done"
    assert score_to_outcome(75) == "soft_fail"
    assert score_to_outcome(REVIEW_SOFT_FAIL_SCORE) == "soft_fail"
    assert score_to_outcome(50) == "hard_fail"
    assert score_to_outcome(None) == "hard_fail"


def test_score_to_outcome_verdict_overrides_score():
    assert score_to_outcome(50, verdict="pass") == "done"
    assert score_to_outcome(99, verdict="hard_fail") == "hard_fail"
    assert score_to_outcome(99, verdict="soft_fail") == "soft_fail"


def test_review_gate_passes():
    assert review_gate_passes(90, None) is True
    assert review_gate_passes(84, None) is False
    assert review_gate_passes(99, "soft_fail") is False  # explicit fail wins
    assert review_gate_passes(10, "pass") is True  # explicit pass wins
    assert review_gate_passes(None, None) is False


def test_breaker_open_helper():
    assert breaker_open({"hard_fail_count": 2, "max_hard_fail": 2}) is True
    assert breaker_open({"soft_fail_count": 3, "max_soft_fail": 3}) is True
    assert breaker_open({"total_attempts": 5, "max_total": 5}) is True
    assert breaker_open({"hard_fail_count": 1, "soft_fail_count": 2, "total_attempts": 3}) is False


# --------------------------------------------------------------------------- #
# Unit tests — output contract integration (Task 5.3 / D7)
# --------------------------------------------------------------------------- #


def test_task_output_contract_for_bootstrap():
    specs = {t.task_key: t for t in build_task_specs(1, 1, 50)}
    contract = specs["bootstrap.world"].output_contract()
    assert isinstance(contract, OutputContract)
    assert "database/worldbuilding/WorldOverview.md" in contract.required_paths


def test_task_output_contract_for_chapter_derives_from_outputs():
    specs = {t.task_key: t for t in build_task_specs(1, 1, 50)}
    write = specs["chapter.0001.write"]
    contract = write.output_contract()
    assert write.output_paths == ("drafts/chapter_0001.md",)
    assert contract.required_paths == write.output_paths
    assert contract.writable_paths == write.output_paths

    self_check = specs["chapter.0001.self_check"]
    assert self_check.input_paths == (
        "PROJECT_DNA.md",
        "drafts/chapter_0001.md",
        "outlines/arc_1/chapter_001_outline.md",
    )
    assert self_check.output_paths == ("drafts/chapter_0001.check.json",)

    review = specs["chapter.0001.review"]
    assert "drafts/chapter_0001.check.json" in review.input_paths
    assert review.output_paths == (
        "reviews/chapter_0001_review.json",
        "reviews/chapter_0001_review.md",
    )


# --------------------------------------------------------------------------- #
# Unit tests — status snapshot (Task 5.2) + serialisation
# --------------------------------------------------------------------------- #


def test_status_snapshot_compatible_shape():
    engine = PipelineEngine.create(target_chapters=3, arc_size=50, novel="demo")
    snap = engine.status_snapshot()
    # Doctor-compatible keys present.
    for key in ("circuit_breaker", "stats", "chapter_history", "status", "novel"):
        assert key in snap
    assert snap["novel"] == "demo"
    assert snap["status"] == "queued"
    cb = snap["circuit_breaker"]
    assert cb["max_hard_fail"] == MAX_HARD_FAIL
    assert cb["max_soft_fail"] == MAX_SOFT_FAIL
    assert cb["max_total"] == MAX_TOTAL


def test_status_snapshot_carries_source_state_identity():
    engine = PipelineEngine.create(target_chapters=3, arc_size=50, novel="demo")
    state_payload = engine.state.to_dict()

    snap = engine.status_snapshot()

    assert snap["source_state_version"] == state_payload["state_version"]
    assert snap["source_state_digest"] == state_payload["state_digest"]


def test_status_snapshot_blocked_when_breaker_open():
    engine = PipelineEngine.create(target_chapters=3, arc_size=50)
    engine.state.add_specs(build_task_specs(1, 3, 50))
    for _ in range(MAX_HARD_FAIL):
        engine.record_result("chapter.0001.review", "hard_fail", failure_signature="x")
    assert engine.state.breaker.is_open
    assert engine.status_snapshot()["status"] == "blocked"


def test_write_status_snapshot_to_disk(tmp_path):
    engine = PipelineEngine.create(target_chapters=2, arc_size=50, novel="n")
    out = engine.write_status_snapshot(tmp_path)
    assert out.exists()
    assert out.name == "pipeline_status.json"
    assert out.parent.name == "logs"


def test_pipeline_state_roundtrip():
    engine = PipelineEngine.create(target_chapters=5, arc_size=50, mode="full_plan")
    _complete_bootstrap(engine)
    engine.record_result("chapter.0001.outline", "soft_fail", failure_signature="z")
    restored = PipelineState.from_dict(engine.state.to_dict())
    assert set(restored.tasks) == set(engine.state.tasks)
    assert restored.breaker.to_dict() == engine.state.breaker.to_dict()
    assert restored.target_chapters == 5


def test_pipeline_state_v2_serialization_has_stable_digest():
    engine = PipelineEngine.create(target_chapters=2, arc_size=50, novel="demo")

    first = engine.state.to_dict()
    second = engine.state.to_dict()

    assert first["schema_version"] == 3
    assert first["state_version"] == 1
    assert first["state_digest"].startswith("sha256:")
    assert len(first["state_digest"].removeprefix("sha256:")) == 64
    assert second == first


def test_pipeline_state_serializes_creative_state_defaults_and_queues():
    engine = PipelineEngine.create(
        target_chapters=2, arc_size=50, novel="demo", mode="full_plan"
    )
    engine.state.creative.rewrite_queue.append(
        {
            "queue_id": "rewrite_chapter_0001_r1",
            "kind": "rewrite",
            "chapter": 1,
            "source_review": "reviews/chapter_0001_review.json",
            "reason_codes": ["continuity_critical"],
            "priority": 20,
            "attempt": 1,
            "max_attempts": 3,
            "status": "pending",
            "created_at": "2026-06-29T08:00:00Z",
        }
    )
    engine.state.creative.paused = True
    engine.state.creative.pause_reason = "user_review"

    payload = engine.state.to_dict()
    restored = PipelineState.from_dict(payload)

    assert payload["creative"]["mode"] == "full_plan"
    assert payload["creative"]["budget_state"] == "ok"
    assert payload["creative"]["rewrite_queue"][0]["status"] == "pending"
    assert restored.creative.paused is True
    assert restored.creative.pause_reason == "user_review"


def test_budget_blocked_state_stops_new_task_planning():
    engine = PipelineEngine.create(target_chapters=1, arc_size=50, novel="demo")
    engine.state.creative.budget_state = "blocked"

    assert engine.ready_tasks() == []
    assert engine.plan_next(claim=True) is None


def test_creative_state_rejects_invalid_mode():
    state = CreativeState(mode="parallel")

    try:
        state.to_dict()
    except ValueError as exc:
        assert "mode" in str(exc)
    else:
        raise AssertionError("invalid creative mode should fail")


def test_claiming_task_increments_state_version_once():
    engine = PipelineEngine.create(target_chapters=2, arc_size=50)
    before = engine.state.state_version

    task = engine.plan_next(claim=True)

    assert task is not None
    assert engine.state.state_version == before + 1


def test_record_result_increments_state_version_once():
    engine = PipelineEngine.create(target_chapters=2, arc_size=50)
    task = engine.plan_next(claim=False)
    assert task is not None
    before = engine.state.state_version

    engine.record_result(task.task_key, "done")

    assert engine.state.state_version == before + 1


def test_review_failures_enqueue_polish_or_rewrite_actions():
    engine = PipelineEngine.create(target_chapters=1, arc_size=50, mode="full_plan")
    engine.record_result("chapter.0001.review", "soft_fail", score=82)
    engine.record_result("chapter.0001.review", "hard_fail", score=55)

    polish = engine.state.creative.polish_queue[0]
    rewrite = engine.state.creative.rewrite_queue[0]
    assert polish["kind"] == "polish"
    assert polish["chapter"] == 1
    assert polish["source_review"] == "reviews/chapter_0001_review.json"
    assert rewrite["kind"] == "rewrite"
    assert rewrite["chapter"] == 1
    assert rewrite["max_attempts"] == 3


def test_rolling_seed_increments_state_version_when_seeded():
    engine = PipelineEngine.create(
        target_chapters=4, arc_size=50, initial_window=1, mode="full_plan"
    )
    _complete_bootstrap(engine)
    _complete_chapter(engine, 1)
    before = engine.state.state_version

    plan = engine.rolling_seed()

    assert plan.seeded is True
    assert engine.state.state_version == before + 1


def test_resume_increments_state_version_when_resetting_claim():
    engine = PipelineEngine.create(target_chapters=2, arc_size=50)
    engine.plan_next(claim=True)
    before = engine.state.state_version

    report = engine.resume()

    assert report.in_progress_reset == 1
    assert engine.state.state_version == before + 1


def test_paused_creative_state_stops_scheduler_at_step_boundary():
    engine = PipelineEngine.create(target_chapters=1, arc_size=50)
    before = engine.state.state_version

    changed = engine.set_paused(True, reason="user_command")

    assert changed is True
    assert engine.state.state_version == before + 1
    assert engine.ready_tasks() == []
    assert engine.plan_next() is None


# --------------------------------------------------------------------------- #
# Unit tests — tool entrypoint + self-registration
# --------------------------------------------------------------------------- #


def test_tool_is_self_registered():
    assert "novelkit_pipeline" in registry.list_tools()
    entry = registry.get("novelkit_pipeline")
    assert entry.fn is pipeline_tool
    assert entry.schema is not None


def test_pipeline_tool_plan_next_roundtrip():
    engine = PipelineEngine.create(target_chapters=3, arc_size=50)
    out = pipeline_tool("plan_next", engine.state.to_dict())
    assert out["result"]["task_key"] == "bootstrap.characters"
    assert "state" in out


def test_pipeline_tool_record_result_updates_state():
    engine = PipelineEngine.create(target_chapters=3, arc_size=50)
    out = pipeline_tool(
        "record_result",
        engine.state.to_dict(),
        task_key="bootstrap.characters",
        result="done",
        score=90,
    )
    restored = PipelineState.from_dict(out["state"])
    assert restored.tasks["bootstrap.characters"].status == TaskStatus.DONE.value


def test_pipeline_tool_unknown_action_raises():
    import pytest

    engine = PipelineEngine.create(target_chapters=1, arc_size=50)
    with pytest.raises(ValueError):
        pipeline_tool("nope", engine.state.to_dict())


# --------------------------------------------------------------------------- #
# Sync gate-fail → automated rewrite cycle (VĐ2 Hướng A)
# --------------------------------------------------------------------------- #


def _seed_single_chapter(engine: PipelineEngine) -> None:
    """Bootstrap + expand chapter 1 so its outline→...→sync tasks are seeded."""
    engine.state.add_specs(build_task_specs(1, 1, 50))
    engine.state.creative.expanded_through_chapter = 1
    _complete_bootstrap(engine)
    for suffix in ("outline", "write", "self_check"):
        _drive_to_done(engine, f"chapter.0001.{suffix}")


def test_sync_hard_fail_recycles_chapter_through_review():
    """A chapter that fails the SYNC quality gate is sent back through review so
    critique can revise the draft again — instead of blocking immediately."""
    engine = PipelineEngine.create(target_chapters=1, arc_size=50, mode="full_plan")
    _seed_single_chapter(engine)
    _drive_to_done(engine, "chapter.0001.review")

    # First sync gate-fail: recycle, not block.
    engine.record_result(
        "chapter.0001.sync", "hard_fail", score=80, failure_signature="sync_blocked"
    )
    review = engine.state.tasks["chapter.0001.review"]
    sync = engine.state.tasks["chapter.0001.sync"]
    assert review.status == TaskStatus.PENDING.value
    assert sync.status == TaskStatus.PENDING.value
    # The breaker streak is cleared so the recycle is not counted as a repeat.
    assert engine.state.breaker.hard_fail_count == 0
    assert not engine.state.breaker.is_open


def test_sync_hard_fail_stops_recycling_after_budget_and_blocks():
    """After ``MAX_REWRITE_CYCLES`` rewrite cycles the chapter is left to block
    (so a human can approve it) instead of recycling forever."""
    engine = PipelineEngine.create(target_chapters=1, arc_size=50, mode="full_plan")
    _seed_single_chapter(engine)

    # Exhaust the rewrite budget: each cycle = one review run + one sync fail.
    for _ in range(MAX_REWRITE_CYCLES + 1):
        _drive_to_done(engine, "chapter.0001.review")
        engine.record_result(
            "chapter.0001.sync", "hard_fail", score=80,
            failure_signature="sync_blocked",
        )

    review = engine.state.tasks["chapter.0001.review"]
    # Budget spent: review was not reset to pending on the final fail.
    assert review.attempt_count > MAX_REWRITE_CYCLES
    # The final sync fail took the normal block/retry path.
    sync = engine.state.tasks["chapter.0001.sync"]
    assert sync.status in (TaskStatus.BLOCKED.value, TaskStatus.RETRYABLE.value)


# --------------------------------------------------------------------------- #
# Manual approval force-passes pre-sync gates (VĐ2 — Duyệt tay bao mọi stage)
# --------------------------------------------------------------------------- #


def test_approve_chapter_force_passes_pre_sync_gates_but_leaves_sync():
    """Approving a chapter stuck at self_check marks self_check + review DONE so
    the run advances, but leaves sync to actually run (it promotes to canon)."""
    engine = PipelineEngine.create(target_chapters=1, arc_size=50, mode="full_plan")
    _seed_single_chapter(engine)
    # Simulate the chapter wedged at self_check: block it + trip the breaker.
    engine.record_result(
        "chapter.0001.self_check", "soft_fail", failure_signature="repeated_sentence"
    )
    engine.state.tasks["chapter.0001.self_check"].status = TaskStatus.BLOCKED.value

    result = engine.approve_chapter(1)

    self_check = engine.state.tasks["chapter.0001.self_check"]
    review = engine.state.tasks["chapter.0001.review"]
    sync = engine.state.tasks["chapter.0001.sync"]
    # Pre-sync gates forced DONE; sync deliberately left to run.
    assert self_check.status == TaskStatus.DONE.value
    assert review.status == TaskStatus.DONE.value
    assert sync.status != TaskStatus.DONE.value
    assert "chapter.0001.self_check" in result["approved_tasks"]
    # Breaker was cleared as part of the approval.
    assert not engine.state.breaker.is_open


def test_approve_chapter_tool_action_roundtrip():
    """The tool entrypoint exposes approve_chapter and returns updated state."""
    engine = PipelineEngine.create(target_chapters=1, arc_size=50, mode="full_plan")
    _seed_single_chapter(engine)
    out = pipeline_tool("approve_chapter", engine.state.to_dict(), chapter=1)
    assert out["result"]["chapter"] == 1
    restored = PipelineState.from_dict(out["state"])
    assert restored.tasks["chapter.0001.self_check"].status == TaskStatus.DONE.value
