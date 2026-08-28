"""Tests for the AutoNovel integration (Task 12, Requirement 7).

Two halves matching the two sub-tasks:

- **12.2 — Artifact layout mapping**: the NovelKit ↔ AutoNovel layout bijection
  round-trips for every canonical artifact path (and for arbitrary nested paths
  under each known top-level prefix).
- **12.1 — Adapter / loop seam**: the :class:`AutoNovelAdapter` drives a sample
  novel through bootstrap → 1 chapter using the **real** ``novelkit_pipeline``
  scheduling interface (``plan_next`` / ``record_result``) and the in-memory
  AutoNovel loop, reusing the real DNA-bootstrap and sync tools. This proves the
  pipeline *extends* AutoNovel's loop rather than running in parallel
  (Requirement 7.2).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from integrations.autonovel import (
    CANONICAL_NOVELKIT_ARTIFACTS,
    AutoNovelAdapter,
    AutoNovelWorkspace,
    InMemoryAutoNovelLoop,
    LoopStage,
    LoopStep,
    to_autonovel,
    to_novelkit,
)
from integrations.autonovel.layout import LAYOUT
from integrations.autonovel.llm_loop import LLMAutoNovelLoop
from tools.novelkit_pipeline_tool import PipelineEngine, TaskStatus, build_task_specs
from tools.novelkit_pipeline_state_store import PipelineStateStore
from tools.novelkit_rules_tool import current_rules_digest


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _workspace(name: str = "demo-autonovel") -> AutoNovelWorkspace:
    root = Path(tempfile.mkdtemp()) / name
    root.mkdir(parents=True)
    return AutoNovelWorkspace(root=root)


# --------------------------------------------------------------------------- #
# 12.2 — Artifact layout mapping round-trip
# --------------------------------------------------------------------------- #


def test_canonical_artifacts_round_trip():
    """Every canonical NovelKit artifact survives NK→AutoNovel→NK unchanged."""
    for rel in CANONICAL_NOVELKIT_ARTIFACTS:
        assert to_novelkit(to_autonovel(rel)) == rel, rel
        assert LAYOUT.round_trips(rel) is True


def test_canonical_artifacts_reverse_round_trip():
    """Every mapped AutoNovel path survives AutoNovel→NK→AutoNovel unchanged."""
    for rel in CANONICAL_NOVELKIT_ARTIFACTS:
        an = to_autonovel(rel)
        assert to_autonovel(to_novelkit(an)) == an, an


def test_mapping_is_actually_renaming_not_identity():
    """The six headline artifact groups must change name (not pass through)."""
    assert to_autonovel("PROJECT_DNA.md") == "bible/premise.md"
    assert to_autonovel("database/characters/x.md") == "codex/characters/x.md"
    assert to_autonovel("outlines/master_outline.md") == "beats/master_outline.md"
    assert to_autonovel("chapters/chapter_001.md") == "manuscript/chapter_001.md"
    assert to_autonovel("reviews/chapter_001_review.md") == "critique/chapter_001_review.md"
    assert to_autonovel("memory/Memory.md") == "context/Memory.md"


_TOP_LEVEL_PREFIXES = [
    "database",
    "outlines",
    "chapters",
    "drafts",
    "reviews",
    "memory",
    "style_vault",
    "logs",
]


@settings(max_examples=200, deadline=None)
@given(
    prefix=st.sampled_from(_TOP_LEVEL_PREFIXES),
    segments=st.lists(
        st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
            min_size=1,
            max_size=8,
        ),
        min_size=1,
        max_size=4,
    ),
)
def test_arbitrary_nested_paths_round_trip(prefix, segments):
    """Arbitrary nested paths under a known prefix round-trip (P-style mapping).

    **Validates: Requirements 7.2**
    """
    rel = prefix + "/" + "/".join(segments) + ".md"
    assert to_novelkit(to_autonovel(rel)) == rel


def test_directory_only_paths_round_trip():
    """Bare directory names (no trailing slash) round-trip too."""
    for prefix in _TOP_LEVEL_PREFIXES:
        assert to_novelkit(to_autonovel(prefix)) == prefix


def test_unknown_paths_pass_through():
    """Unrecognised paths map to themselves (the mapping is total)."""
    assert to_autonovel("README.md") == "README.md"
    assert to_novelkit("README.md") == "README.md"


def test_describe_lists_all_rules():
    rows = LAYOUT.describe()
    kinds = {r["kind"] for r in rows}
    assert kinds == {"file", "dir"}
    novelkit_names = {r["novelkit"] for r in rows}
    assert "PROJECT_DNA.md" in novelkit_names
    assert "chapters/" in novelkit_names


# --------------------------------------------------------------------------- #
# 12.1 — Phase → loop stage mapping
# --------------------------------------------------------------------------- #


def test_every_pipeline_task_maps_to_a_loop_stage():
    """Every task the DAG can emit has an AutoNovel loop stage (no parallel loop).

    **Validates: Requirements 7.1, 7.2**
    """
    # Chapter 10 triggers the character-update barrier (phase "state").
    specs = build_task_specs(1, 10, mode="full_plan")
    stages = {LoopStep.from_task(t).stage for t in specs}
    # The unified chapter flow exercises plan/draft/self-check/review/sync.
    assert stages == {
        LoopStage.WORLDBUILD,
        LoopStage.OUTLINE,
        LoopStage.DRAFT,
        LoopStage.SELF_CHECK,
        LoopStage.CRITIQUE,
        LoopStage.SYNCHRONISE,
    }


def test_loop_step_exposes_autonovel_outputs():
    specs = build_task_specs(1, 1)
    write = next(t for t in specs if t.task_key == "chapter.0001.write")
    step = LoopStep.from_task(write)
    assert step.output_paths == ("drafts/chapter_0001.md",)
    assert step.autonovel_outputs() == ("working/chapter_0001.md",)


class _FakeClient:
    def complete(self, **_kwargs):  # noqa: ANN003
        return ""


class _ExplodingLoop(InMemoryAutoNovelLoop):
    def worldbuild(self, step, workspace):  # noqa: ANN001
        raise RuntimeError("boom")


def test_llm_loop_retrieve_uses_accepted_chapters_and_reviews():
    ws = _workspace()
    ws.write("chapters/chapter_001.md", "Tuyết Hồn Ấn được gieo trong hang băng.")
    ws.write(
        "reviews/chapter_001_review.md",
        "review_lesson: Tuyết Hồn Ấn cần được nhắc lại bằng hành động.",
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())

    block = loop._retrieve(ws, "Tuyết Hồn Ấn review_lesson")

    assert "source: chapters/chapter_001.md" in block
    assert "source: reviews/chapter_001_review.md" in block


def test_llm_loop_retrieve_uses_rules_snapshot_and_summaries():
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.rules.json",
        json.dumps(
            {
                "schema_version": 1,
                "revision": 1,
                "rules": [
                    {
                        "rule_id": "user_0001",
                        "scope": "style",
                        "kind": "preference",
                        "text": "prefer short lines for dialogue",
                        "normalized": {
                            "target": "dialogue_style",
                            "operator": "prefer",
                            "value": "short_lines",
                        },
                        "enforcement": "preference",
                        "source": "runtime_user_update",
                        "created_at": "2026-06-29T00:00:00Z",
                    }
                ],
                "updated_at": "2026-06-29T00:00:00Z",
            }
        ),
    )
    ws.write(
        "summaries/chapter_0001.summary.json",
        json.dumps(
            {
                "schema_version": 1,
                "chapter": 1,
                "source_commit_ids": ["commit-a"],
                "source_digests": {"chapters/chapter_001.md": "a" * 64},
                "event": "moon oath creates unresolved debt",
            }
        ),
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())

    block = loop._retrieve(ws, "short lines moon oath unresolved debt")

    assert "source: PROJECT_DNA.rules.json" in block
    assert "source: summaries/chapter_0001.summary.json" in block


# --------------------------------------------------------------------------- #
# 12.1 — Adapter drives bootstrap → 1 chapter through the pipeline
# --------------------------------------------------------------------------- #


def test_adapter_runs_bootstrap_to_one_chapter():
    """Drive a sample novel bootstrap → 1 chapter via plan_next/record_result.

    **Validates: Requirements 7.1, 7.2**
    """
    ws = _workspace()
    adapter = AutoNovelAdapter.create(
        workspace=ws,
        loop=InMemoryAutoNovelLoop(),
        target_chapters=1,
        mode="full_plan",
    )

    report = adapter.run()

    # The run drained the DAG without tripping the breaker.
    assert report.stopped_reason == "drained"
    assert report.blocked is False
    assert report.breaker_open is False

    # The full chapter loop ran exactly once.
    assert report.chapters_drafted == 1
    assert report.chapters_synced == 1

    # Bootstrap (5 specs) + chapter outline/write/self-check/review/sync (5) = 10 tasks.
    assert report.tasks_completed == 10
    assert report.final_status == "completed"

    # Every pipeline task is done — nothing left ready.
    assert all(
        t.status == TaskStatus.DONE.value
        for t in adapter.engine.state.tasks.values()
    )
    assert adapter.engine.plan_next() is None


def test_adapter_run_produces_chapter_and_review_artifacts():
    """The loop materialised draft/check/review, then sync promoted canon."""
    ws = _workspace()
    adapter = AutoNovelAdapter.create(
        workspace=ws, loop=InMemoryAutoNovelLoop(), target_chapters=1, mode="full_plan"
    )
    adapter.run()

    assert ws.exists("drafts/chapter_0001.md")
    assert ws.exists("drafts/chapter_0001.check.json")
    assert ws.exists("chapters/chapter_001.md")
    assert ws.exists("reviews/chapter_0001_review.json")
    assert ws.exists("reviews/chapter_0001_review.md")
    # The sync tool wrote its content-addressed commit and refreshed the index.
    assert (ws.root / ".commits" / "chapter_0001.commit.json").exists()
    assert (ws.root / ".rag" / "index_meta.json").exists()
    # Doctor-compatible status snapshot was refreshed each step.
    assert ws.exists("logs/pipeline_status.json")


def test_loop_self_check_and_review_share_rules_digest():
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.rules.json",
        json.dumps(
            {
                "schema_version": 1,
                "revision": 1,
                "rules": [
                    {
                        "rule_id": "user_0001",
                        "scope": "style",
                        "kind": "preference",
                        "text": "ưu tiên đối thoại ngắn",
                        "normalized": {
                            "target": "dialogue_style",
                            "operator": "prefer",
                            "value": "short_lines",
                        },
                        "enforcement": "preference",
                        "source": "runtime_user_update",
                        "created_at": "2026-06-29T00:00:00Z",
                    }
                ],
                "updated_at": "2026-06-29T00:00:00Z",
            },
            ensure_ascii=False,
        ),
    )
    ws.write("drafts/chapter_0001.md", "Một chương thử có đối thoại gọn.")
    expected_digest = current_rules_digest(ws.root)
    loop = InMemoryAutoNovelLoop()
    check_step = LoopStep(
        task_key="chapter.0001.self_check",
        stage=LoopStage.SELF_CHECK,
        phase="self_check",
        command="self_check",
        agent_role="reviewer",
        chapter=1,
        arc=1,
        input_paths=("drafts/chapter_0001.md",),
        output_paths=("drafts/chapter_0001.check.json",),
        context_query=None,
    )
    review_step = LoopStep(
        task_key="chapter.0001.review",
        stage=LoopStage.CRITIQUE,
        phase="review",
        command="review",
        agent_role="reviewer",
        chapter=1,
        arc=1,
        input_paths=("drafts/chapter_0001.md", "drafts/chapter_0001.check.json"),
        output_paths=("reviews/chapter_0001_review.json",),
        context_query=None,
    )

    loop.self_check(check_step, ws)
    loop.critique(review_step, ws)

    check = json.loads(ws.read("drafts/chapter_0001.check.json"))
    review = json.loads(ws.read("reviews/chapter_0001_review.json"))
    assert check["rules_digest"] == expected_digest
    assert review["rules_digest"] == expected_digest


def test_adapter_step_persists_pipeline_state_through_store():
    ws = _workspace()
    engine = PipelineEngine.create(target_chapters=1, arc_size=50, novel="demo")
    store = PipelineStateStore(ws.root)
    store.save(engine.state)
    adapter = AutoNovelAdapter(
        engine,
        InMemoryAutoNovelLoop(),
        ws,
        state_store=store,
    )

    step = adapter.step()

    assert step is not None
    persisted = json.loads(store.state_path.read_text())
    first_task = next(t for t in persisted["tasks"] if t["task_key"] == step["task_key"])
    assert first_task["status"] == TaskStatus.DONE.value
    assert persisted["state_version"] == engine.state.state_version
    checkpoint = json.loads(store.checkpoints_path.read_text().splitlines()[-1])
    assert checkpoint["task_key"] == step["task_key"]
    assert checkpoint["step"] == "plan_completed"
    assert checkpoint["state_version"] == persisted["state_version"]


def test_adapter_step_persists_claim_before_stage_execution():
    ws = _workspace()
    engine = PipelineEngine.create(target_chapters=1, arc_size=50, novel="demo")
    store = PipelineStateStore(ws.root)
    store.save(engine.state)
    adapter = AutoNovelAdapter(engine, _ExplodingLoop(), ws, state_store=store)

    with pytest.raises(RuntimeError):
        adapter.step()

    persisted = json.loads(store.state_path.read_text())
    claimed = next(t for t in persisted["tasks"] if t["task_key"] == "bootstrap.characters")
    assert claimed["status"] == TaskStatus.IN_PROGRESS.value


def test_adapter_run_order_follows_dag():
    """The stages execute in DAG order: outline → draft → self-check → critique → sync."""
    ws = _workspace()
    adapter = AutoNovelAdapter.create(
        workspace=ws, loop=InMemoryAutoNovelLoop(), target_chapters=1
    )
    report = adapter.run()

    chapter_steps = [s for s in report.steps if s["chapter"] == 1]
    stages = [s["stage"] for s in chapter_steps]
    assert stages == [
        LoopStage.OUTLINE.value,
        LoopStage.DRAFT.value,
        LoopStage.SELF_CHECK.value,
        LoopStage.CRITIQUE.value,
        LoopStage.SYNCHRONISE.value,
    ]


def test_adapter_respects_max_steps():
    ws = _workspace()
    adapter = AutoNovelAdapter.create(
        workspace=ws, loop=InMemoryAutoNovelLoop(), target_chapters=1
    )
    report = adapter.run(max_steps=3)
    assert report.stopped_reason == "max_steps"
    assert len(report.steps) == 3
    # The pipeline still has ready work — the loop was paused, not drained.
    assert adapter.engine.plan_next() is not None


def test_adapter_stops_after_requested_chapters():
    """max_chapters stops the loop once N chapters finish syncing, regardless
    of how many steps that took, and leaves the rest of the DAG ready."""
    ws = _workspace()
    adapter = AutoNovelAdapter.create(
        workspace=ws, loop=InMemoryAutoNovelLoop(), target_chapters=3, mode="full_plan"
    )

    report = adapter.run(max_chapters=1)

    assert report.stopped_reason == "max_chapters"
    assert report.chapters_synced == 1
    # More chapters remain in the target → the loop paused, not drained.
    assert adapter.engine.plan_next() is not None


def test_adapter_blocks_when_review_fails_gate():
    """A failing review score blocks the sync stage (gate enforced through loop)."""
    ws = _workspace()
    # Score below the soft-fail floor → sync's review gate blocks.
    loop = InMemoryAutoNovelLoop(review_score=40.0)
    adapter = AutoNovelAdapter.create(
        workspace=ws, loop=loop, target_chapters=1
    )
    report = adapter.run()

    assert report.chapters_synced == 0
    assert report.blocked is True
    # The chapter was drafted + critiqued, but never promoted into canon.
    assert ws.exists("drafts/chapter_0001.md")
    assert not ws.exists("chapters/chapter_001.md")
    assert not (ws.root / ".commits" / "chapter_0001.commit.json").exists()


def test_adapter_resume_does_not_rerun_done_tasks():
    """Re-running the adapter after a full drain is a no-op (resume safety)."""
    ws = _workspace()
    adapter = AutoNovelAdapter.create(
        workspace=ws, loop=InMemoryAutoNovelLoop(), target_chapters=1
    )
    adapter.run()
    second = adapter.run()
    assert second.tasks_completed == 0
    assert second.stopped_reason == "drained"


def test_synchronise_without_real_sync_still_completes():
    """The loop can run without delegating to the real sync tool (pure seam)."""
    ws = _workspace()
    loop = InMemoryAutoNovelLoop(use_real_sync=False)
    adapter = AutoNovelAdapter.create(workspace=ws, loop=loop, target_chapters=1)
    report = adapter.run()
    assert report.chapters_synced == 1
    assert report.blocked is False


# --------------------------------------------------------------------------- #
# Bug fix: worldbuild bootstrap generates ONE file per LLM call (not a single
# mega multi-file call). Root cause of the field report: the old one-call-for-
# all-files request blew past the provider's token/output ceiling and raised
# LLMError as a whole, so EVERY bootstrap file fell back to the
# "_(chờ AI bổ sung — chạy lại bước này)_" stub. Per-file calls keep each
# request small and isolate any failure to just the file that failed — its
# siblings still get real content.
# --------------------------------------------------------------------------- #


def _bootstrap_step(command: str = "BUILD_WORLD") -> LoopStep:
    return LoopStep(
        task_key="bootstrap.world",
        stage=LoopStage.WORLDBUILD,
        phase="1",
        command=command,
        agent_role="World Builder",
        chapter=None,
        arc=None,
        input_paths=("PROJECT_DNA.md",),
        output_paths=("database/worldbuilding/", "database/systems/"),
        context_query="world rules factions geography systems",
    )


class _PerFileClient:
    """Fake LLM client that maps each per-file request to a scripted result.

    ``worldbuild`` now issues one ``complete`` call per target file, embedding
    the file's relative path in the user prompt as a backticked token
    (`` `<rel>` ``). This client matches on that exact token — not a loose
    substring — so it never matches a path that merely appears inside the RAG
    ground block (canon written by an earlier run mentions sibling file paths).
    A string is returned as-is; an :class:`Exception` value is raised to
    simulate a provider failure for just that file. A ``list`` value is consumed
    one entry per call (each entry a string to return or an ``Exception`` to
    raise), so a file can fail then recover across retries.
    """

    def __init__(self, by_path: dict[str, object]):
        self._by_path = by_path
        self.calls: list[str] = []
        self.users: list[str] = []

    def complete(self, *, user: str = "", **_kwargs):  # noqa: ANN003
        self.users.append(user)
        for path, result in self._by_path.items():
            if f"`{path}`" in user:
                self.calls.append(path)
                if isinstance(result, list):
                    result = result.pop(0) if result else "Nội dung mặc định."
                if isinstance(result, Exception):
                    raise result
                return result
        return "Nội dung mặc định."


def test_worldbuild_generates_one_call_per_file():
    """Each bootstrap file is produced by its own LLM call and gets that call's
    real content — no shared mega-call, no delimiter parsing."""
    from provider.llm_client import LLMError

    ws = _workspace()
    # The genre must be declared: the register contract is resolved from the
    # novel's own genre, and there is deliberately no implicit "xianxia" default
    # any more (a novel with no genre used to be silently drafted as xianxia).
    ws.write(
        "PROJECT_DNA.md",
        "---\ngenre: xianxia\ngenre_primary: xianxia\n---\n"
        "- **Tên tác phẩm:** Thí Nghiệm\n",
    )
    client = _PerFileClient(
        {
            "database/worldbuilding/overview.md": "Tổng quan thế giới thật.",
            "database/worldbuilding/geography.md": "Địa lý thật.",
            "database/worldbuilding/factions.md": "Thế lực thật.",
            "database/systems/power_system.md": "Hệ thống sức mạnh thật.",
        }
    )
    loop = LLMAutoNovelLoop(client=client)

    result = loop.worldbuild(_bootstrap_step(), ws)

    # One call per target file (four BUILD_WORLD files) — not a single mega-call.
    assert len(client.calls) == 4
    assert all("REGISTER CONTRACT TỪ CONFIG" in user for user in client.users)
    for rel in (
        "database/worldbuilding/overview.md",
        "database/worldbuilding/geography.md",
        "database/worldbuilding/factions.md",
        "database/systems/power_system.md",
    ):
        text = (ws.root / rel).read_text(encoding="utf-8")
        assert "_(chờ AI bổ sung" not in text, f"{rel} unexpectedly stubbed"
    assert "Địa lý thật." in (
        ws.root / "database/worldbuilding/geography.md"
    ).read_text(encoding="utf-8")
    assert set(result.artifacts) >= {
        "database/worldbuilding/overview.md",
        "database/systems/power_system.md",
    }


def test_worldbuild_stubs_only_the_file_whose_call_failed(monkeypatch):
    """A provider failure on ONE file's call stubs only that file; the other
    files' calls succeed and keep their real content (failure isolation)."""
    import time

    from provider.llm_client import LLMError

    # Skip the retry backoff sleeps for the deliberately-failing file.
    monkeypatch.setattr(time, "sleep", lambda *_a, **_k: None)

    ws = _workspace()
    ws.write("PROJECT_DNA.md", "- **Tên tác phẩm:** Thí Nghiệm\n")
    client = _PerFileClient(
        {
            "database/worldbuilding/overview.md": "Tổng quan thế giới thật.",
            # geography's call fails (e.g. provider token ceiling) → stub only it
            "database/worldbuilding/geography.md": LLMError("LLM API error 400"),
            "database/worldbuilding/factions.md": "Thế lực thật.",
            "database/systems/power_system.md": "Hệ thống sức mạnh thật.",
        }
    )
    loop = LLMAutoNovelLoop(client=client)

    loop.worldbuild(_bootstrap_step(), ws)

    overview = (ws.root / "database/worldbuilding/overview.md").read_text(encoding="utf-8")
    assert "Tổng quan thế giới thật." in overview
    assert "_(chờ AI bổ sung" not in overview
    geography = (ws.root / "database/worldbuilding/geography.md").read_text(encoding="utf-8")
    assert "_(chờ AI bổ sung — chạy lại bước này)_" in geography


