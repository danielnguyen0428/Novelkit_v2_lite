"""Tests for the long-form GA config + flag loader (Req 14.1, 14.2)."""

from __future__ import annotations

import json

from tools.novelkit_longform_config import (
    DEFAULTS,
    FLAG_NAMES,
    flag_enabled,
    load_config,
)


def test_defaults_when_missing(tmp_path):
    cfg = load_config(tmp_path)  # tmp_path has no config/longform.json
    assert cfg["COMPASS_MODE_MIN_CHAPTERS"] == 60
    assert cfg["MIN_ARC_LEN"] == 8
    assert cfg["K_PER_DIM"] == 2
    assert cfg["STYLE_STATS_WINDOW"] == 10
    assert cfg["REPEAT_GUARD_WINDOW"] == 3
    assert cfg["flags"]["compass"] is True  # package config now ships flags ON


def test_module_defaults_are_safe_fallback():
    # The in-module DEFAULTS constant stays all-False: a safety net if the
    # package config file is ever missing/corrupted, load_config() still
    # falls back to the conservative rollout posture.
    assert set(DEFAULTS["flags"]) == set(FLAG_NAMES)
    assert all(value is False for value in DEFAULTS["flags"].values())


def test_all_flags_default_on():
    cfg = load_config()
    assert set(cfg["flags"]) == set(FLAG_NAMES)
    assert all(value is True for value in cfg["flags"].values())


def test_novel_override_wins(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "longform.json").write_text(
        json.dumps({"MIN_ARC_LEN": 12, "flags": {"compass": False}}),
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg["MIN_ARC_LEN"] == 12  # scalar overridden
    assert cfg["flags"]["compass"] is False  # nested flag overridden
    assert cfg["flags"]["recall"] is True  # other flags preserved (default ON)
    assert cfg["K_PER_DIM"] == 2  # untouched default preserved


def test_flag_enabled_helper(tmp_path):
    assert flag_enabled("compass", tmp_path) is True
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "longform.json").write_text(
        json.dumps({"flags": {"steer": False}}), encoding="utf-8"
    )
    assert flag_enabled("steer", tmp_path) is False
    assert flag_enabled("diag", tmp_path) is True


def test_defaults_constant_shape():
    assert "flags" in DEFAULTS and isinstance(DEFAULTS["flags"], dict)
