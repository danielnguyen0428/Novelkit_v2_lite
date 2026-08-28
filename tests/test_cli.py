"""CLI surface smoke tests (Task 11.3).

Exercises the CLI entrypoint end-to-end over the registered tools (hub-and-spoke):
- ``tools`` lists the registered surface;
- ``schedule`` loads the declarative cron config (style audit every 10 chapters
  + rolling seed);
- ``pipeline init → plan-next → record-result → resume`` drives the DAG via the
  ``novelkit_pipeline`` tool and persists state to a JSON file;
- ``sync`` commits a chapter and ``doctor`` runs the health-check on a fixture
  novel via the ``novelkit_sync`` tool.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

import bootstrap
import cli
from tools.novelkit_pipeline_state_store import PipelineStateConflict, PipelineStateStore
from tools.novelkit_pipeline_tool import PipelineEngine, PipelineState, TaskStatus

_PASSING_REVIEW = """# Review chapter

**Trạng thái:** PASS

**Điểm:** 91/100
"""

_CHAPTER_TEXT = (
    "Hắn bước vào sảnh đường rộng lớn, ánh nến lập lòe trên những cây cột đá.\n\n"
    "Người gác cổng cúi đầu chào. Hắn gật đầu rồi sải bước về phía ngai vàng.\n\n"
    "Bên ngoài, mưa bắt đầu rơi, gột rửa bụi đường trên vai áo bạc màu."
)


def _make_novel(name: str = "cli-novel") -> Path:
    novel = Path(tempfile.mkdtemp()) / name
    for sub in ("chapters", "reviews", "memory", "logs"):
        (novel / sub).mkdir(parents=True)
    (novel / "PROJECT_DNA.md").write_text(
        "---\ntitle: Demo\ngenre: xianxia\ntarget_chapters: 50\n---\n", encoding="utf-8"
    )
    (novel / "PLAN.md").write_text("# PLAN\n", encoding="utf-8")
    (novel / "GOAL_TRACKER.md").write_text("# GOAL TRACKER\n", encoding="utf-8")
    (novel / "memory" / "Memory.md").write_text("# Memory\n", encoding="utf-8")
    (novel / "logs" / "pipeline_status.json").write_text(
        json.dumps(
            {
                "novel": name,
                "status": "running",
                "circuit_breaker": {
                    "hard_fail_count": 0,
                    "soft_fail_count": 0,
                    "total_attempts": 0,
                    "max_hard_fail": 2,
                    "max_soft_fail": 3,
                    "max_total": 5,
                },
            }
        ),
        encoding="utf-8",
    )
    (novel / "chapters" / "chapter_001.md").write_text(_CHAPTER_TEXT, encoding="utf-8")
    (novel / "reviews" / "chapter_001_review.md").write_text(
        _PASSING_REVIEW, encoding="utf-8"
    )
    return novel


def test_cli_tools_lists_surface(capsys) -> None:
    assert cli.main(["tools"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert bootstrap.EXPECTED_TOOLS <= set(out)


def test_cli_schedule_loads_cron_jobs(capsys) -> None:
    assert cli.main(["schedule"]) == 0
    out = json.loads(capsys.readouterr().out)
    job_names = {job["name"] for job in out["jobs"]}
    assert {"style_audit", "rolling_seed"} <= job_names
    style = next(j for j in out["jobs"] if j["name"] == "style_audit")
    assert style["trigger"]["every_chapters"] == 10
    assert style["tool"] == "novelkit_style_coherence"


def test_cli_pipeline_init_and_plan_next(capsys) -> None:
    state_file = Path(tempfile.mkdtemp()) / "state.json"
    assert cli.main(["pipeline", "init", "--state", str(state_file), "--target-chapters", "10"]) == 0
    capsys.readouterr()
    assert state_file.exists()

    # plan-next returns the first ready task (a bootstrap task).
    assert cli.main(["pipeline", "plan-next", "--state", str(state_file)]) == 0
    task = json.loads(capsys.readouterr().out)
    assert task is not None
    assert "task_key" in task


def test_cli_pipeline_init_writes_standard_status_projection(capsys) -> None:
    novel_root = Path(tempfile.mkdtemp())
    state_file = novel_root / "logs" / "pipeline_state.json"

    assert cli.main(["pipeline", "init", "--state", str(state_file), "--target-chapters", "2"]) == 0
    capsys.readouterr()

    state = json.loads(state_file.read_text())
    status = json.loads((novel_root / "logs" / "pipeline_status.json").read_text())
    assert status["source_state_version"] == state["state_version"]
    assert status["source_state_digest"] == state["state_digest"]


def test_cli_pipeline_record_result_and_resume(capsys) -> None:
    state_file = Path(tempfile.mkdtemp()) / "state.json"
    cli.main(["pipeline", "init", "--state", str(state_file), "--target-chapters", "10"])
    capsys.readouterr()

    cli.main(["pipeline", "plan-next", "--state", str(state_file), "--claim"])
    task = json.loads(capsys.readouterr().out)
    first_key = task["task_key"]

    assert cli.main(
        ["pipeline", "record-result", "--state", str(state_file), "--task-key", first_key, "--result", "done"]
    ) == 0
    capsys.readouterr()

    # Resume continues from the next ready task without re-running the done one.
    assert cli.main(["pipeline", "resume", "--state", str(state_file)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["next_task_key"] != first_key
    assert report["done_count"] >= 1


def test_cli_pipeline_mutation_refuses_stale_state(capsys, monkeypatch) -> None:
    state_file = Path(tempfile.mkdtemp()) / "state.json"
    cli.main(["pipeline", "init", "--state", str(state_file), "--target-chapters", "2"])
    capsys.readouterr()
    store = PipelineStateStore.from_state_path(state_file)
    before = store.load_payload()

    def _racing_delegate(_tool_name, *, state, **_kwargs):  # noqa: ANN001
        fresh = PipelineEngine(PipelineState.from_dict(state))
        claimed = fresh.plan_next(claim=True)
        assert claimed is not None
        store.save(fresh.state, expected_version=state["state_version"])
        return {"result": {"ok": True}, "state": state}

    monkeypatch.setattr(cli, "delegate_tool", _racing_delegate)

    with pytest.raises(PipelineStateConflict):
        cli.main(
            [
                "pipeline",
                "record-result",
                "--state",
                str(state_file),
                "--task-key",
                "bootstrap.characters",
                "--result",
                "done",
            ]
        )

    after = store.load_payload()
    assert after["state_version"] == before["state_version"] + 1
    claimed = next(t for t in after["tasks"] if t["task_key"] == "bootstrap.characters")
    assert claimed["status"] == TaskStatus.IN_PROGRESS.value


def test_cli_sync_commits_chapter(capsys) -> None:
    novel = _make_novel()
    rc = cli.main(["sync", "--novel", str(novel), "--chapter", "1"])
    out = json.loads(capsys.readouterr().out)
    assert "stages" in out
    # A passing chapter should not be blocked → exit 0.
    assert rc == 0


def test_cli_doctor_runs(capsys) -> None:
    novel = _make_novel()
    rc = cli.main(["doctor", "--novel", str(novel)])
    out = json.loads(capsys.readouterr().out)
    assert "issues" in out and "blocking_issues" in out
    assert rc in (0, 1)


def test_cli_requires_subcommand() -> None:
    with pytest.raises(SystemExit):
        cli.main([])