def test_worldbuild_recovers_from_transient_gateway_timeout(monkeypatch):
    """A transient gateway timeout (Cloudflare 524) on the first attempt must be
    retried with backoff, not fail the file outright. Production evidence showed
    two back-to-back attempts hitting the same slow window and failing
    identically; spacing the retries lets the provider recover so the file gets
    real content instead of the stub."""
    import time

    from provider.llm_client import LLMError

    # Don't actually sleep during the backoff between retries.
    monkeypatch.setattr(time, "sleep", lambda *_a, **_k: None)

    ws = _workspace()
    ws.write("PROJECT_DNA.md", "- **Tên tác phẩm:** Thí Nghiệm\n")
    client = _PerFileClient(
        {
            # First attempt 524s, second attempt succeeds → real content, no stub.
            "database/characters/protagonist.md": [
                LLMError("LLM API error 524: <!DOCTYPE html>"),
                "Hồ sơ nhân vật chính thật.",
            ],
            "database/characters/antagonist.md": "Hồ sơ phản diện thật.",
            "database/characters/supporting_cast.md": "Dàn phụ thật.",
        }
    )
    loop = LLMAutoNovelLoop(client=client)

    loop.worldbuild(_bootstrap_step("CREATE_CHARACTERS"), ws)

    protagonist = (
        ws.root / "database/characters/protagonist.md"
    ).read_text(encoding="utf-8")
    assert "Hồ sơ nhân vật chính thật." in protagonist
    assert "_(chờ AI bổ sung" not in protagonist
    # protagonist.md was called twice (one 524, one success).
    assert client.calls.count("database/characters/protagonist.md") == 2


