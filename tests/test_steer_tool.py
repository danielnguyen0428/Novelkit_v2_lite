"""Realtime steer router + recovery (Req 9; Property P22)."""

from __future__ import annotations

import pytest

import bootstrap  # noqa: F401
from delegate import delegate_tool
from tools.novelkit_pipeline_tool import PipelineEngine, PipelineState
from tools.novelkit_rules_tool import current_rules_digest, load_rules_snapshot
from tools.novelkit_steer_tool import ROUTES, apply, classify


@pytest.mark.parametrize(
    "text,route",
    [
        ("mỗi chương 1500 từ", "style_rule"),
        ("ít dùng so sánh", "style_rule"),
        ("viết lại chương 3", "rewrite_existing"),
        ("tăng lên 40 chương", "scope_change"),
        ("từ chương 30 main lạnh hơn", "plot_or_character"),
        ("thêm một phản diện mới", "plot_or_character"),
        ("tiếp tục đi", "none"),
        ("hiện trạng thế nào", "answer"),
    ],
)
def test_classify_one_route(text, route):
    intent = classify(text)
    assert intent.route == route
    assert intent.route in ROUTES


def test_classify_is_deterministic():
    a = classify("viết lại chương 7")
    b = classify("viết lại chương 7")
    assert a == b and a.steer_id == b.steer_id  # P22


def test_rewrite_extracts_affected_chapters():
    intent = classify("viết lại chương 3")
    assert intent.kind == "modify" and intent.affected_chapters == (3,)


def test_apply_enqueues_rewrite_and_is_idempotent(tmp_path):
    state = PipelineEngine.create(target_chapters=10, novel="x").state.to_dict()
    out1 = apply(tmp_path, "viết lại chương 3", state)
    assert out1["route"] == "rewrite_existing"
    assert out1["affected_chapters"] == [3]
    rq = out1["state"]["creative"]["rewrite_queue"]
    assert any(item["chapter"] == 3 for item in rq)
    # re-applying the same steer is a no-op (P22 idempotent)
    out2 = apply(tmp_path, "viết lại chương 3", out1["state"])
    assert out2["applied"] is False
    rq2 = out2["state"]["creative"]["rewrite_queue"]
    assert len(rq2) == len(rq)


def test_pending_steer_survives_resume(tmp_path):
    state = PipelineEngine.create(target_chapters=10, novel="x").state.to_dict()
    out = apply(tmp_path, "tăng lên 40 chương", state)
    assert out["state"]["creative"]["pending_steer"]["route"] == "scope_change"
    # round-trip through resume must keep pending_steer (P22 recovery)
    engine = PipelineEngine(PipelineState.from_dict(out["state"]))
    engine.resume()
    assert engine.state.creative.pending_steer is not None
    assert engine.state.creative.pending_steer["route"] == "scope_change"


def test_continue_is_noop(tmp_path):
    state = PipelineEngine.create(target_chapters=10, novel="x").state.to_dict()
    out = apply(tmp_path, "tiếp tục đi", state)
    assert out["applied"] is False
    assert out["state"]["creative"].get("pending_steer") is None


# --- route execution (seam #2): apply performs the deterministic side-effect - #


def test_style_rule_writes_rule_snapshot(tmp_path):
    state = PipelineEngine.create(target_chapters=10, novel="x").state.to_dict()
    out = apply(tmp_path, "mỗi chương 1500 từ", state)
    assert out["route"] == "style_rule" and out["applied"] is True
    assert out["executed"]["executed"] == "style_rule"
    assert out["executed"]["changed"] is True
    snapshot = load_rules_snapshot(tmp_path)
    assert snapshot is not None
    texts = [r["text"] for r in snapshot["rules"]]
    assert "mỗi chương 1500 từ" in texts
    # the reported digest matches what is persisted on disk
    assert out["executed"]["rules_digest"] == current_rules_digest(tmp_path)


def test_scope_change_records_reseed_due_action(tmp_path):
    state = PipelineEngine.create(target_chapters=10, novel="x").state.to_dict()
    out = apply(tmp_path, "tăng lên 40 chương", state)
    assert out["route"] == "scope_change"
    reseeds = [
        d for d in out["state"]["creative"]["due_actions"] if d["kind"] == "reseed"
    ]
    assert reseeds and reseeds[0]["target_chapters"] == 40
    assert reseeds[0]["source_steer"] == out["steer_id"]
    # no compass present ⇒ nothing to update, but intent is still recorded
    assert out["executed"]["compass_updated"] is False


def test_scope_change_updates_compass_when_present(tmp_path):
    from tools.novelkit_compass_tool import read_compass, update_compass

    update_compass(
        tmp_path,
        ending_direction="chủ đạt đạo, thoát tục",
        active_long_threads=[{"id": "t1", "text": "mối thù sư môn"}],
        scale_estimate={"chapters": 300, "volumes": 6},
    )
    state = PipelineEngine.create(target_chapters=300, novel="x").state.to_dict()
    out = apply(tmp_path, "kéo dài lên 500 chương", state)
    assert out["route"] == "scope_change"
    assert out["executed"]["compass_updated"] is True
    compass = read_compass(tmp_path)
    assert compass["scale_estimate"]["chapters"] == 500
    # unrelated fields are preserved through the retarget
    assert compass["ending_direction"] == "chủ đạt đạo, thoát tục"
    assert compass["active_long_threads"][0]["id"] == "t1"


def test_plot_steer_records_due_action(tmp_path):
    state = PipelineEngine.create(target_chapters=10, novel="x").state.to_dict()
    out = apply(tmp_path, "từ chương 30 main lạnh hơn", state)
    assert out["route"] == "plot_or_character"
    das = out["state"]["creative"]["due_actions"]
    assert any(
        d["kind"] == "plot_or_character" and d["source_steer"] == out["steer_id"]
        for d in das
    )


def test_apply_is_idempotent_via_log_even_if_pending_cleared(tmp_path):
    state = PipelineEngine.create(target_chapters=10, novel="x").state.to_dict()
    out1 = apply(tmp_path, "ít dùng so sánh", state)
    assert out1["applied"] is True
    # simulate a downstream consumer clearing pending_steer after execution
    cleared = out1["state"]
    cleared["creative"]["pending_steer"] = None
    out2 = apply(tmp_path, "ít dùng so sánh", cleared)
    assert out2["applied"] is False  # log-based idempotency (review #16)
    # and the rule snapshot has no duplicate
    texts = [r["text"] for r in load_rules_snapshot(tmp_path)["rules"]]
    assert texts.count("ít dùng so sánh") == 1
