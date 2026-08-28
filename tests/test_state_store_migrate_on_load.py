"""Store auto-migrates a legacy v2 state payload on load (seam #4; P24)."""

from __future__ import annotations

import json

from tools.novelkit_pipeline_state_store import PipelineStateStore
from tools.novelkit_pipeline_tool import PIPELINE_SCHEMA_VERSION, PipelineState


def _v2() -> dict:
    return {
        "schema_version": 2, "state_version": 5, "novel": "x", "tasks": [],
        "breaker": {}, "creative": {"mode": "rolling"},
        "target_chapters": 300, "arc_size": 50, "window_size": 5, "min_remaining": 3,
    }


def _write(store: PipelineStateStore, payload: dict) -> None:
    store.state_path.parent.mkdir(parents=True, exist_ok=True)
    store.state_path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_migrates_v2_without_digest(tmp_path):
    store = PipelineStateStore(tmp_path)
    _write(store, _v2())  # no state_digest → validation skipped
    payload = store.load_payload()
    assert payload["schema_version"] == PIPELINE_SCHEMA_VERSION == 3
    assert store.load_state().creative.mode == "rolling"  # legacy mode preserved


def test_load_migrates_v2_with_valid_digest(tmp_path):
    store = PipelineStateStore(tmp_path)
    # A realistic on-disk v2 payload carries a matching digest.
    v2_on_disk = PipelineState.from_dict(_v2()).to_dict()
    assert v2_on_disk["schema_version"] == 2  # from_dict preserves the source schema
    _write(store, v2_on_disk)
    payload = store.load_payload()  # validate v2 digest → then migrate
    assert payload["schema_version"] == 3
    # migrated payload has its own valid v3 digest
    assert payload["state_digest"] == PipelineState.from_dict(payload).to_dict()["state_digest"]


def test_load_v3_is_noop(tmp_path):
    store = PipelineStateStore(tmp_path)
    v3 = PipelineState.from_dict({"schema_version": 3, "novel": "x"}).to_dict()
    _write(store, v3)
    payload = store.load_payload()
    assert payload["schema_version"] == 3
    assert payload["state_digest"] == v3["state_digest"]  # unchanged