def test_worldbuild_reports_soft_fail_when_a_file_stays_stub(monkeypatch):
    """A file that stays on the stub after retries must make worldbuild report
    ``soft_fail`` (not ``done``), so the pipeline marks the task ``retryable``
    and the bootstrap step can run again — otherwise the stub is frozen forever.
    """
    import time

    from provider.llm_client import LLMError

    monkeypatch.setattr(time, "sleep", lambda *_a, **_k: None)

    ws = _workspace()
    ws.write("PROJECT_DNA.md", "- **Tên tác phẩm:** Thí Nghiệm\n")
    client = _PerFileClient(
        {
            "database/characters/protagonist.md": "Hồ sơ nhân vật chính thật.",
            "database/characters/antagonist.md": LLMError("LLM API error 524"),
            "database/characters/supporting_cast.md": "Dàn phụ thật.",
        }
    )
    loop = LLMAutoNovelLoop(client=client)

    result = loop.worldbuild(_bootstrap_step("CREATE_CHARACTERS"), ws)

    assert result.outcome == "soft_fail"
    # The failure signature names the still-stubbed file so the breaker only
    # trips on the SAME file failing repeatedly.
    assert result.failure_signature is not None
    assert "antagonist.md" in result.failure_signature


def test_worldbuild_rerun_skips_files_already_good(monkeypatch):
    """A re-run only regenerates the still-stubbed file; files that already hold
    real content are skipped (no LLM call) and never overwritten — so a retry
    converges instead of re-rolling everything and risking a good file."""
    import time

    from provider.llm_client import LLMError

    monkeypatch.setattr(time, "sleep", lambda *_a, **_k: None)

    ws = _workspace()
    ws.write("PROJECT_DNA.md", "- **Tên tác phẩm:** Thí Nghiệm\n")

    # First run: antagonist fails → stub; the other two get real content.
    client1 = _PerFileClient(
        {
            "database/characters/protagonist.md": "Hồ sơ nhân vật chính thật.",
            "database/characters/antagonist.md": LLMError("LLM API error 524"),
            "database/characters/supporting_cast.md": "Dàn phụ thật.",
        }
    )
    loop1 = LLMAutoNovelLoop(client=client1)
    loop1.worldbuild(_bootstrap_step("CREATE_CHARACTERS"), ws)

    # Second run: provider is healthy now. Only antagonist should be requested;
    # the two already-good files must be skipped (idempotent, no clobber).
    client2 = _PerFileClient(
        {
            "database/characters/protagonist.md": "KHÔNG ĐƯỢC GHI ĐÈ.",
            "database/characters/antagonist.md": "Hồ sơ phản diện thật.",
            "database/characters/supporting_cast.md": "KHÔNG ĐƯỢC GHI ĐÈ.",
        }
    )
    loop2 = LLMAutoNovelLoop(client=client2)
    result = loop2.worldbuild(_bootstrap_step("CREATE_CHARACTERS"), ws)

    # Only the stubbed file was regenerated on the re-run.
    assert client2.calls == ["database/characters/antagonist.md"]
    assert result.outcome == "done"
    antagonist = (
        ws.root / "database/characters/antagonist.md"
    ).read_text(encoding="utf-8")
    assert "Hồ sơ phản diện thật." in antagonist
    # The already-good files kept their original content.
    protagonist = (
        ws.root / "database/characters/protagonist.md"
    ).read_text(encoding="utf-8")
    assert "Hồ sơ nhân vật chính thật." in protagonist


