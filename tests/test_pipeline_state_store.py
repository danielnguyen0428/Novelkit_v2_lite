"""Tests for the shared PipelineState persistence boundary."""

from __future__ import annotations

import json

import pytest

from tools.novelkit_pipeline_state_store import (
    PipelineStateDigestError,
    PipelineStateStore,
)
from tools.novelkit_pipeline_tool import PipelineEngine


def test_state_store_saves_state_and_status_projection(tmp_path):
    store = PipelineStateStore(tmp_path)
    engine = PipelineEngine.create(target_chapters=2, arc_size=50, novel="demo")

    saved = store.save(engine.state)

    state = json.loads((tmp_path / "logs" / "pipeline_state.json").read_text())
    status = json.loads((tmp_path / "logs" / "pipeline_status.json").read_text())
    assert saved["state_digest"] == state["state_digest"]
    assert status["source_state_version"] == state["state_version"]
    assert status["source_state_digest"] == state["state_digest"]


def test_state_store_rejects_mismatched_state_digest(tmp_path):
    store = PipelineStateStore(tmp_path)
    engine = PipelineEngine.create(target_chapters=2, arc_size=50, novel="demo")
    store.save(engine.state)
    state_path = tmp_path / "logs" / "pipeline_state.json"
    payload = json.loads(state_path.read_text())
    payload["state_digest"] = "sha256:" + ("0" * 64)
    state_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PipelineStateDigestError):
        store.load_state()


def test_state_store_appends_checkpoint_with_artifact_hash(tmp_path):
    store = PipelineStateStore(tmp_path)
    engine = PipelineEngine.create(target_chapters=2, arc_size=50, novel="demo")
    store.save(engine.state)
    artifact = tmp_path / "drafts" / "chapter_0001.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("hello checkpoint", encoding="utf-8")

    first = store.append_checkpoint(
        task_key="chapter.0001.write",
        step="draft_completed",
        state=engine.state,
        input_digest="sha256:" + ("1" * 64),
        artifacts=["drafts/chapter_0001.md"],
    )
    second = store.append_checkpoint(
        task_key="chapter.0001.review",
        step="review_completed",
        state=engine.state,
        input_digest="sha256:" + ("2" * 64),
    )

    lines = (tmp_path / "logs" / "checkpoints.jsonl").read_text().splitlines()
    assert first["seq"] == 1
    assert second["seq"] == 2
    assert len(lines) == 2
    assert first["artifacts"][0]["path"] == "drafts/chapter_0001.md"
    assert len(first["artifacts"][0]["sha256"]) == 64
    assert first["artifacts"][0]["bytes"] == len("hello checkpoint".encode("utf-8"))
