"""Guard: losing the long-form config must be loud, not silent."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import tools.novelkit_longform_config as lf


def test_missing_package_config_logs_an_error(tmp_path, monkeypatch, caplog):
    """A missing config disables all 12 flags — that must never be silent."""
    monkeypatch.setattr(lf, "PACKAGE_CONFIG_PATH", tmp_path / "gone.json")
    with caplog.at_level(logging.ERROR):
        cfg = lf.load_config()
    assert all(v is False for v in cfg["flags"].values())
    assert any("MISSING" in r.message or "MISSING" in r.getMessage()
               for r in caplog.records), caplog.text


def test_corrupt_package_config_logs_an_error(tmp_path, monkeypatch, caplog):
    bad = tmp_path / "longform.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(lf, "PACKAGE_CONFIG_PATH", bad)
    with caplog.at_level(logging.ERROR):
        lf.load_config()
    assert any("UNREADABLE" in r.getMessage() for r in caplog.records), caplog.text


def test_shipped_config_enables_the_flags():
    """The real shipped config must actually turn the features on."""
    cfg = lf.load_config()
    assert cfg["flags"], "no flags in the shipped config"
    enabled = [k for k, v in cfg["flags"].items() if v]
    assert enabled, "shipped longform.json enables zero features"


def test_optional_per_novel_override_stays_quiet(tmp_path, caplog):
    """A novel with no override is normal — it must not log an error."""
    with caplog.at_level(logging.ERROR):
        lf.load_config(tmp_path)
    assert not [r for r in caplog.records if "config" in r.getMessage().lower()
                and str(tmp_path) in r.getMessage()], caplog.text
