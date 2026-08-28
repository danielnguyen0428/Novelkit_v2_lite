"""Tests for the LLM settings + real-generation run path (webapp.api).

Network is never hit: ``LLMClient.complete`` is monkeypatched to return canned
content. Verifies the key is stored masked (never echoed), the test-connection
probe maps cleanly, and ``run`` drives the pipeline through the LLM loop and
materialises real artifacts + a passing sync.
"""

from __future__ import annotations

import importlib
import json
import re
import tempfile

import pytest
from fastapi.testclient import TestClient

from webapp.db.models import Base
from webapp.db.session import engine
from tools.novelkit_pipeline_state_store import PipelineStateConflict, PipelineStateStore
from tools.novelkit_pipeline_tool import ARC_SIZE, PipelineEngine, PipelineState, TaskStatus


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("NOVELKIT_WORKSPACE_ROOT", tempfile.mkdtemp())
    monkeypatch.setenv("NOVELKIT_SECRETS_DIR", tempfile.mkdtemp())
    # No real key in env — tests set it through the API.
    monkeypatch.delenv("NOVELKIT_LLM_API_KEY", raising=False)
    import provider.settings as ps

    importlib.reload(ps)
    import provider.llm_client as lc

    importlib.reload(lc)
    import webapp.api.service as service

    importlib.reload(service)
    import webapp.api.main as main

    importlib.reload(main)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestClient(main.app)


_REVIEW_BODY = (
    "Chương chắc tay, nhịp ổn, nhân vật nhất quán.\n\n"
    "**Điểm:** 90/100\n## Verdict: PASS\n"
)


def _fake_complete(self, *, system=None, user="", messages=None, temperature=None, max_tokens=None):
    # Critique prompts ask for scoring → return a passing review; other stages
    # return plausible prose that still carries a passing verdict so sync passes.
    body = (
        "Hắn vận khí, linh lực chảy qua kinh mạch, đan điền rung lên một nhịp. "
        "Ngoài song, tuyết rơi lặng lẽ phủ trắng sân điện cổ.\n\n"
    ) * 20
    return body + "\n" + _REVIEW_BODY


def _complete_pipeline_task(engine: PipelineEngine, task_key: str) -> None:
    engine.record_result(task_key, "done", score=90)


def _complete_bootstrap_and_chapter(engine: PipelineEngine, chapter: int) -> None:
    for key in (
        "bootstrap.characters",
        "bootstrap.world",
        "bootstrap.plot_threads",
        "bootstrap.timeline",
        "bootstrap.master_outline",
    ):
        _complete_pipeline_task(engine, key)
    for suffix in ("outline", "write", "self_check", "review", "sync"):
        _complete_pipeline_task(engine, f"chapter.{chapter:04d}.{suffix}")


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #


def test_settings_empty_by_default(client):
    s = client.get("/api/settings").json()
    assert s["api_key_set"] is False
    assert s["configured"] is False


