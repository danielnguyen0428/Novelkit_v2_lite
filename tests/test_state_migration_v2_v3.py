"""PipelineState v2→v3 migration + backward compatibility (Req 11; Property P24)."""

from __future__ import annotations

from tools.novelkit_pipeline_tool import (
    PIPELINE_SCHEMA_VERSION,
    PipelineEngine,
    PipelineState,
    migrate_state,
)


def _v2_payload() -> dict:
    return {
        "schema_version": 2,
        "state_version": 5,
        "novel": "x",
        "tasks": [],
        "breaker": {},
        "creative": {"mode": "rolling", "expanded_through_chapter": 0},
        "target_chapters": 300,
        "arc_size": 50,
        "window_size": 5,
        "min_remaining": 3,
    }


def test_v2_loads_without_error_and_keeps_mode():
    st = PipelineState.from_dict(_v2_payload())
    assert st.creative.mode == "rolling"  # legacy mode preserved (P24)
    assert st.creative.arc_map_digest is None
    assert st.creative.pending_steer is None
    assert st.creative.stop_block_count == 0


def test_migrate_v2_to_v3_idempotent():
    m1 = migrate_state(_v2_payload())
    m2 = migrate_state(m1)
    assert m1["schema_version"] == 3 == PIPELINE_SCHEMA_VERSION
    assert m1 == m2  # idempotent (P24)


def test_default_creative_serialises_without_new_keys():
    """A default CreativeState must NOT emit the new v3 keys, so a legacy
    state digest stays byte-identical on first load (P24)."""
    eng = PipelineEngine.create(target_chapters=50, novel="n")
    creative = eng.state.to_dict()["creative"]
    assert "arc_map_digest" not in creative
    assert "pending_steer" not in creative
    assert "stop_block_count" not in creative


def test_new_keys_emitted_when_set():
    eng = PipelineEngine.create(target_chapters=50, novel="n")
    eng.state.creative.arc_map_digest = "sha256:abc"
    eng.state.creative.pending_steer = {"steer_id": "s1", "route": "style_rule"}
    eng.state.creative.stop_block_count = 2
    creative = eng.state.to_dict()["creative"]
    assert creative["arc_map_digest"] == "sha256:abc"
    assert creative["pending_steer"]["route"] == "style_rule"
    assert creative["stop_block_count"] == 2


def test_migrate_defaults_expanded_through_to_max_chapter():
    payload = _v2_payload()
    payload["creative"] = {"mode": "compass", "expanded_through_chapter": 0}
    # add a chapter task so chapter_numbers() is non-empty
    payload["tasks"] = [
        {
            "task_key": "chapter.0003.outline",
            "phase": "2",
            "agent_role": "Plot Weaver",
            "command": "OUTLINE_CHAPTER",
            "priority": 130,
            "chapter": 3,
        }
    ]
    m1 = migrate_state(payload)
    assert m1["creative"]["expanded_through_chapter"] == 3
    assert migrate_state(m1) == m1  # still idempotent