# --------------------------------------------------------------------------- #
# Prose budget scales with the DNA's target_words_per_chapter (MAX_TOKEN b/c)
# --------------------------------------------------------------------------- #


class _ConfigClient:
    """Fake client exposing a ``config.max_tokens`` ceiling like the real one."""

    def __init__(self, max_tokens: int):
        from provider.llm_client import LLMConfig

        self.config = LLMConfig(
            api_key="k", model="m", base_url="https://x/v1", max_tokens=max_tokens
        )

    def complete(self, **_kwargs):  # noqa: ANN003 — never called in these tests
        raise AssertionError("complete() should not run in budget tests")


def test_words_per_chapter_reads_from_dna_footer():
    ws = _workspace()
    ws.write("PROJECT_DNA.md", "- **Tên:** X\n\ntarget_words_per_chapter: 4200\n")
    loop = LLMAutoNovelLoop(client=_ConfigClient(16384))
    assert loop._resolve_words_per_chapter(ws) == 4200


def test_words_per_chapter_falls_back_to_default_without_dna_field():
    ws = _workspace()
    ws.write("PROJECT_DNA.md", "- **Tên:** X\n")
    loop = LLMAutoNovelLoop(client=_ConfigClient(16384), words_per_chapter=2600)
    assert loop._resolve_words_per_chapter(ws) == 2600


