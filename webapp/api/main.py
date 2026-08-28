"""FastAPI application — HTTP surface over the NovelKit tool registry.

Run (dev)::

    cd "Novelkit V2-lite"
    /path/to/.venv/bin/python -m uvicorn webapp.api.main:app --reload --port 8000

The built React SPA (``webapp/frontend/dist``) is served at ``/`` when present,
so the API and UI run as one local unit.

SECURITY: this API is UNAUTHENTICATED by design for local/single-operator use.
Do NOT expose it to an untrusted network without putting an auth proxy
(or a gateway with auth) in front of it — every endpoint can mutate novel state.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from webapp.api.deps import get_current_user
from webapp.db.models import Base, User
from webapp.db.session import engine, get_db

from .schemas import (
    AnalyzeRequest,
    CompassMigrateRequest,
    CreateNovelRequest,
    DnaGenerateRequest,
    PlanNextRequest,
    ProviderSettingsRequest,
    ProviderTestRequest,
    RecordResultRequest,
    RegenerateDocRequest,
    RunRequest,
    SteerRequest,
    SyncRequest,
    WriteArtifactRequest,
)
from .service import SERVICE, RunBusyError, ServiceError
from .studio_routes import router as studio_router

app = FastAPI(
    title="NovelKit V2-lite",
    version="1.0.0",
    description="Local-only web surface for the NovelKit creative tool registry.",
)

allow_origins = os.environ.get(
    "NOVELKIT_CORS_ORIGINS",
    "http://127.0.0.1:5173,http://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(studio_router)


@app.on_event("startup")
def _create_db_tables() -> None:
    Base.metadata.create_all(bind=engine)
    from .run_jobs import recover_orphaned_run_jobs

    recover_orphaned_run_jobs()


# --------------------------------------------------------------------------- #
# Error mapping
# --------------------------------------------------------------------------- #


@app.exception_handler(ServiceError)
async def _service_error_handler(_request, exc: ServiceError):  # noqa: ANN001
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


def _guard(fn):
    """Wrap a service call, translating ServiceError → HTTPException is handled
    by the exception handler; this keeps route bodies tiny."""
    return fn


# --------------------------------------------------------------------------- #
# Meta / read endpoints
# --------------------------------------------------------------------------- #


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "tools": len(SERVICE.tools())}


@app.get("/api/tools")
def tools() -> list[str]:
    return SERVICE.tools()


@app.get("/api/schedule")
def schedule() -> Any:
    return SERVICE.schedule()


@app.get("/api/provider")
def provider() -> Any:
    return SERVICE.provider()


# --------------------------------------------------------------------------- #
# Provider settings (LLM API key) — key is never returned, only status.
# --------------------------------------------------------------------------- #


@app.get("/api/settings")
def get_settings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return SERVICE.provider_settings(db, user)


@app.get("/api/settings/providers")
def get_provider_catalog() -> Any:
    from .provider_catalog import provider_catalog

    return provider_catalog()


@app.put("/api/settings")
def put_settings(
    req: ProviderSettingsRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return SERVICE.save_provider_settings(
        db,
        user,
        provider=req.provider,
        base_url=req.base_url,
        model=req.model,
        api_key=req.api_key,
    )


@app.post("/api/settings/test")
def test_settings(
    req: ProviderTestRequest = Body(default_factory=ProviderTestRequest),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return SERVICE.test_provider(
        db,
        user,
        base_url=req.base_url,
        model=req.model,
        api_key=req.api_key,
    )


@app.get("/api/inventory")
def inventory() -> dict[str, Any]:
    return SERVICE.inventory_summary()


@app.get("/api/suggest-characters")
def suggest_characters() -> Any:
    """Get a random character setup suggestion (MC & Antagonist) from tailieu files."""
    return SERVICE.suggest_characters()


@app.get("/api/suggest-seed")
def suggest_seed() -> Any:
    """Get a random story seed suggestion (logline, usp, theme, audience) from tailieu/hatgiong.md."""
    return SERVICE.suggest_seed()


@app.get("/api/suggest-companions")
def suggest_companions() -> Any:
    """Get a random companion setup suggestion (artifact, spirit_beast, supporting_cast) from tailieu/donghanh.md."""
    return SERVICE.suggest_companions()


@app.get("/api/suggest-cultivation")
def suggest_cultivation(style_model: str | None = None) -> Any:
    """Get a random cultivation milestones suggestion (cultivation_age_benchmarks) from tailieu/tuluyen.md."""
    return SERVICE.suggest_cultivation(style_model)






# --------------------------------------------------------------------------- #
# Novels
# --------------------------------------------------------------------------- #


@app.get("/api/dna-template")
def dna_template() -> Any:
    """Form schema mirroring the PROJECT_DNA FILLABLE template."""
    return SERVICE.dna_schema()


@app.post("/api/dna-generate")
def dna_generate(
    req: DnaGenerateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Quick Setup: AI fills the PROJECT_DNA fields from a short brief."""
    return SERVICE.generate_dna_fields(
        brief=req.brief,
        genre=req.genre,
        title=req.title,
        output_language=req.output_language,
        output_language_custom=req.output_language_custom,
        db=db,
        user=user,
    )


