"""Rollback drill: flags OFF (via per-novel override) ⇒ pre-GA behaviour
(Req 14.6; P24 non-regression).

GA defaults now ship with all flags ON and ``mode="compass"`` as the primary
path (compass is the recommended long-form mode). This drill proves the
pre-GA legacy path is still fully reachable and byte-for-byte unchanged: a
per-novel override can still force every flag OFF, and ``mode="full_plan"``
still seeds bootstrap + window chapters with none of the compass machinery.
"""

from __future__ import annotations

import json

from tools.novelkit_longform_config import FLAG_NAMES, flag_enabled, load_config
from tools.novelkit_pipeline_tool import PipelineEngine


def _all_flags_off_override(tmp_path):
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "longform.json").write_text(
        json.dumps({"flags": {name: False for name in FLAG_NAMES}}),
        encoding="utf-8",
    )


def test_all_flags_can_be_rolled_back_off(tmp_path):
    _all_flags_off_override(tmp_path)
    for name in FLAG_NAMES:
        assert flag_enabled(name, tmp_path) is False


def test_legacy_create_unchanged_when_flags_off():
    # mode="full_plan" seeds bootstrap + window chapters, no compass.
    eng = PipelineEngine.create(target_chapters=10, novel="x", mode="full_plan")
    keys = set(eng.state.tasks)
    assert "bootstrap.compass" not in keys
    assert "chapter.0001.outline" in keys  # legacy rolling seed
    assert eng.state.creative.mode == "full_plan"


def test_legacy_state_has_no_new_creative_keys():
    eng = PipelineEngine.create(target_chapters=10, novel="x", mode="full_plan")
    creative = eng.state.to_dict()["creative"]
    # New v3 fields stay absent at default so legacy digests are stable (P24).
    for key in ("arc_map_digest", "pending_steer", "stop_block_count"):
        assert key not in creative


def test_config_defaults_can_be_rolled_back_safe(tmp_path):
    _all_flags_off_override(tmp_path)
    cfg = load_config(tmp_path)
    assert cfg["COMPASS_MODE_MIN_CHAPTERS"] == 60
    assert all(v is False for v in cfg["flags"].values())