def test_words_per_chapter_is_clamped_against_typos():
    ws = _workspace()
    ws.write("PROJECT_DNA.md", "target_words_per_chapter: 999999\n")
    loop = LLMAutoNovelLoop(client=_ConfigClient(16384))
    # Clamped to the sane upper band, not the raw typo.
    assert loop._resolve_words_per_chapter(ws) == 12000


def test_prose_budget_scales_with_words_but_caps_at_config_ceiling():
    ws = _workspace()
    ws.write("PROJECT_DNA.md", "target_words_per_chapter: 4200\n")
    # Ceiling high enough: budget scales to ~4 tokens/word.
    loop = LLMAutoNovelLoop(client=_ConfigClient(20000))
    assert loop._prose_budget(ws) == 4200 * 4
    # Low ceiling: budget is capped so we never ask for more than the model emits.
    capped = LLMAutoNovelLoop(client=_ConfigClient(8192))
    assert capped._prose_budget(ws) == 8192


def test_prose_budget_respects_floor_for_short_chapters():
    ws = _workspace()
    ws.write("PROJECT_DNA.md", "target_words_per_chapter: 800\n")
    loop = LLMAutoNovelLoop(client=_ConfigClient(16384))
    # 800*4 = 3200 < 8000 floor → floored at 8000.
    assert loop._prose_budget(ws) == 8000


# --------------------------------------------------------------------------- #
# Continuity state-card + length penalty (Phần 2/3 quality fixes)
# --------------------------------------------------------------------------- #


def test_state_card_prefers_latest_character_snapshot():
    ws = _workspace()
    ws.write("PROJECT_DNA.md", "- **Tên:** X\n")
    ws.write(
        "database/characters/protagonist.md",
        "Cảnh giới: Luyện Khí tầng 1 (canon gốc).",
    )
    ws.write(
        "memory/character_snapshots/chapter_002_character_state.md",
        "Cảnh giới HIỆN TẠI: Trúc Cơ sơ kỳ sau chương 2.",
    )
    loop = LLMAutoNovelLoop(client=_ConfigClient(16384))
    # Drafting chapter 3 must see the ch2 snapshot, not the stale canon sheet.
    card = loop._state_card(ws, 3)
    assert "Trúc Cơ sơ kỳ" in card
    assert "canon gốc" not in card


def test_state_card_falls_back_to_protagonist_sheet_without_snapshot():
    ws = _workspace()
    ws.write("PROJECT_DNA.md", "- **Tên:** X\n")
    ws.write(
        "database/characters/protagonist.md",
        "Cảnh giới: Luyện Khí tầng 9 đỉnh phong.",
    )
    loop = LLMAutoNovelLoop(client=_ConfigClient(16384))
    card = loop._state_card(ws, 2)
    assert "Luyện Khí tầng 9" in card


def test_length_penalty_forces_rewrite_when_chapter_too_short():
    ws = _workspace()
    ws.write("PROJECT_DNA.md", "target_words_per_chapter: 2500\n")
    loop = LLMAutoNovelLoop(client=_ConfigClient(16384))
    # A 1000-word chapter (40% of 2500) with a "pass" review must be knocked
    # into the fail band so the auto-revise loop rewrites it longer.
    short_text = " ".join(["từ"] * 1000)
    score, verdict = loop._apply_length_penalty(ws, short_text, 90.0, "pass")
    assert verdict in ("soft_fail", "hard_fail")
    assert score < 85


def test_length_penalty_leaves_full_length_chapter_untouched():
    ws = _workspace()
    ws.write("PROJECT_DNA.md", "target_words_per_chapter: 2500\n")
    loop = LLMAutoNovelLoop(client=_ConfigClient(16384))
    # 2200 words = 88% of target ≥ 80% floor → unchanged.
    full_text = " ".join(["từ"] * 2200)
    score, verdict = loop._apply_length_penalty(ws, full_text, 90.0, "pass")
    assert score == 90.0
    assert verdict == "pass"


# --------------------------------------------------------------------------- #
# self_check: repeated_sentence is warning-only, never a blocking soft_fail
# (VĐ1 — the loop that wedged the pipeline across many novels)
# --------------------------------------------------------------------------- #


class _SilentClient:
    """Fake client whose complete() is never expected to run in self_check."""

    def complete(self, **_kwargs):  # noqa: ANN003
        raise AssertionError("self_check must not call the LLM")


def _self_check_step(chapter: int) -> LoopStep:
    return LoopStep(
        task_key=f"chapter.{chapter:04d}.self_check",
        stage=LoopStage.SELF_CHECK,
        phase="self_check",
        command="self_check",
        agent_role="reviewer",
        chapter=chapter,
        arc=1,
        input_paths=(f"drafts/chapter_{chapter:04d}.md",),
        output_paths=(f"drafts/chapter_{chapter:04d}.check.json",),
        context_query=None,
    )


def test_self_check_repeated_sentence_is_warning_not_soft_fail():
    """A verbatim repeated sentence across chapters must NOT soft_fail self_check
    (that fail had no rewrite path and looped the breaker open). It stays a
    non-blocking warning so the chapter advances to review."""
    ws = _workspace()
    ws.write("PROJECT_DNA.md", "- **Tên:** X\ntarget_words_per_chapter: 100\n")
    # Enable the style_stats flag so the repeat guard actually runs.
    ws.write("config/longform.json", json.dumps({"flags": {"style_stats": True}}))
    # A sentence long enough (≥40 chars) repeated verbatim in the previous chapter.
    repeated = "Dương Dương siết chặt mảnh kính xám tro trong lòng bàn tay lạnh."
    ws.write("chapters/chapter_002.md", f"Mở đầu chương hai. {repeated} Kết chương hai.")
    ws.write(
        "drafts/chapter_0003.md",
        f"Sang chương ba, mọi thứ đổi khác. {repeated} Rồi hắn bước tiếp về phía trước.",
    )
    loop = LLMAutoNovelLoop(client=_SilentClient())
    result = loop.self_check(_self_check_step(3), ws)

    check = json.loads(ws.read("drafts/chapter_0003.check.json"))
    # The guard still records the finding as a warning (visibility preserved)…
    assert "repeated_sentence" in check["warnings"]
    # …but the step outcome is NOT a soft_fail — it advances.
    assert result.outcome == "done"
    assert result.failure_signature is None