@app.post("/api/novels/{name}/enrich")
def enrich_dna(
    name: str,
    max_batches: int | None = Query(None, ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """AI-complete the deep PROJECT_DNA sections for an existing novel."""
    return SERVICE.enrich_dna(db, user, name, max_batches=max_batches)


@app.get("/api/novels")
def list_novels(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return SERVICE.list_novels(db, user)


@app.post("/api/novels", status_code=201)
def create_novel(
    req: CreateNovelRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return SERVICE.create_novel(db, user, name=req.name, fields=req.fields)


@app.get("/api/novels/{name}")
def novel_detail(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return SERVICE.novel_detail(db, user, name)


@app.delete("/api/novels/{name}")
def delete_novel(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return SERVICE.delete_novel(db, user, name)


@app.get("/api/novels/{name}/chapters")
def chapters(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return SERVICE.chapters(db, user, name)


@app.get("/api/novels/{name}/artifact")
def read_artifact(
    name: str,
    path: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Read a step-produced artifact file (by workspace-relative path) as text."""
    return SERVICE.read_artifact(db, user, name, path)


@app.post("/api/novels/{name}/artifact")
def write_artifact(
    name: str,
    req: WriteArtifactRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Write or update an existing artifact/planning document file in the novel workspace."""
    return SERVICE.write_artifact(db, user, name, relpath=req.path, text=req.text)


@app.get("/api/novels/{name}/docs")
def list_docs(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """List planning/worldbuilding docs generated during writing (Tài liệu tab)."""
    return SERVICE.list_docs(db, user, name)


@app.post("/api/novels/{name}/docs/regenerate")
def regenerate_doc(
    name: str,
    req: RegenerateDocRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Regenerate ONE stubbed bootstrap canon doc on demand (Tài liệu tab)."""
    try:
        return SERVICE.regenerate_doc(db, user, name, relpath=req.path)
    except RunBusyError:
        return {"alreadyRunning": True}


@app.get("/api/novels/{name}/chapters/{chapter}")
def chapter_content(
    name: str,
    chapter: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return SERVICE.chapter_content(db, user, name, chapter)


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #


@app.post("/api/novels/{name}/pipeline/plan-next")
def plan_next(
    name: str,
    req: PlanNextRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return {"ready_task": SERVICE.plan_next(db, user, name, claim=req.claim)}
    except RunBusyError:
        return {"alreadyRunning": True, "ready_task": None}


@app.post("/api/novels/{name}/pipeline/record-result")
def record_result(
    name: str,
    req: RecordResultRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        return SERVICE.record_result(
            db, user, name, task_key=req.task_key, result=req.result, score=req.score
        )
    except RunBusyError:
        return {"alreadyRunning": True}


@app.post("/api/novels/{name}/pipeline/resume")
def resume(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        return SERVICE.resume(db, user, name)
    except RunBusyError:
        return {"alreadyRunning": True}


@app.post("/api/novels/{name}/pipeline/rolling-seed")
def rolling_seed(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    try:
        return SERVICE.rolling_seed(db, user, name)
    except RunBusyError:
        return {"alreadyRunning": True}


@app.post("/api/novels/{name}/pipeline/recover")
def recover(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Clear an open circuit breaker so a wedged run can make progress again."""
    try:
        return SERVICE.recover(db, user, name)
    except RunBusyError:
        return {"alreadyRunning": True}


@app.post("/api/novels/{name}/pipeline/approve")
def approve_chapter(
    name: str,
    req: SyncRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Manually pass a chapter the AI could not lift above the quality bar."""
    try:
        return SERVICE.approve_chapter(db, user, name, chapter=req.chapter)
    except RunBusyError:
        return {"alreadyRunning": True}


@app.post("/api/novels/{name}/run")
def run_novel(
    name: str,
    req: RunRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Auto-advance the pipeline with the real LLM creative loop."""
    try:
        return SERVICE.run(
            db, user, name, max_steps=req.max_steps, stop_after_chapters=req.chapters
        )
    except RunBusyError:
        return {"alreadyRunning": True}


@app.post("/api/novels/{name}/run-step")
def run_step(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Run exactly one creative step (for realtime, per-step UI driving)."""
    try:
        return SERVICE.run_step(db, user, name)
    except RunBusyError:
        return {"alreadyRunning": True, "step": None, "finished": False,
                "blocked": False, "breaker_open": False, "status": "running"}


@app.post("/api/novels/{name}/run-async")
def run_async(
    name: str,
    req: RunRequest,
    user: User = Depends(get_current_user),
) -> Any:
    """Enqueue a server-side AI run job (mobile-friendly; survives app backgrounding)."""
    from .run_jobs import start_run_async

    return start_run_async(
        None, user, name, max_steps=req.max_steps, stop_after_chapters=req.chapters
    )


@app.get("/api/novels/{name}/run-status")
def run_status(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Poll progress of the latest async run job for a novel."""
    SERVICE._require_owned_novel(db, user, name)
    from .run_jobs import get_run_status

    return get_run_status(user.id, name)


@app.post("/api/novels/{name}/runs")
def create_run(
    name: str,
    req: RunRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Spec 2.2.0 run enqueue endpoint backed by persistent DB state."""
    SERVICE._require_owned_novel(db, user, name)
    from .run_jobs import start_run_async

    return start_run_async(
        None, user, name, max_steps=req.max_steps, stop_after_chapters=req.chapters
    )


@app.get("/api/novels/{name}/runs/{job_id}")
def get_run(
    name: str,
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Spec 2.2.0 run status endpoint."""
    SERVICE._require_owned_novel(db, user, name)
    from .run_jobs import get_run_status

    return get_run_status(user.id, name, job_id=job_id)


@app.post("/api/novels/{name}/runs/{job_id}/commands")
def create_run_command(
    name: str,
    job_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Persist a step-boundary command for a run."""
    SERVICE._require_owned_novel(db, user, name)
    command_type = str(payload.get("command_type") or "")
    raw_expected = payload.get("expected_state_version")
    expected = int(raw_expected) if raw_expected is not None else None
    from .run_jobs import enqueue_run_command, mark_run_command

    try:
        command = enqueue_run_command(
            user.id,
            name,
            job_id,
            command_type=command_type,
            payload=dict(payload.get("payload") or {}),
            expected_state_version=expected,
        )
        applied = SERVICE.apply_run_command(
            db,
            user,
            name,
            command_type=command_type,
            payload=dict(payload.get("payload") or {}),
            expected_state_version=expected,
        )
        if applied.get("applied"):
            command = mark_run_command(command["id"], status="applied") or command
        return {**command, "application": applied}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    except ServiceError as exc:
        if "command" in locals():
            mark_run_command(command["id"], status="failed")
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.get("/api/novels/{name}/runs/{job_id}/commands")
def get_run_commands(
    name: str,
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """List step-boundary commands for a run."""
    SERVICE._require_owned_novel(db, user, name)
    from .run_jobs import list_run_commands

    return {"commands": list_run_commands(user.id, name, job_id)}


# --------------------------------------------------------------------------- #
# Sync + doctor
# --------------------------------------------------------------------------- #


@app.post("/api/novels/{name}/sync")
def sync(
    name: str,
    req: SyncRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return SERVICE.sync(db, user, name, chapter=req.chapter)


@app.get("/api/novels/{name}/doctor")
def doctor(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return SERVICE.doctor(db, user, name)


# --------------------------------------------------------------------------- #
# Long-form GA surface (NovelCLI): compass · steer · diagnostics · reminder
# --------------------------------------------------------------------------- #


@app.get("/api/novels/{name}/longform")
def longform_status(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Aggregate long-form status: mode, feature flags, compass, arc-map,
    pending steer, per-turn reminder and the completion guard (read-only)."""
    return SERVICE.longform_status(db, user, name)


@app.post("/api/novels/{name}/steer")
def steer(
    name: str,
    req: SteerRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return SERVICE.steer(db, user, name, text=req.text)


@app.get("/api/novels/{name}/diagnostics")
def diagnostics(
    name: str,
    redact: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return SERVICE.diagnostics(db, user, name, redact=redact)


@app.post("/api/novels/{name}/compass/migrate")
def compass_migrate(
    name: str,
    req: CompassMigrateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    return SERVICE.compass_migrate(
        db, user, name,
        current_chapter=req.current_chapter,
        target_chapters=req.target_chapters,
    )


# --------------------------------------------------------------------------- #
# Creative analysis helpers (for an editor panel)
# --------------------------------------------------------------------------- #


@app.post("/api/analyze/ai-flavor")
def analyze_ai_flavor(req: AnalyzeRequest) -> Any:
    return SERVICE.analyze_ai_flavor(req.text)


@app.post("/api/analyze/language-guard")
def analyze_language_guard(req: AnalyzeRequest) -> Any:
    if not req.genre:
        raise HTTPException(status_code=422, detail="genre is required")
    return SERVICE.language_guard(req.text, req.genre, req.secondary_genre)


# --------------------------------------------------------------------------- #
# Static SPA serving (built frontend) — mounted last so /api/* wins.
# --------------------------------------------------------------------------- #

_FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"

if _FRONTEND_DIST.is_dir():
    _INDEX_HTML = _FRONTEND_DIST / "index.html"

    app.mount(
        "/assets",
        StaticFiles(directory=_FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/")
    def _spa_index() -> FileResponse:
        return FileResponse(_INDEX_HTML)

    @app.get("/studio")
    def _spa_shell() -> FileResponse:
        # Client-side routes — /api/* is registered above and takes precedence.
        return FileResponse(_INDEX_HTML)
