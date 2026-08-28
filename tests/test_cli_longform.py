"""CLI surface for long-form GA commands (Req 8.4, 9, 10, 14)."""

from __future__ import annotations

import json

from cli import main


def _init_state(tmp_path):
    state = tmp_path / "logs" / "pipeline_state.json"
    assert main([
        "pipeline", "init", "--state", str(state),
        "--target-chapters", "3", "--novel", "demo",
    ]) == 0
    return state


def test_stop_guard_exit_codes(tmp_path):
    state = _init_state(tmp_path)
    # fresh pipeline has ready work → blocked → exit 2
    assert main(["stop-guard", "--state", str(state)]) == 2


def test_stop_guard_escalates_after_repeated_blocks(tmp_path):
    # MAX_STOP_BLOCKS defaults to 3 → the 4th consecutive block escalates
    # (exit 0) instead of blocking forever (Req 8.4).
    state = _init_state(tmp_path)
    codes = [main(["stop-guard", "--state", str(state)]) for _ in range(4)]
    assert codes[:3] == [2, 2, 2]
    assert codes[3] == 0  # escalated → allowed to stop


def test_reminder_renders(tmp_path, capsys):
    state = _init_state(tmp_path)
    assert main(["reminder", "--state", str(state)]) == 0
    out = capsys.readouterr().out
    assert "<system-reminder>" in out


def test_steer_routes_and_persists(tmp_path, capsys):
    state = _init_state(tmp_path)
    capsys.readouterr()  # flush the init command's output
    rc = main(["steer", "--state", str(state), "--novel", str(tmp_path),
               "--text", "viết lại chương 2"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["route"] == "rewrite_existing"
    assert out["affected_chapters"] == [2]


def test_diag_runs(tmp_path, capsys):
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter_001.md").write_text("# c1", encoding="utf-8")
    (tmp_path / "chapters" / "chapter_003.md").write_text("# c3", encoding="utf-8")
    rc = main(["diag", "--novel", str(tmp_path)])
    assert rc == 0
    findings = json.loads(capsys.readouterr().out)
    assert any(f["code"] == "chapter_number_skip" for f in findings)


def test_compass_show_empty(tmp_path, capsys):
    rc = main(["compass", "--novel", str(tmp_path)])
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == {"compass": None}


def test_compass_migrate_cli(tmp_path, capsys):
    rc = main([
        "compass", "--novel", str(tmp_path), "--migrate",
        "--current-chapter", "12", "--target-chapters", "300",
    ])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["expanded_through_chapter"] == 12
    assert (tmp_path / "outlines" / "compass.md").exists()
    assert (tmp_path / "outlines" / "arc_map.json").exists()


def test_compass_migrate_requires_target(tmp_path):
    import pytest

    with pytest.raises(SystemExit):
        main(["compass", "--novel", str(tmp_path), "--migrate", "--current-chapter", "5"])


def test_pipeline_init_compass_mode(tmp_path, capsys):
    state = tmp_path / "logs" / "pipeline_state.json"
    rc = main([
        "pipeline", "init", "--state", str(state),
        "--target-chapters", "300", "--novel", "demo", "--mode", "compass",
    ])
    assert rc == 0
    payload = json.loads(state.read_text(encoding="utf-8"))
    assert payload["creative"]["mode"] == "compass"
    keys = {t["task_key"] for t in payload["tasks"]}
    assert "bootstrap.compass" in keys  # compass task seeded
    assert not any(k.startswith("chapter.") for k in keys)  # chapters expand on demand