# --------------------------------------------------------------------------- #
# Anti-slop / lexical gate in the critique repair loop (flag-gated, default OFF)
# --------------------------------------------------------------------------- #


def _anti_slop_ws(draft: str, *, flag_on: bool) -> AutoNovelWorkspace:
    ws = _workspace()
    ws.write("PROJECT_DNA.md", "genre: xianxia\ntarget_words_per_chapter: 100\n")
    # Write an explicit per-novel override either way: the package config ships
    # anti_slop ON, so "flag off" must be an explicit false, not an omission.
    ws.write("config/longform.json", json.dumps({"flags": {"anti_slop": flag_on}}))
    ws.write("drafts/chapter_0001.md", draft)
    return ws


def test_classical_xianxia_prompt_contract_is_derived_from_guard_profile():
    ws = _anti_slop_ws("Nội dung sạch.", flag_on=True)
    contract = LLMAutoNovelLoop(
        client=_FakeClient()
    )._language_guard_prompt_contract(ws)

    assert "đại từ khẩu ngữ tao/mày" in contract
    assert "ta / ngươi / các ngươi" in contract
    assert "thời lượng hiện đại tính bằng giờ" in contract


def test_outline_prompt_includes_strict_config_contract():
    class _CaptureClient:
        def __init__(self):
            self.user = ""

        def complete(self, *, user="", **_kwargs):  # noqa: ANN003
            self.user = user
            return "# Dàn ý\n\nKỷ Trụ bước vào cổ miếu."

    ws = _anti_slop_ws("Nội dung sạch.", flag_on=True)
    client = _CaptureClient()
    step = LoopStep(
        task_key="chapter.0001.outline",
        stage=LoopStage.OUTLINE,
        phase="2",
        command="outline",
        agent_role="outliner",
        chapter=1,
        arc=1,
        input_paths=("PROJECT_DNA.md",),
        output_paths=("outlines/arc_1/chapter_001_outline.md",),
        context_query="chương 1",
    )

    LLMAutoNovelLoop(client=client).outline(step, ws)

    assert "REGISTER CONTRACT TỪ CONFIG" in client.user
    assert "đại từ khẩu ngữ tao/mày" in client.user


def test_outline_repairs_config_violation_before_persisting():
    class _SequenceClient:
        def __init__(self):
            self.responses = [
                'Bác Trường Can hỏi: "Đêm qua mày có thấy gì không?"',
                'Trưởng lão hỏi: "Đêm qua ngươi có trông thấy dị tượng không?"',
            ]

        def complete(self, **_kwargs):  # noqa: ANN003
            return self.responses.pop(0)

    ws = _anti_slop_ws("Nội dung sạch.", flag_on=True)
    step = LoopStep(
        task_key="chapter.0001.outline",
        stage=LoopStage.OUTLINE,
        phase="2",
        command="outline",
        agent_role="outliner",
        chapter=1,
        arc=1,
        input_paths=("PROJECT_DNA.md",),
        output_paths=("outlines/arc_1/chapter_001_outline.md",),
        context_query="chương 1",
    )

    result = LLMAutoNovelLoop(
        client=_SequenceClient(), max_revisions=1
    ).outline(step, ws)

    saved = ws.read("outlines/arc_1/chapter_001_outline.md")
    assert result.outcome == "done"
    assert "ngươi" in saved
    assert "mày" not in saved


def test_draft_repairs_config_violation_before_review():
    class _SequenceClient:
        def __init__(self):
            self.responses = [
                'A Mãnh gọi: "Trụ ơi, về ăn cơm với tao!"',
                'A Mãnh gọi: "Trụ ca, trở về dùng bữa cùng ta!"',
            ]

        def complete(self, **_kwargs):  # noqa: ANN003
            return self.responses.pop(0)

    class _NoCastLoop(LLMAutoNovelLoop):
        def _emit_cast_intros(self, ws, ch, chapter_text):  # noqa: ANN001
            return None

    ws = _anti_slop_ws("Nội dung sạch.", flag_on=True)
    ws.write(
        "outlines/arc_1/chapter_001_outline.md",
        "A Mãnh gọi Kỷ Trụ trở về dùng bữa.",
    )
    step = LoopStep(
        task_key="chapter.0001.write",
        stage=LoopStage.DRAFT,
        phase="3",
        command="write",
        agent_role="writer",
        chapter=1,
        arc=1,
        input_paths=("outlines/arc_1/chapter_001_outline.md",),
        output_paths=("drafts/chapter_0001.md",),
        context_query="chương 1",
    )

    result = _NoCastLoop(
        client=_SequenceClient(), max_revisions=1
    ).draft(step, ws)

    saved = ws.read("drafts/chapter_0001.md")
    assert result.outcome == "done"
    assert "cùng ta" in saved
    assert "tao" not in saved


def test_revise_prompt_includes_strict_config_contract():
    class _CaptureClient:
        def __init__(self):
            self.user = ""

        def complete(self, *, user="", **_kwargs):  # noqa: ANN003
            self.user = user
            return "Kỷ Trụ lặng lẽ bước vào cổ miếu."

    ws = _anti_slop_ws("Nội dung sạch.", flag_on=True)
    client = _CaptureClient()
    step = LoopStep(
        task_key="chapter.0001.review",
        stage=LoopStage.CRITIQUE,
        phase="review",
        command="review",
        agent_role="writer",
        chapter=1,
        arc=1,
        input_paths=("drafts/chapter_0001.md",),
        output_paths=("reviews/chapter_0001_review.json",),
        context_query=None,
    )

    LLMAutoNovelLoop(client=client)._revise_chapter(
        step,
        ws,
        1,
        ws.read("drafts/chapter_0001.md"),
        "Cần sửa văn phong.",
    )

    assert "REGISTER CONTRACT TỪ CONFIG" in client.user
    assert "đại từ khẩu ngữ tao/mày" in client.user


def test_reviewer_prompt_includes_strict_config_contract():
    class _CaptureClient:
        def __init__(self):
            self.user = ""

        def complete(self, *, user="", **_kwargs):  # noqa: ANN003
            self.user = user
            return (
                "## Author Style Gate: PASS\n"
                "## Worldbuilding Gate: PASS\n"
                "## Verdict: PASS\n"
                "**Điểm:** 90/100"
            )

    ws = _anti_slop_ws("Nội dung sạch.", flag_on=True)
    client = _CaptureClient()
    step = LoopStep(
        task_key="chapter.0001.review",
        stage=LoopStage.CRITIQUE,
        phase="review",
        command="review",
        agent_role="reviewer",
        chapter=1,
        arc=1,
        input_paths=("drafts/chapter_0001.md",),
        output_paths=("reviews/chapter_0001_review.json",),
        context_query=None,
    )

    LLMAutoNovelLoop(client=client)._critique_once(
        step, ws, ws.read("drafts/chapter_0001.md")
    )

    assert "REGISTER CONTRACT TỪ CONFIG" in client.user
    assert "đại từ khẩu ngữ tao/mày" in client.user


