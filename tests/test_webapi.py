"""Smoke + behaviour tests for the FastAPI web surface (webapp.api).

Drives the HTTP API the React SPA consumes: meta endpoints, novel lifecycle
(create → detail), the pipeline board (plan-next/record-result/resume), and the
creative analysis passthroughs. The service writes into an isolated temp
workspace via NOVELKIT_WORKSPACE_ROOT so tests never touch real novels.
"""

from __future__ import annotations

import importlib
import json
import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    workspace = tempfile.mkdtemp()
    storage = tempfile.mkdtemp()
    monkeypatch.setenv("NOVELKIT_WORKSPACE_ROOT", workspace)
    monkeypatch.setenv("NOVELKIT_STORAGE_ROOT", storage)
    # Reimport the service + app so they pick up the temp workspace root.
    import webapp.api.service as service

    importlib.reload(service)
    import webapp.api.main as main

    importlib.reload(main)
    return TestClient(main.app)


def _fields(target: int = 2) -> dict:
    """Minimal valid PROJECT_DNA form payload."""
    return {
        "title": "Demo",
        "genre": "xianxia",
        "logline": "Một câu pitch thử nghiệm.",
        "target_chapters": target,
    }


# --------------------------------------------------------------------------- #
# Meta
# --------------------------------------------------------------------------- #


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["tools"] >= 10


def test_tools_lists_novelkit_tools(client):
    tools = client.get("/api/tools").json()
    assert "novelkit_pipeline" in tools
    assert "novelkit_sync" in tools


def test_inventory_coverage_complete(client):
    summary = client.get("/api/inventory").json()
    assert summary["coverage_complete"] is True
    assert summary["orphan_count"] == 0


def test_schedule_has_jobs(client):
    sched = client.get("/api/schedule").json()
    names = {j["name"] for j in sched.get("jobs", [])}
    assert {"style_audit", "rolling_seed"} <= names


# --------------------------------------------------------------------------- #
# Novel lifecycle
# --------------------------------------------------------------------------- #