def test_save_settings_masks_key(client):
    r = client.put(
        "/api/settings",
        json={"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini",
              "api_key": "sk-test-1234567890"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["api_key_set"] is True
    assert body["configured"] is True
    # The raw key is NEVER returned.
    assert "sk-test-1234567890" not in r.text
    assert "…" in body["api_key_fingerprint"]


def test_save_settings_rejects_unencrypted_provider_url(client):
    r = client.put(
        "/api/settings",
        json={"base_url": "http://api.example.com/v1", "api_key": "sk-test"},
    )
    assert r.status_code == 422
    assert "must use HTTPS" in r.text


def test_loopback_http_requires_explicit_server_flag(client, monkeypatch):
    blocked = client.put(
        "/api/settings",
        json={"base_url": "http://localhost:11434/v1", "api_key": "ollama"},
    )
    assert blocked.status_code == 422

    monkeypatch.setenv("NOVELKIT_ALLOW_INSECURE_LLM_URLS", "1")
    allowed = client.put(
        "/api/settings",
        json={"base_url": "http://localhost:11434/v1", "api_key": "ollama"},
    )
    assert allowed.status_code == 200

    remote = client.put(
        "/api/settings",
        json={"base_url": "http://api.example.com/v1", "api_key": "sk-test"},
    )
    assert remote.status_code == 422


def test_save_settings_without_key_keeps_existing(client):
    client.put("/api/settings", json={"api_key": "sk-secret-abcdef12345"})
    # Update only the model; key must persist.
    r = client.put("/api/settings", json={"model": "gpt-4o"})
    body = r.json()
    assert body["model"] == "gpt-4o"
    assert body["api_key_set"] is True


def test_test_connection_requires_key(client):
    r = client.post("/api/settings/test")
    assert r.status_code == 400


def test_test_connection_ok_when_mocked(client, monkeypatch):
    import provider.llm_client as lc

    monkeypatch.setattr(lc.LLMClient, "complete", _fake_complete)
    client.put("/api/settings", json={"api_key": "sk-x-123456789"})
    r = client.post("/api/settings/test")
    assert r.status_code == 200
    assert r.json()["ok"] is True


# --------------------------------------------------------------------------- #
# Run — real generation loop (mocked LLM)
# --------------------------------------------------------------------------- #


def test_run_requires_configured_key(client):
    client.post("/api/novels", json={"name": "nokey", "fields": {"title": "D", "genre": "xianxia", "logline": "x", "target_chapters": 1}})
    r = client.post("/api/novels/nokey/run", json={"max_steps": 2})
    assert r.status_code == 400


def test_run_advances_pipeline_with_mocked_llm(client, monkeypatch):
    import provider.llm_client as lc

    monkeypatch.setattr(lc.LLMClient, "complete", _fake_complete)
    client.put("/api/settings", json={"api_key": "sk-run-123456789"})
    client.post("/api/novels", json={"name": "runnable", "fields": {"title": "R", "genre": "xianxia", "logline": "x", "target_chapters": 1}})

    r = client.post("/api/novels/runnable/run", json={"max_steps": 8})
    assert r.status_code == 200, r.text
    report = r.json()
    assert len(report["steps"]) >= 1
    # At least the bootstrap/worldbuild stage ran and produced artifacts.
    assert report["tasks_completed"] >= 1


def test_run_unknown_novel_404(client, monkeypatch):
    import provider.llm_client as lc

    monkeypatch.setattr(lc.LLMClient, "complete", _fake_complete)
    client.put("/api/settings", json={"api_key": "sk-x-123456789"})
    r = client.post("/api/novels/ghost/run", json={"max_steps": 2})
    assert r.status_code == 404


def test_run_step_persists_rolling_seed_before_claim(client, monkeypatch):
    import provider.llm_client as lc
    from sqlalchemy import select
    from webapp.api.novel_paths import novel_disk_path
    from webapp.db.models import Novel
    from webapp.db.session import SessionLocal

    monkeypatch.setattr(lc.LLMClient, "complete", _fake_complete)
    client.put("/api/settings", json={"api_key": "sk-roll-123456789"})
    client.post(
        "/api/novels",
        json={
            "name": "rollstep",
            "fields": {
                "title": "Roll",
                "genre": "xianxia",
                "logline": "Một thiếu niên mở rộng hành trình.",
                "target_chapters": 4,
            },
        },
    )

    with SessionLocal() as db:
        novel = db.scalar(select(Novel).where(Novel.slug == "rollstep"))
        assert novel is not None
        path = novel_disk_path(novel)

    engine = PipelineEngine.create(
        target_chapters=4,
        arc_size=ARC_SIZE,
        novel="rollstep",
        initial_window=1,
        mode="full_plan",
    )
    _complete_bootstrap_and_chapter(engine, 1)
    PipelineStateStore(path).save(engine.state)

    r = client.post("/api/novels/rollstep/run-step")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["step"]["task_key"] == "chapter.0002.outline"
    state = PipelineStateStore(path).load_payload()
    assert any(t["task_key"] == "chapter.0002.outline" for t in state["tasks"])


def test_run_step_conflict_does_not_overwrite_newer_state(client, monkeypatch):
    import provider.llm_client as lc
    from integrations.autonovel.adapter import AutoNovelAdapter
    from sqlalchemy import select
    from webapp.api.novel_paths import novel_disk_path
    from webapp.db.models import Novel
    from webapp.db.session import SessionLocal

    monkeypatch.setattr(lc.LLMClient, "complete", _fake_complete)
    client.put("/api/settings", json={"api_key": "sk-conflict-123456789"})
    client.post(
        "/api/novels",
        json={
            "name": "conflictstep",
            "fields": {
                "title": "Conflict",
                "genre": "xianxia",
                "logline": "Một thiếu niên gặp ngã rẽ.",
                "target_chapters": 1,
            },
        },
    )

    with SessionLocal() as db:
        novel = db.scalar(select(Novel).where(Novel.slug == "conflictstep"))
        assert novel is not None
        path = novel_disk_path(novel)

    store = PipelineStateStore(path)
    before = store.load_payload()
    fresh = PipelineEngine(PipelineState.from_dict(before))
    claimed = fresh.plan_next(claim=True)
    assert claimed is not None

    def _conflicting_step(self):  # noqa: ANN001
        self.state_store.save(fresh.state, expected_version=before["state_version"])
        raise PipelineStateConflict("stale worker")

    monkeypatch.setattr(AutoNovelAdapter, "step", _conflicting_step)

    r = client.post("/api/novels/conflictstep/run-step")

    assert r.status_code == 409
    after = store.load_payload()
    assert after["state_version"] == fresh.state.state_version
    persisted = next(t for t in after["tasks"] if t["task_key"] == claimed.task_key)
    assert persisted["status"] == TaskStatus.IN_PROGRESS.value


def test_run_blocked_until_dna_ready(client, monkeypatch):
    """Writing must not start while PROJECT_DNA is still a placeholder."""
    import provider.llm_client as lc

    monkeypatch.setattr(lc.LLMClient, "complete", _fake_complete)
    client.put("/api/settings", json={"api_key": "sk-dna-123456789"})
    client.post(
        "/api/novels",
        json={"name": "needdna", "fields": {"title": "D", "genre": "xianxia",
                                            "logline": "x", "target_chapters": 1}},
    )

    # Overwrite PROJECT_DNA with an unfilled placeholder logline.
    client.post(
        "/api/novels/needdna/artifact",
        json={
            "path": "PROJECT_DNA.md",
            "text": "# PROJECT_DNA.md — D\n\n- **Logline (1 câu pitch):** [Tự sinh]\n",
        },
    )

    # Listing reflects the not-ready state.
    listing = client.get("/api/novels").json()
    brief = next(n for n in listing if n["name"] == "needdna")
    assert brief["dna_ready"] is False

    # And the creative loop refuses to run.
    r = client.post("/api/novels/needdna/run", json={"max_steps": 2})
    assert r.status_code == 409
    assert "PROJECT_DNA" in r.json()["detail"]

    r2 = client.post("/api/novels/needdna/run-step")
    assert r2.status_code == 409


def test_dna_ready_true_for_filled_logline(client):
    client.post(
        "/api/novels",
        json={"name": "hasdna", "fields": {"title": "H", "genre": "xianxia",
                                           "logline": "Một thiếu niên trùng sinh báo thù.",
                                           "target_chapters": 1}},
    )
    listing = client.get("/api/novels").json()
    brief = next(n for n in listing if n["name"] == "hasdna")
    assert brief["dna_ready"] is True


def test_recover_clears_open_breaker_dead_end(client, monkeypatch):
    """An open circuit breaker parks every task as BLOCKED and short-circuits
    ready_tasks to []. Neither resume nor plan-next can then make progress, so
    the UI is wedged. /pipeline/recover is the operator valve: it must clear the
    breaker, release the blocked task back to retryable, and make it ready again.
    """
    from sqlalchemy import select
    from webapp.api.novel_paths import novel_disk_path
    from webapp.db.models import Novel
    from webapp.db.session import SessionLocal

    client.post(
        "/api/novels",
        json={"name": "wedged", "fields": {"title": "W", "genre": "xianxia",
                                           "logline": "Một thiếu niên gặp bế tắc.",
                                           "target_chapters": 3}},
    )
    with SessionLocal() as db:
        novel = db.scalar(select(Novel).where(Novel.slug == "wedged"))
        assert novel is not None
        path = novel_disk_path(novel)

    # Drive to breaker-open: bootstrap + expand arc 1, then hammer identical
    # soft-fails on chapter 1's review until the breaker trips.
    store = PipelineStateStore(path)
    eng = PipelineEngine(PipelineState.from_dict(store.load_payload()))
    for key in ("bootstrap.characters", "bootstrap.world", "bootstrap.plot_threads",
                "bootstrap.timeline", "bootstrap.master_outline", "bootstrap.compass"):
        t = eng.plan_next(claim=True)
        if t:
            eng.record_result(t.task_key, "done", score=90)
    eng.advance_expansion(3)
    for suffix in ("outline", "write", "self_check"):
        eng.record_result(f"chapter.0001.{suffix}", "done", score=90)
    for _ in range(6):
        eng.record_result("chapter.0001.review", "soft_fail",
                          failure_signature="review_gate_fail", score=50)
    store.save(eng.state)
    assert eng.state.breaker.is_open

    # Pre-fix dead-end: nothing is ready and resume cannot help.
    assert client.get("/api/novels/wedged").json()["ready_task"] is None
    client.post("/api/novels/wedged/pipeline/resume")
    assert client.get("/api/novels/wedged").json()["ready_task"] is None

    # The recovery valve un-sticks it.
    r = client.post("/api/novels/wedged/pipeline/recover")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["breaker_was_open"] is True
    assert body["released_tasks"] >= 1
    assert body["next_task_key"] == "chapter.0001.review"

    # Flow can continue: a task is ready again and the breaker is clear.
    detail = client.get("/api/novels/wedged").json()
    assert detail["ready_task"] is not None
    assert not detail["doctor"]["blocking_issues"]


def test_enrich_step_returns_done_flag(client, monkeypatch):
    import provider.llm_client as lc

    calls = {"n": 0}

    def one_field_per_call(
        self, *, system=None, user="", messages=None, temperature=None, max_tokens=None
    ):
        calls["n"] += 1
        keys = __import__("re").findall(r'^- "([^"]+)":', user, __import__("re").MULTILINE)
        if not keys:
            return "{}"
        return __import__("json").dumps({keys[0]: f"value-{keys[0]}"}, ensure_ascii=False)

    monkeypatch.setattr(lc.LLMClient, "complete", one_field_per_call)
    client.put("/api/settings", json={"api_key": "sk-step-123456789"})
    client.post(
        "/api/novels",
        json={
            "name": "step_enrich",
            "fields": {
                "title": "Step",
                "genre": "xianxia",
                "logline": "Một thiếu niên đi tìm chân tướng.",
                "target_chapters": 10,
            },
        },
    )

    first = client.post("/api/novels/step_enrich/enrich?max_batches=1")
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["count"] >= 1
    assert body.get("done") is False

    second = client.post("/api/novels/step_enrich/enrich?max_batches=1")
    assert second.status_code == 200, second.text
    assert calls["n"] >= 2


def test_enrich_fills_blank_full_setup_fields(client, monkeypatch):
    import provider.llm_client as lc

    def complete_requested_fields(
        self, *, system=None, user="", messages=None, temperature=None, max_tokens=None
    ):
        keys = re.findall(r'^- "([^"]+)":', user, re.MULTILINE)
        values = {key: f"Nội dung {key}" for key in keys}
        values.update(
            {
                "style_model": "NC",
                "worldbuilding_guide": "NC",
                "cultivation_speed": "slow",
                "supporting_cast": "- Lạc Yên\n- Tạ Vũ\n- Mộc Đồng",
                "world_locations": "Huyền Kinh; Táng Hải; Cổ Thành Vô Danh",
                "mc_want": "Báo thù",
                "mc_need": "Học cách tin người",
            }
        )
        return json.dumps({key: values[key] for key in keys}, ensure_ascii=False)

    monkeypatch.setattr(lc.LLMClient, "complete", complete_requested_fields)
    client.put("/api/settings", json={"api_key": "sk-enrich-123456789"})
    client.post(
        "/api/novels",
        json={
            "name": "full_blanks",
            "fields": {
                "title": "Full Blanks",
                "genre": "xianxia",
                "logline": "Một thiếu niên đi tìm chân tướng thiên đạo.",
                "target_chapters": 30,
            },
        },
    )

    r = client.post("/api/novels/full_blanks/enrich")
    assert r.status_code == 200, r.text
    assert {"usp", "style_model", "mc_name", "antagonist_name", "supporting_cast"} <= set(
        r.json()["enriched_fields"]
    )
    dna = client.get("/api/novels/full_blanks").json()["dna"]
    assert "- **Dấu riêng (USP):** Nội dung usp" in dna
    assert "template_source: skills/novelkit-canon/templates/genres/PROJECT_DNA_XIANXIA.md" in dna


def test_enrich_retries_fields_omitted_twice(client, monkeypatch):
    import provider.llm_client as lc

    world_location_requests = 0

    def omit_world_locations_twice(
        self, *, system=None, user="", messages=None, temperature=None, max_tokens=None
    ):
        nonlocal world_location_requests
        keys = re.findall(r'^- "([^"]+)":', user, re.MULTILINE)
        if "world_locations" in keys:
            world_location_requests += 1
            if world_location_requests <= 2:
                keys.remove("world_locations")
        values = {key: f"Nội dung {key}" for key in keys}
        values.update(
            {
                "style_model": "NC",
                "worldbuilding_guide": "NC",
                "supporting_cast": "- Lạc Yên\n- Tạ Vũ\n- Mộc Đồng",
                "mc_want": "Báo thù",
                "mc_need": "Học cách tin người",
                "world_locations": "Huyền Kinh; Táng Hải; Cổ Thành Vô Danh",
            }
        )
        return json.dumps({key: values[key] for key in keys}, ensure_ascii=False)

    monkeypatch.setattr(lc.LLMClient, "complete", omit_world_locations_twice)
    client.put("/api/settings", json={"api_key": "sk-retry-123456789"})
    client.post(
        "/api/novels",
        json={
            "name": "retry_missing",
            "fields": {
                "title": "Retry Missing",
                "genre": "xianxia",
                "logline": "Một thiếu niên đi tìm chân tướng thiên đạo.",
                "target_chapters": 30,
            },
        },
    )

    r = client.post("/api/novels/retry_missing/enrich")
    assert r.status_code == 200, r.text
    assert r.json()["missing_count"] == 0
    assert world_location_requests == 3


def test_enrich_defaults_style_when_model_returns_no_valid_code(client, monkeypatch):
    """Root-cause fix: when the model answers the style fields with a full author
    name / prose (not the bare code), parse_generated drops them and — without a
    deterministic fallback — enrich can never reach "done", leaving a permanent
    [Tự sinh] + an unchecked pre-flight "style" item. The fallback must fill both
    style_model and worldbuilding_guide so enrich completes cleanly."""
    import provider.llm_client as lc

    def unmappable_style(
        self, *, system=None, user="", messages=None, temperature=None, max_tokens=None
    ):
        keys = re.findall(r'^- "([^"]+)":', user, re.MULTILINE)
        values = {key: f"Nội dung {key}" for key in keys}
        values.update(
            {
                # Not a valid xianxia code → parse_generated drops these.
                "style_model": "Một tác giả giấu tên",
                "worldbuilding_guide": "Hướng dẫn dựng thế giới huyền huyễn chi tiết",
                "supporting_cast": "- Lạc Yên\n- Tạ Vũ\n- Mộc Đồng",
                "world_locations": "Huyền Kinh; Táng Hải; Cổ Thành Vô Danh",
                "mc_want": "Báo thù",
                "mc_need": "Học cách tin người",
            }
        )
        return json.dumps({key: values[key] for key in keys}, ensure_ascii=False)

    monkeypatch.setattr(lc.LLMClient, "complete", unmappable_style)
    client.put("/api/settings", json={"api_key": "sk-style-123456789"})
    client.post(
        "/api/novels",
        json={
            "name": "style_default",
            "fields": {
                "title": "Style Default",
                "genre": "xianxia",
                "logline": "Một thiếu niên đi tìm chân tướng thiên đạo.",
                "target_chapters": 30,
            },
        },
    )

    r = client.post("/api/novels/style_default/enrich")
    assert r.status_code == 200, r.text
    body = r.json()
    # Enrich now completes despite the model never giving a valid style code.
    assert body["missing_count"] == 0
    assert body["done"] is True
    assert {"style_model", "worldbuilding_guide"} <= set(body["enriched_fields"])

    dna = client.get("/api/novels/style_default").json()["dna"]
    # Style defaulted to the genre's first canonical author code (NC), and the
    # pre-flight "style" item is now checked.
    assert "style_model: NC" in dna
    assert "☑ Mã Đại Thần" in dna


def test_enrich_never_takes_a_model_supplied_style_code(client, monkeypatch):
    """Enrich must NOT let the model choose the voice authority.

    ``style_model`` selects which ``*_rules.md`` profile becomes the top style
    authority for every chapter, so a model answer here would silently rewrite
    the whole novel's voice. The fields are excluded from ``ENRICH_KEYS`` and
    resolved deterministically instead: even when the model volunteers a valid,
    perfectly-formatted alternative (here ``Tiêu Đỉnh`` = TD), the author's
    genre default (NC) must win and ``worldbuilding_guide`` must follow
    ``style_model`` rather than the model's separate pick.
    """
    import provider.llm_client as lc

    asked: list[str] = []

    def full_name_style(
        self, *, system=None, user="", messages=None, temperature=None, max_tokens=None
    ):
        keys = re.findall(r'^- "([^"]+)":', user, re.MULTILINE)
        asked.extend(keys)
        values = {key: f"Nội dung {key}" for key in keys}
        values.update(
            {
                "supporting_cast": "- A\n- B\n- C",
                "world_locations": "X; Y; Z",
                "mc_want": "a",
                "mc_need": "b",
            }
        )
        payload = {key: values[key] for key in keys}
        # Volunteered even though never requested — must be ignored, not obeyed.
        payload["style_model"] = "Tiêu Đỉnh"
        payload["worldbuilding_guide"] = "Vong Ngữ"
        return json.dumps(payload, ensure_ascii=False)

    monkeypatch.setattr(lc.LLMClient, "complete", full_name_style)
    client.put("/api/settings", json={"api_key": "sk-name-123456789"})
    client.post(
        "/api/novels",
        json={
            "name": "style_name",
            "fields": {
                "title": "Style Name",
                "genre": "xianxia",
                "logline": "Một thiếu niên tầm đạo.",
                "target_chapters": 30,
            },
        },
    )

    r = client.post("/api/novels/style_name/enrich")
    assert r.status_code == 200, r.text
    assert r.json()["missing_count"] == 0
    # The model is never even asked for a routing/style field.
    assert not ({"style_model", "style_secondary", "worldbuilding_guide"} & set(asked))
    dna = client.get("/api/novels/style_name").json()["dna"]
    assert "style_model: NC" in dna            # deterministic default, not "TD"
    assert "worldbuilding_guide: NC" in dna    # follows style_model, not "VN"
    assert "☑ Mã Đại Thần" in dna


def test_enrich_completes_when_model_omits_cross_genre_fields(client, monkeypatch):
    """Root cause: ENRICH_KEYS pools EVERY genre's craft fields (it ends with
    ``+ GENRE_ENRICH_KEYS``). A xianxia novel can never fill romance/urban/scifi/
    time-travel/meta fields (romance_barrier_*, urban_power_*, mc_modern_*, …), so
    counting them toward "missing" made enrich never reach ``done`` — the client's
    enrichDnaAll loop then stalled and stopped early, leaving genuine core fields
    (world/system/cast/premise) stuck on ``_(tự sinh)_``. A realistic model fills
    only the fields that make sense for the chosen genre; enrich must still complete.
    """
    import provider.llm_client as lc
    from webapp.api.dna_genre_fields import GENRE_ENRICH_KEYS, GENRE_SECTIONS

    xianxia_ids = {f["id"] for sec in GENRE_SECTIONS.get("xianxia", []) for f in sec["fields"]}
    cross_genre_ids = {k for k, _ in GENRE_ENRICH_KEYS if k not in xianxia_ids}

    def only_genre_relevant(
        self, *, system=None, user="", messages=None, temperature=None, max_tokens=None
    ):
        keys = re.findall(r'^- "([^"]+)":', user, re.MULTILINE)
        values: dict[str, str] = {}
        for key in keys:
            if key in cross_genre_ids:
                continue  # a real model omits out-of-genre fields
            if key in ("style_model", "worldbuilding_guide"):
                values[key] = "NC"
            elif key == "arc_count":
                values[key] = "5"
            elif key == "supporting_cast":
                values[key] = "- Lạc Yên\n- Tạ Vũ\n- Mộc Đồng"
            elif key == "world_locations":
                values[key] = "Huyền Kinh; Táng Hải; Cổ Thành Vô Danh"
            elif key == "mc_want":
                values[key] = "Báo thù"
            elif key == "mc_need":
                values[key] = "Học cách tin người"
            else:
                values[key] = f"Nội dung {key}"
        return json.dumps(values, ensure_ascii=False)

    monkeypatch.setattr(lc.LLMClient, "complete", only_genre_relevant)
    client.put("/api/settings", json={"api_key": "sk-crossgenre-123456789"})
    client.post(
        "/api/novels",
        json={
            "name": "crossgenre",
            "fields": {
                "title": "Cross Genre",
                "genre": "xianxia",
                "logline": "Một thiếu niên phàm căn nghịch thiên tu tiên.",
                "target_chapters": 30,
            },
        },
    )

    r = client.post("/api/novels/crossgenre/enrich")
    assert r.status_code == 200, r.text
    body = r.json()
    # Enrich completes even though the model never fills other genres' fields.
    assert body["done"] is True
    assert body["missing_count"] == 0

    # The rendered PROJECT_DNA.md has no leftover _(tự sinh)_ placeholders.
    dna = client.get("/api/novels/crossgenre").json()["dna"]
    assert "_(tự sinh)_" not in dna


def test_enrich_completes_when_model_omits_genre_section_detail(client, monkeypatch):
    """Root cause of 'enrich incomplete (4 fields remaining)': a genre's own
    section fields (xianxia: mc_spirit_root / mc_starting_realm / mc_age_foundation
    / main_cultivation_method) were counted toward ``done``, but a real model often
    omits these tail-of-prompt detail bullets. With no fallback they stayed empty
    across all passes, so ``done`` never flipped and the client reported exactly
    "4 fields remaining". These render an inline option-hint placeholder in the
    genre template and are author-fillable, so they must be best-effort (still
    requested) and never block completion.
    """
    import provider.llm_client as lc
    from webapp.api.dna_form import genre_section_field_ids

    section_ids = genre_section_field_ids("xianxia")
    assert section_ids  # guard: the genre must actually have section fields

    def omit_genre_section(
        self, *, system=None, user="", messages=None, temperature=None, max_tokens=None
    ):
        keys = re.findall(r'^- "([^"]+)":', user, re.MULTILINE)
        values: dict[str, str] = {}
        for key in keys:
            if key in section_ids:
                continue  # realistic: model omits the genre-section detail bullets
            if key in ("style_model", "worldbuilding_guide"):
                values[key] = "NC"
            elif key == "arc_count":
                values[key] = "5"
            elif key == "supporting_cast":
                values[key] = "- Lạc Yên\n- Tạ Vũ\n- Mộc Đồng"
            elif key == "world_locations":
                values[key] = "Huyền Kinh; Táng Hải; Cổ Thành Vô Danh"
            elif key == "mc_want":
                values[key] = "Báo thù"
            elif key == "mc_need":
                values[key] = "Học cách tin người"
            else:
                values[key] = f"Nội dung {key}"
        return json.dumps(values, ensure_ascii=False)

    monkeypatch.setattr(lc.LLMClient, "complete", omit_genre_section)
    client.put("/api/settings", json={"api_key": "sk-section-123456789"})
    client.post(
        "/api/novels",
        json={
            "name": "sectionomit",
            "fields": {
                "title": "Section Omit",
                "genre": "xianxia",
                "logline": "Một thiếu niên phàm căn nghịch thiên tu tiên.",
                "target_chapters": 30,
            },
        },
    )

    r = client.post("/api/novels/sectionomit/enrich")
    assert r.status_code == 200, r.text
    body = r.json()
    # Enrich completes even though every genre-section field was omitted.
    assert body["done"] is True
    assert body["missing_count"] == 0
    # Omitted section fields are never reported as blocking-missing.
    assert not (section_ids & set(body["missing_fields"]))