def test_revise_repairs_config_violation_before_next_review():
    class _SequenceClient:
        def __init__(self):
            self.responses = [
                'A Mãnh gọi: "Trụ ơi, trở về dùng bữa với tao!"',
                'A Mãnh gọi: "Trụ ca, trở về dùng bữa cùng ta!"',
            ]

        def complete(self, **_kwargs):  # noqa: ANN003
            return self.responses.pop(0)

    ws = _anti_slop_ws("Nội dung sạch.", flag_on=True)
    step = LoopStep(
        task_key="chapter.0001.review",
        stage=LoopStage.CRITIQUE,
        phase="review",
        command="review",
        agent_role="writer",
        chapter=1,
        arc=1,
        input_paths=("drafts/chapter_0001.md",),
        output_paths=("reviews/chapter_0001_review.json",),
        context_query=None,
    )

    revised = LLMAutoNovelLoop(
        client=_SequenceClient(), max_revisions=1
    )._revise_chapter(
        step,
        ws,
        1,
        ws.read("drafts/chapter_0001.md"),
        "Cần sửa văn phong.",
    )

    assert "cùng ta" in revised
    assert "tao" not in revised
    assert ws.read("drafts/chapter_0001.md") == revised


def test_anti_slop_noop_when_flag_off():
    """Flag OFF → _anti_slop_feedback is a pure no-op (no block, no hint),
    so a flags-off deploy behaves exactly as before."""
    ws = _anti_slop_ws("Chương có từ pipeline và metadata lộ liễu.", flag_on=False)
    loop = LLMAutoNovelLoop(client=_FakeClient())
    block, hint = loop._anti_slop_feedback(ws, ws.read("drafts/chapter_0001.md"))
    assert block is False
    assert hint == ""


def test_anti_slop_blocks_on_operational_error_term():
    """Flag ON + an operational 'error' term (e.g. 'pipeline') present →
    block_requested True and a concrete replacement hint is produced."""
    ws = _anti_slop_ws(
        "Hắn vận công, nhưng pipeline linh khí trong metadata đan điền rối loạn.",
        flag_on=True,
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())
    block, hint = loop._anti_slop_feedback(ws, ws.read("drafts/chapter_0001.md"))
    assert block is True
    assert "NGÔN TỪ CẤM" in hint


def test_anti_slop_blocks_profile_warning_under_strict_classical_config():
    ws = _anti_slop_ws(
        "Hắn mở hồ sơ, cân nhắc logic của vụ việc.",
        flag_on=True,
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())

    block, hint = loop._anti_slop_feedback(
        ws, ws.read("drafts/chapter_0001.md")
    )

    assert block is True
    assert "hồ sơ" in hint


def test_anti_slop_clean_prose_does_not_block():
    """Flag ON but clean cổ-phong prose → no operational error term → no block."""
    ws = _anti_slop_ws(
        "Hắn vận công một vòng chu thiên, linh khí trong đan điền dần lắng lại.",
        flag_on=True,
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())
    block, _hint = loop._anti_slop_feedback(ws, ws.read("drafts/chapter_0001.md"))
    assert block is False


def test_anti_slop_never_raises_on_empty_text():
    """Empty draft is a clean no-op (never raises)."""
    ws = _anti_slop_ws("", flag_on=True)
    loop = LLMAutoNovelLoop(client=_FakeClient())
    block, hint = loop._anti_slop_feedback(ws, "")
    assert block is False


def test_unresolved_language_guard_error_caps_review_after_repairs():
    """An objective lexical error must not pass after the repair budget expires."""
    loop = LLMAutoNovelLoop(client=_FakeClient())
    score, verdict = loop._apply_language_guard_penalty(True, 97.0, "pass")
    assert score == 69.0
    assert verdict == "hard_fail"


def test_critique_cannot_emit_passing_review_for_unrepaired_register_error():
    class _StubbornLoop(LLMAutoNovelLoop):
        def _critique_once(self, step, ws, chapter_text):  # noqa: ANN001
            return (
                "## Author Style Gate: PASS\n"
                "## Worldbuilding Gate: PASS\n"
                "## Verdict: PASS\n"
                "**Điểm:** 97/100"
            )

        def _revise_chapter(  # noqa: ANN001
            self, step, ws, ch, chapter_text, review_text
        ):
            return chapter_text

    bad_sentence = (
        "Trụ ơi, tối rồi về ăn cơm với tao; sao mày không nói sớm? "
        "A Mãnh là thằng bạn từ nhỏ của hắn. "
    )
    ws = _anti_slop_ws(bad_sentence * 15, flag_on=True)
    step = LoopStep(
        task_key="chapter.0001.review",
        stage=LoopStage.CRITIQUE,
        phase="review",
        command="review",
        agent_role="reviewer",
        chapter=1,
        arc=1,
        input_paths=("drafts/chapter_0001.md",),
        output_paths=("reviews/chapter_0001_review.json",),
        context_query=None,
    )

    result = _StubbornLoop(client=_FakeClient(), max_revisions=1).critique(step, ws)
    review = json.loads(ws.read("reviews/chapter_0001_review.json"))

    assert result.score == 69.0
    assert review["gate_outcome"] == "rewrite"
    assert review["final_action"] == "queue_rewrite"


def test_anti_slop_allows_declared_modern_xianxia_register():
    ws = _anti_slop_ws("Tao nói mày nghe, đừng bước qua cửa ấy.", flag_on=True)
    ws.write(
        "PROJECT_DNA.fields.json",
        json.dumps({"world_era": "Tu tiên đô thị hiện đại"}),
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())

    block, _hint = loop._anti_slop_feedback(
        ws, ws.read("drafts/chapter_0001.md")
    )

    assert block is False


# --------------------------------------------------------------------------- #
# Genre resolution for hybrid novels (regression: hybrid disabled lexical guard)
# --------------------------------------------------------------------------- #


def test_genre_hybrid_resolves_to_primary_not_hybrid():
    """A hybrid DNA has ``genre: hybrid`` BEFORE ``genre_primary: xianxia``.
    The resolver must return the primary genre (which has a language-guard
    profile), never the bare routing marker ``hybrid`` (which has none and
    silently disabled the lexical guard for every hybrid novel)."""
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.md",
        "---\ngenre: hybrid\ngenre_primary: xianxia\n"
        "genre_secondary: romance\nstyle_model: TD\n---\n",
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())
    assert loop._genre(ws) == "xianxia"
    assert loop._genre_secondary(ws) == "romance"