def test_create_and_get_novel(client):
    r = client.post(
        "/api/novels",
        json={"name": "demo_one", "fields": _fields(3)},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "demo_one"
    assert body["target_chapters"] == 3
    # ready task is the first bootstrap task.
    assert body["ready_task"]["task_key"] == "bootstrap.characters"

    listing = client.get("/api/novels").json()
    assert any(n["name"] == "demo_one" for n in listing)


def test_dna_template_schema(client):
    sch = client.get("/api/dna-template").json()
    ids = {f["id"] for sec in sch["sections"] for f in sec["fields"]}
    assert {"title", "genre", "logline", "target_chapters"} <= ids
    assert "genre_template_files" in sch
    assert sch["genre_template_files"]["xianxia"].endswith("PROJECT_DNA_XIANXIA.md")
    assert "output_language_options" in sch
    assert any(o["value"] == "en" for o in sch["output_language_options"])


def test_created_dna_uses_genre_template(client):
    client.post("/api/novels", json={"name": "tpl_demo", "fields": _fields(2)})
    detail = client.get("/api/novels/tpl_demo").json()
    dna = detail["dna"]
    assert "## I. HẠT GIỐNG" in dna
    assert "sub_agents_squad: sub_agents" in dna
    assert "template_source: skills/novelkit-canon/templates/genres/PROJECT_DNA_XIANXIA.md" in dna
    # Xianxia genre template (not the unified 14-section layout).
    assert "## III. NHÂN VẬT CHÍNH (Tu Sĩ)" in dna
    assert "## VI. THẾ GIỚI TU CHÂN" in dna
    assert "## X. CỐT TRUYỆN" in dna
    assert "## XII. SỔ KIỂM KHỞI TẠO" in dna


def test_created_dna_hybrid_uses_unified_template(client):
    fields = {**_fields(5), "genre_secondary": "urban", "hybrid_ratio": "70-30"}
    client.post("/api/novels", json={"name": "hybrid_tpl", "fields": fields})
    dna = client.get("/api/novels/hybrid_tpl").json()["dna"]
    assert "template_source: templates/PROJECT_DNA_TEMPLATE.md" in dna
    assert "## II. THỂ LOẠI & ROUTING" in dna
    assert "## VIII. PHẢN DIỆN" in dna


def test_writing_dna_fields_resynchronizes_rendered_dna_and_routing_meta(client):
    client.post("/api/novels", json={"name": "dna_sync", "fields": _fields(8)})
    current = client.get(
        "/api/novels/dna_sync/artifact",
        params={"path": "PROJECT_DNA.fields.json"},
    ).json()
    fields = json.loads(current["text"])
    fields.update(
        {
            "genre_secondary": "romance",
            "hybrid_ratio": "80-20",
            "style_model": "VN",
            "style_secondary": "CM",
            "worldbuilding_guide": "VN",
            "tone": "trầm tĩnh, thực dụng, hài khô kín đáo",
            "style_execution": "Câu vừa làm trục; không dùng chuỗi mảnh câu.",
        }
    )

    saved = client.post(
        "/api/novels/dna_sync/artifact",
        json={
            "path": "PROJECT_DNA.fields.json",
            "text": json.dumps(fields, ensure_ascii=False),
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["synced"] == [
        "PROJECT_DNA.fields.json",
        "PROJECT_DNA.md",
        "PROJECT_DNA.meta.json",
    ]

    dna = client.get("/api/novels/dna_sync").json()["dna"]
    assert "genre: hybrid" in dna
    assert "style_model: VN" in dna
    assert "trầm tĩnh, thực dụng, hài khô kín đáo" in dna
    assert "Câu vừa làm trục; không dùng chuỗi mảnh câu." in dna

    meta = client.get(
        "/api/novels/dna_sync/artifact",
        params={"path": "PROJECT_DNA.meta.json"},
    ).json()
    routing = json.loads(meta["text"])
    assert routing["genre"] == "hybrid"
    assert routing["genre_primary"] == "xianxia"
    assert routing["genre_secondary"] == "romance"
    assert routing["style_model"] == "VN"
    assert routing["style_secondary"] == "CM"
    assert routing["style_blend"] == "CM"


def test_writing_invalid_dna_fields_keeps_existing_bundle(client):
    client.post("/api/novels", json={"name": "dna_sync_bad", "fields": _fields(3)})
    before = client.get("/api/novels/dna_sync_bad").json()["dna"]
    saved = client.post(
        "/api/novels/dna_sync_bad/artifact",
        json={"path": "PROJECT_DNA.fields.json", "text": "{not-json"},
    )
    assert saved.status_code == 422
    assert client.get("/api/novels/dna_sync_bad").json()["dna"] == before


def test_writing_unknown_author_code_is_rejected_without_desynchronizing_bundle(client):
    client.post("/api/novels", json={"name": "dna_style_bad", "fields": _fields(3)})
    before = client.get("/api/novels/dna_style_bad").json()["dna"]
    fields = {
        **_fields(3),
        "style_model": "UNKNOWN",
        "worldbuilding_guide": "UNKNOWN",
    }
    saved = client.post(
        "/api/novels/dna_style_bad/artifact",
        json={
            "path": "PROJECT_DNA.fields.json",
            "text": json.dumps(fields),
        },
    )
    assert saved.status_code == 422
    assert client.get("/api/novels/dna_style_bad").json()["dna"] == before


def _preflight_block(dna: str) -> str:
    for marker in ("## XII. SỔ KIỂM KHỞI TẠO", "## XIII. SỔ KIỂM KHỞI TẠO"):
        if marker in dna:
            return dna.split(marker, 1)[1].split("---", 1)[0]
    raise AssertionError("no preflight section in PROJECT_DNA")


def test_create_requires_template_fields(client):
    # Valid name but missing required template fields → 422.
    r = client.post("/api/novels", json={"name": "empty_one", "fields": {}})
    assert r.status_code == 422


def test_created_dna_checks_completed_preflight_items(client):
    fields = {
        **_fields(30),
        "usp": "Tu luyện bằng ký ức đã mất.",
        "theme": "Cái giá của trường sinh.",
        "style_model": "NC",
        "worldbuilding_guide": "NC",
        "world_name": "Cửu Vực",
        "world_secret": "Thiên đạo đã chết từ vạn năm trước.",
        "world_locations": "Huyền Kinh; Táng Hải; Cổ Thành Vô Danh",
        "system_tiers": "Luyện Khí → Trúc Cơ → Kim Đan",
        "system_cost": "Mỗi lần đột phá mất một đoạn ký ức.",
        "system_bottleneck": "Linh khí cạn kiệt.",
        "mc_want": "Báo thù.",
        "mc_need": "Học cách tin người.",
        "mc_ghost": "Tông môn bị diệt.",
        "mc_lie": "Chỉ sức mạnh mới bảo vệ được mọi thứ.",
        "mc_voice": "Ít lời, sắc lạnh.",
        "supporting_cast": "- Lạc Yên\n- Tạ Vũ\n- Mộc Đồng",
        "antagonist_name": "Vô Tướng",
        "villain_want": "Viết lại thiên đạo.",
        "villain_human_moment": "Giữ lại chiếc trâm của cố thê.",
        "inciting_incident": "MC nhặt được mảnh thiên thư.",
        "midpoint_twist": "Thiên thư là khóa phong ấn.",
        "climax": "MC phá bỏ thiên đạo giả.",
        "arc_boss_ladder": "Arc 1: Huyết Sứ; Arc 2: Đạo Chủ; Arc 3: Vô Tướng",
        "mini_bosses": "Huyết Lang; Kiếm Nô; Mộng Yểm",
    }
    r = client.post("/api/novels", json={"name": "preflight", "fields": fields})
    assert r.status_code == 201, r.text

    dna = client.get("/api/novels/preflight").json()["dna"]
    preflight = _preflight_block(dna)
    assert preflight.count("☑") == 11


def test_preflight_world_requires_at_least_three_locations(client):
    fields = {
        **_fields(30),
        "world_name": "Cửu Vực",
        "world_secret": "Thiên đạo đã chết từ vạn năm trước.",
        "world_locations": "Huyền Kinh",
    }
    client.post("/api/novels", json={"name": "one_location", "fields": fields})

    dna = client.get("/api/novels/one_location").json()["dna"]
    preflight = _preflight_block(dna)
    assert "□ Thế giới quan" in preflight


def test_create_rejects_bad_name(client):
    r = client.post("/api/novels", json={"name": "Bad Name!", "fields": _fields()})
    assert r.status_code == 422


def test_create_duplicate_dedups(client):
    first = client.post("/api/novels", json={"name": "dup", "fields": _fields()})
    assert first.status_code in (200, 201)
    assert first.json()["name"] == "dup"
    second = client.post("/api/novels", json={"name": "dup", "fields": _fields()})
    assert second.status_code in (200, 201)
    # Collision is auto-resolved with a numeric suffix instead of a 409.
    assert second.json()["name"] == "dup-2"


def test_missing_novel_is_404(client):
    assert client.get("/api/novels/nope").status_code == 404


# --------------------------------------------------------------------------- #
# Pipeline board
# --------------------------------------------------------------------------- #


def test_pipeline_plan_record_advances(client):
    client.post("/api/novels", json={"name": "flow", "fields": _fields()})

    nxt = client.post("/api/novels/flow/pipeline/plan-next", json={"claim": True})
    assert nxt.status_code == 200
    task_key = nxt.json()["ready_task"]["task_key"]
    assert task_key == "bootstrap.characters"

    rec = client.post(
        "/api/novels/flow/pipeline/record-result",
        json={"task_key": task_key, "result": "done", "score": 90},
    )
    assert rec.status_code == 200

    # Next ready task must differ now that the first is done.
    after = client.post("/api/novels/flow/pipeline/plan-next", json={"claim": False})
    assert after.json()["ready_task"]["task_key"] != task_key


def test_resume_is_safe(client):
    client.post("/api/novels", json={"name": "res", "fields": _fields()})
    r = client.post("/api/novels/res/pipeline/resume")
    assert r.status_code == 200
    assert r.json()["done_count"] == 0


def test_pipeline_state_digest_mismatch_is_rejected(client):
    client.post("/api/novels", json={"name": "tamper", "fields": _fields()})

    import json

    from sqlalchemy import select
    from webapp.api.novel_paths import novel_disk_path
    from webapp.db.models import Novel
    from webapp.db.session import SessionLocal

    with SessionLocal() as db:
        novel = db.scalar(select(Novel).where(Novel.slug == "tamper"))
        assert novel is not None
        state_path = novel_disk_path(novel) / "logs" / "pipeline_state.json"

    payload = json.loads(state_path.read_text())
    payload["state_digest"] = "sha256:" + ("0" * 64)
    state_path.write_text(json.dumps(payload), encoding="utf-8")

    r = client.get("/api/novels/tamper")
    assert r.status_code == 409


# --------------------------------------------------------------------------- #
# Creative analysis passthroughs
# --------------------------------------------------------------------------- #


def test_ai_flavor_analysis(client):
    r = client.post("/api/analyze/ai-flavor", json={"text": "Một câu văn bình thường."})
    assert r.status_code == 200
    assert "risk_score" in r.json()


def test_language_guard_requires_genre(client):
    r = client.post("/api/analyze/language-guard", json={"text": "mở debug runtime"})
    assert r.status_code == 422


def test_language_guard_flags_operational(client):
    r = client.post(
        "/api/analyze/language-guard",
        json={"text": "Nhân vật mở debug và xem metadata.", "genre": "xianxia"},
    )
    assert r.status_code == 200
    terms = {v["term"] for v in r.json()["violations"]}
    assert "debug" in terms


# --------------------------------------------------------------------------- #
# Concurrency safety (job lock + atomic state write)
# --------------------------------------------------------------------------- #


def test_atomic_write_survives_crash_midway(tmp_path, monkeypatch):
    """A crash during serialisation must leave the previous file intact."""
    import json as _json

    import webapp.api.service as service

    target = tmp_path / "state.json"
    service._write_json(target, {"v": 1})
    assert _json.loads(target.read_text())["v"] == 1

    # Force json.dumps to blow up while writing the *new* payload.
    def _boom(*_a, **_k):
        raise RuntimeError("serialise failed")

    monkeypatch.setattr(service.json, "dumps", _boom)
    with pytest.raises(RuntimeError):
        service._write_json(target, {"v": 2})

    # Old content survives; no truncated/half-written file, no leftover .tmp.
    assert _json.loads(target.read_text())["v"] == 1
    assert not list(tmp_path.glob("*.tmp"))


def test_run_lock_is_exclusive_per_novel(tmp_path):
    """A second acquirer of a held novel lock must fail fast (RunBusyError)."""
    import threading

    import webapp.api.service as service

    name = "lockdemo"
    path = tmp_path / name
    (path / "logs").mkdir(parents=True)

    held = threading.Event()
    release = threading.Event()

    def _holder():
        with service._novel_run_lock(name, path):
            held.set()
            release.wait(timeout=5)

    t = threading.Thread(target=_holder)
    t.start()
    assert held.wait(timeout=5)

    # Lock is held → a second attempt raises instead of clobbering state.
    with pytest.raises(service.RunBusyError):
        with service._novel_run_lock(name, path):
            pass

    release.set()
    t.join(timeout=5)

    # Once released, the lock is acquirable again.
    with service._novel_run_lock(name, path):
        pass


def test_record_result_busy_returns_already_running(client, monkeypatch):
    """When a run holds the lock, record-result reports alreadyRunning (not 500)."""
    client.post("/api/novels", json={"name": "busy", "fields": _fields()})

    import webapp.api.service as service

    # Simulate an in-flight run by holding the novel lock from another thread.
    import threading

    from sqlalchemy import select
    from webapp.api.novel_paths import novel_disk_path
    from webapp.db.models import Novel
    from webapp.db.session import SessionLocal

    with SessionLocal() as db:
        novel = db.scalar(select(Novel).where(Novel.slug == "busy"))
        assert novel is not None
        path = novel_disk_path(novel)
    held = threading.Event()
    release = threading.Event()

    def _holder():
        with service._novel_run_lock("busy", path):
            held.set()
            release.wait(timeout=5)

    t = threading.Thread(target=_holder)
    t.start()
    assert held.wait(timeout=5)

    r = client.post(
        "/api/novels/busy/pipeline/record-result",
        json={"task_key": "bootstrap.characters", "result": "done", "score": 90},
    )
    release.set()
    t.join(timeout=5)

    assert r.status_code == 200
    assert r.json().get("alreadyRunning") is True


def test_legacy_control_plane_state_is_refused(client):
    """A workspace carrying the legacy SQLite control plane must not be driven
    by the Hermes JSON runtime — operating on it would create two divergent
    sources of truth for one novel."""
    client.post("/api/novels", json={"name": "legacy", "fields": _fields()})

    import webapp.api.service as service

    from sqlalchemy import select
    from webapp.api.novel_paths import novel_disk_path
    from webapp.db.models import Novel
    from webapp.db.session import SessionLocal

    with SessionLocal() as db:
        novel = db.scalar(select(Novel).where(Novel.slug == "legacy"))
        assert novel is not None
        path = novel_disk_path(novel)
    (path / ".controlplane.sqlite3").write_bytes(b"SQLite format 3\x00")

    r = client.post("/api/novels/legacy/pipeline/plan-next", json={"claim": False})
    assert r.status_code == 409
    assert ".controlplane.sqlite3" in r.json()["detail"]


def test_run_command_pause_applies_authoritative_pipeline_state(client):
    from sqlalchemy import select
    from tools.novelkit_pipeline_state_store import PipelineStateStore
    from webapp.api.novel_paths import novel_disk_path
    from webapp.db.models import Novel, RunJobRecord
    from webapp.db.session import SessionLocal

    client.post(
        "/api/novels",
        json={"name": "cmdpause", "fields": _fields(target=1)},
    )
    with SessionLocal() as db:
        novel = db.scalar(select(Novel).where(Novel.slug == "cmdpause"))
        assert novel is not None
        job = RunJobRecord(
            user_id=novel.owner_user_id,
            novel_id=novel.slug,
            status="running",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
        path = novel_disk_path(novel)

    state = PipelineStateStore(path).load_payload()
    r = client.post(
        f"/api/novels/cmdpause/runs/{job_id}/commands",
        json={
            "command_type": "pause",
            "payload": {"reason": "operator_review"},
            "expected_state_version": state["state_version"],
        },
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "applied"
    assert body["application"]["paused"] is True
    persisted = json.loads(PipelineStateStore(path).state_path.read_text())
    assert persisted["creative"]["paused"] is True
    assert persisted["creative"]["pause_reason"] == "operator_review"


def test_suggest_characters(client):
    r = client.get("/api/suggest-characters")
    assert r.status_code == 200
    data = r.json()
    assert "mc" in data
    assert "antagonist" in data

    mc = data["mc"]
    pd = data["antagonist"]

    if mc and pd:
        mc_name = mc.get("mc_name", "")
        if mc_name:
            original_names = ["Trần Trường Sinh", "Trường Sinh", "Ninh Khuyết", "Phạm Nhàn", "Hứa Nhạc"]
            for key in ["antagonist_traits", "antagonist_conflict"]:
                val = pd.get(key, "")
                if val:
                    # None of the original MC names should be in the descriptions
                    for orig in original_names:
                        assert orig not in val
                        assert orig.lower() not in val.lower()
                    # The newly suggested MC name should not be in the descriptions
                    assert mc_name not in val
                    assert mc_name.lower() not in val.lower()
                    
                    # The antagonist's own base name should not be in the descriptions
                    pd_name = pd.get("antagonist_name", "")
                    if pd_name:
                        base = pd_name
                        for suffix in [" Khánh Dư Niên", " Tương Dạ", " Trạch Thiên Ký", " Gian Khách"]:
                            base = base.replace(suffix, "")
                        if len(base) > 2:
                            assert base.lower() not in val.lower()




def test_suggest_seed(client):
    r = client.get("/api/suggest-seed")
    assert r.status_code == 200
    data = r.json()
    assert "logline" in data
    assert "usp" in data
    assert "theme" in data
    assert "audience" in data
    assert data["logline"] != ""
    assert data["usp"] != ""
    assert data["theme"] != ""
    assert data["audience"] != ""


def test_suggest_companions(client):
    r = client.get("/api/suggest-companions")
    assert r.status_code == 200
    data = r.json()
    assert "artifact" in data
    assert "spirit_beast" in data
    assert "supporting_cast" in data
    assert data["artifact"] != ""
    assert data["spirit_beast"] != ""
    assert data["supporting_cast"] != ""

    # Check that it does not contain capitalized proper names (case-sensitive)
    original_names = ["Trần Trường Sinh", "Trường Sinh", "Ninh Khuyết", "Phạm Nhàn", "Hứa Nhạc"]
    for key in ["artifact", "spirit_beast", "supporting_cast"]:
        val = data.get(key, "")
        assert val != ""
        lines = [line.strip() for line in val.strip().split("\n") if line.strip()]
        assert len(lines) >= 4
        
        # Verify that all 4 milestones are represented in the list of companions
        assert any("Khởi đầu" in line for line in lines)
        assert any("Trung kỳ" in line for line in lines)
        assert any("Hậu kỳ" in line for line in lines)
        assert any("Kết thúc" in line for line in lines)
        
        for orig in original_names:
            assert orig not in val


def test_suggest_cultivation(client):
    # Test random/fallback
    r = client.get("/api/suggest-cultivation")
    assert r.status_code == 200
    data = r.json()
    assert "cultivation_age_benchmarks" in data
    val = data["cultivation_age_benchmarks"]
    assert val != ""
    lines = [line.strip() for line in val.strip().split("\n") if line.strip()]
    assert len(lines) >= 3
    
    # Test alignment for VN (Vong Ngữ)
    r_vn = client.get("/api/suggest-cultivation?style_model=VN")
    assert r_vn.status_code == 200
    data_vn = r_vn.json()
    val_vn = data_vn["cultivation_age_benchmarks"]
    assert "Trường Xuân Công" in val_vn
    
    # Test alignment for TD (Tiêu Đỉnh)
    r_td = client.get("/api/suggest-cultivation?style_model=TD")
    assert r_td.status_code == 200
    data_td = r_td.json()
    val_td = data_td["cultivation_age_benchmarks"]
    assert "Thanh Vân" in val_td

    # Verify proper names generalization
    original_names = ["Hàn Lập", "Vương Lâm", "Tô Minh", "Mạnh Hạo", "Bạch Tiểu Thuần", "Trương Tiểu Phàm"]
    for val_str in [val, val_vn, val_td]:
        for orig in original_names:
            assert orig not in val_str


# --------------------------------------------------------------------------- #
# Long-form GA surface (NovelCLI): longform status · steer · diag · compass
# --------------------------------------------------------------------------- #


def test_longform_status_defaults_on(client):
    client.post("/api/novels", json={"name": "lf_status", "fields": _fields()})
    r = client.get("/api/novels/lf_status/longform")
    assert r.status_code == 200, r.text
    body = r.json()
    # Feature flags are present and default ON (GA: compass is the primary mode).
    assert set(body["flags"]) >= {
        "compass", "recall", "minor_cast", "style_stats", "reminder", "steer", "diag"
    }
    assert all(v is True for v in body["flags"].values())
    # Thresholds surfaced from config for the panel.
    assert body["thresholds"]["COMPASS_MODE_MIN_CHAPTERS"] == 60
    # No compass artifact yet; arc map is an empty (but valid) structure.
    assert body["compass"] is None
    assert body["arc_map"]["arcs"] == []
    # Reminder is always renderable; stop-guard is advisory dict.
    assert isinstance(body["reminder"], str)
    assert "blocked" in body["stop_guard"]


def test_steer_routes_rewrite(client):
    client.post("/api/novels", json={"name": "lf_steer", "fields": _fields()})
    r = client.post("/api/novels/lf_steer/steer", json={"text": "viết lại chương 3"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["route"] == "rewrite_existing"
    assert body["affected_chapters"] == [3]
    assert body["applied"] is True
    # The steer is now recorded as pending in the aggregated status.
    status = client.get("/api/novels/lf_steer/longform").json()
    assert status["pending_steer"]["route"] == "rewrite_existing"


def test_steer_style_rule_is_applied(client):
    client.post("/api/novels", json={"name": "lf_style", "fields": _fields()})
    r = client.post("/api/novels/lf_style/steer", json={"text": "mỗi chương 1500 từ"})
    assert r.status_code == 200, r.text
    assert r.json()["route"] == "style_rule"


def test_diagnostics_returns_list(client):
    client.post("/api/novels", json={"name": "lf_diag", "fields": _fields()})
    r = client.get("/api/novels/lf_diag/diagnostics")
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)  # findings list (empty for a fresh novel)


def test_compass_migrate_creates_compass(client):
    client.post("/api/novels", json={"name": "lf_mig", "fields": _fields()})
    r = client.post(
        "/api/novels/lf_mig/compass/migrate",
        json={"current_chapter": 0, "target_chapters": 300},
    )
    assert r.status_code == 200, r.text
    assert r.json()["changed"] is True
    # Compass now materialises in the aggregated status with the target scale.
    status = client.get("/api/novels/lf_mig/longform").json()
    assert status["compass"] is not None
    assert status["compass"]["scale_estimate"]["chapters"] == 300


def test_compass_migrate_requires_target(client):
    client.post("/api/novels", json={"name": "lf_mig2", "fields": _fields()})
    r = client.post("/api/novels/lf_mig2/compass/migrate", json={"current_chapter": 5})
    assert r.status_code == 422  # target_chapters is required


# --------------------------------------------------------------------------- #
# Knowledge graph read endpoint (Req 8.1) — GET /api/studio/novels/{slug}/graph
# --------------------------------------------------------------------------- #


def _novel_disk_path(slug: str):
    """Resolve the on-disk workspace path for a novel by slug (test helper)."""
    from sqlalchemy import select
    from webapp.api.novel_paths import novel_disk_path
    from webapp.db.models import Novel
    from webapp.db.session import SessionLocal

    with SessionLocal() as db:
        novel = db.scalar(select(Novel).where(Novel.slug == slug))
        assert novel is not None
        return novel_disk_path(novel)


def test_graph_endpoint_empty_state(client):
    """No graph exported yet → 200 with an explicit empty-state body (never 500)."""
    client.post("/api/novels", json={"name": "graph_empty", "fields": _fields()})

    r = client.get("/api/studio/novels/graph_empty/graph")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["exists"] is False
    assert body["graph"] is None


def test_graph_endpoint_returns_built_graph(client):
    """After a graph is exported to logs/knowledge_graph.json the endpoint
    returns the persisted node-link payload plus its digest."""
    client.post("/api/novels", json={"name": "graph_built", "fields": _fields()})

    path = _novel_disk_path("graph_built")
    # Seed one canon character so the built graph has at least one entity node.
    chars = path / "database" / "characters"
    chars.mkdir(parents=True, exist_ok=True)
    (chars / "A.md").write_text("# A\n", encoding="utf-8")

    from tools.novelkit_graph_tool import build

    result = build(path)
    assert result["node_count"] >= 1

    r = client.get("/api/studio/novels/graph_built/graph")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["exists"] is True
    assert body["graph_digest"].startswith("sha256:")
    # node-link payload with the seeded entity present.
    graph = body["graph"]
    assert graph is not None
    node_ids = {n["id"] for n in graph["nodes"]}
    assert "ent:a" in node_ids


def test_graph_endpoint_404_unknown_novel(client):
    r = client.get("/api/studio/novels/does-not-exist/graph")
    assert r.status_code == 404


def test_graph_endpoint_contradictions_empty_state(client):
    """No graph exported yet → contradictions is an explicit empty tiered map
    (never missing, never a 500), so the frontend can highlight safely (Req 8.4)."""
    client.post("/api/novels", json={"name": "graph_contra_empty", "fields": _fields()})

    r = client.get("/api/studio/novels/graph_contra_empty/graph")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["contradictions"] == {"soft": [], "hard": []}


def test_graph_endpoint_includes_hard_contradictions(client):
    """A built graph seeded with a death-then-acts logic gap exposes a hard
    ``kg_dead_but_acts`` contradiction on the read endpoint for UI highlight (Req 8.4)."""
    client.post("/api/novels", json={"name": "graph_contra", "fields": _fields()})

    path = _novel_disk_path("graph_contra")

    from plugins.memory.novelkit_memory import get_provider

    p = get_provider()
    p.add(
        {
            "category": "timeline",
            "subject": "A",
            "field": "death",
            "value": "chết",
            "source_chapter": 50,
            "payload": {},
        },
        scope=path,
    )
    p.add(
        {
            "category": "character_state",
            "subject": "A",
            "field": "state_change",
            "value": "vung kiếm",
            "source_chapter": 80,
            "payload": {},
        },
        scope=path,
    )
    (path / "database" / "characters").mkdir(parents=True, exist_ok=True)
    (path / "database" / "characters" / "A.md").write_text("# A\n", "utf-8")

    from tools.novelkit_graph_tool import build

    build(path)

    r = client.get("/api/studio/novels/graph_contra/graph")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["exists"] is True
    hard = body["contradictions"]["hard"]
    assert hard, "expected at least one hard contradiction"
    assert any(c["code"] == "kg_dead_but_acts" for c in hard)