def test_genre_plain_xianxia_still_resolves():
    """A single-genre DNA (no genre_primary) still resolves via the bare key."""
    ws = _workspace()
    ws.write("PROJECT_DNA.md", "---\ngenre: xianxia\n---\n")
    loop = LLMAutoNovelLoop(client=_FakeClient())
    assert loop._genre(ws) == "xianxia"
    assert loop._genre_secondary(ws) == ""


def test_dna_cap_keeps_late_sections_reachable():
    """The DNA read cap must be large enough that late-but-critical sections
    (Anti-AI checklist, style-execution) reach the model. The real novel's DNA
    is ~13K chars; a marker past 8K must survive the read."""
    ws = _workspace()
    # Filler pushes the marker to ~char 11.6K: past the old 8K cap but within the
    # raised cap, mirroring the real novel's ~13K DNA where the Anti-AI checklist
    # sits near char 9.6K.
    filler = "\n".join(f"- dòng đệm số {i}" for i in range(650))
    marker = "MARKER_ANTI_AI_CHECKLIST_CUOI_FILE"
    ws.write("PROJECT_DNA.md", f"---\ngenre_primary: xianxia\n---\n{filler}\n{marker}\n")
    loop = LLMAutoNovelLoop(client=_FakeClient())
    dna = loop._dna(ws)
    assert marker in dna, "late DNA section was truncated by the read cap"


# --------------------------------------------------------------------------- #
# DNA digest — compact, writing-focused DNA for prose stages
# --------------------------------------------------------------------------- #


def test_dna_digest_from_sidecar_keeps_craft_drops_scaffolding():
    """With a fields.json sidecar, the digest keeps writing-craft fields (voice,
    style execution, MC spine, scene promise) and omits project scaffolding
    (routing table, pre-flight, arc grid) — and is far shorter than full DNA."""
    ws = _workspace()
    # A bloated full-text DNA whose scaffolding must NOT leak into the digest.
    ws.write(
        "PROJECT_DNA.md",
        "---\ngenre_primary: xianxia\n---\n## II. THỂ LOẠI & ROUTING\n"
        "| Tiên Hiệp | sub_agents | system/Xianxia |\n"
        "## XIII. SỔ KIỂM KHỞI TẠO (Pre-flight)\nMARKER_PREFLIGHT_SCAFFOLD\n"
        + ("- đệm dài dòng\n" * 400),
    )
    ws.write(
        "PROJECT_DNA.fields.json",
        json.dumps(
            {
                "title": "Ta Từng Là Thiên Đế",
                "logline": "Thiên Đế bị phản bội, trùng sinh báo thù.",
                "genre_primary": "xianxia",
                "tone": "ngược tâm, lạnh, u ám thi ca",
                "style_execution": "Câu biến thiên, ẩn dụ máu-kiếm, khoảng lặng.",
                "mc_want": "Báo thù kẻ phản bội",
                "mc_need": "Học cách tin lại",
                "mc_lie": "Yêu thương là yếu đuối",
                "mc_voice": "Trầm, ít lời, mỗi câu như đao",
                "scene_promise": "Mỗi chương một cú sốc hoặc mảnh ký ức đau",
                "scene_vitality_contract": "Mỗi cảnh phải có xung đột hoặc tiết lộ. Không cảnh chết.",
            },
            ensure_ascii=False,
        ),
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())
    digest = loop._dna_digest(ws)

    # Craft signal present.
    assert "ngược tâm" in digest
    assert "Câu biến thiên" in digest
    assert "Yêu thương là yếu đuối" in digest  # MC lie
    assert "cú sốc" in digest  # scene promise
    # Regression: the sidecar key is ``scene_vitality_contract`` (not
    # ``scene_vitality``); a key typo silently dropped this field from the digest.
    assert "Không cảnh chết" in digest  # scene vitality contract
    # Scaffolding absent.
    assert "MARKER_PREFLIGHT_SCAFFOLD" not in digest
    assert "ROUTING" not in digest
    # Much smaller than the full document.
    assert len(digest) < len(loop._dna(ws))


def test_dna_digest_falls_back_to_full_text_without_sidecar():
    """No fields.json (legacy/hand-made novel) → digest == full-text DNA, so the
    contract is never lost."""
    ws = _workspace()
    body = "---\ngenre_primary: xianxia\n---\n## I. HẠT GIỐNG\n- Logline: X\n"
    ws.write("PROJECT_DNA.md", body)
    loop = LLMAutoNovelLoop(client=_FakeClient())
    assert loop._dna_digest(ws) == loop._dna(ws)


def test_dna_tail_reminder_echoes_voice_and_anti_ai():
    """The tail reminder echoes the master voice + a standing anti-AI cấm kỵ so
    the craft floor survives at the prompt tail (lost-in-the-middle guard)."""
    ws = _workspace()
    ws.write("PROJECT_DNA.md", "---\ngenre_primary: xianxia\n---\n")
    ws.write(
        "PROJECT_DNA.fields.json",
        json.dumps({"tone": "u ám thi ca, ngược tâm"}, ensure_ascii=False),
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())
    tail = loop._dna_tail_reminder(ws)
    assert "u ám thi ca" in tail          # voice echoed
    assert "CẤM" in tail                   # anti-AI floor echoed
    assert "không chạm đến mắt" in tail    # translated-cliché ban echoed


def test_dna_tail_reminder_keeps_vn_contract_when_tone_is_hai_lay():
    """A broad tone may colour VN prose, but must not replace its style contract.

    Regression: ``tone or style_execution`` selected only ``hài lầy`` and
    silently dropped the detailed VN execution contract from the prompt tail.
    """
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.md",
        "---\ngenre_primary: xianxia\nstyle_model: VN\n---\n",
    )
    ws.write(
        "PROJECT_DNA.fields.json",
        json.dumps(
            {
                "genre": "xianxia",
                "style_model": "VN",
                "tone": "hài lầy",
                "style_execution": "Câu vừa làm trục, nhân quả và tài nguyên phải rõ.",
            },
            ensure_ascii=False,
        ),
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())
    tail = loop._dna_tail_reminder(ws)

    assert "hài lầy" in tail
    assert "Câu vừa làm trục" in tail
    assert "tiếng lóng hiện đại" in tail
    assert "không quá 2 câu cực ngắn" in tail


def test_dna_tail_reminder_keeps_author_codes_as_neutral_metadata():
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.md",
        "---\ngenre_primary: xianxia\nstyle_model: VN\nstyle_blend: CM\n---\n",
    )
    ws.write(
        "PROJECT_DNA.fields.json",
        json.dumps(
            {
                "genre": "xianxia",
                "genre_secondary": "romance",
                "style_model": "VN",
                "style_secondary": "CM",
            }
        ),
    )
    tail = LLMAutoNovelLoop(client=_FakeClient())._dna_tail_reminder(ws)
    assert "THAM CHIẾU TÁC GIẢ: chính=VN; phụ=CM" in tail
    assert "không suy luận hoặc mô phỏng văn phong" in tail
    assert "PHONG CÁCH KHÓA" not in tail
