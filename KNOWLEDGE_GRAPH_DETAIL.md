# Component map chi tiết — NovelKit V2 Lite

Tài liệu tra cứu nhanh code → responsibility → data. Kiến trúc tổng quan nằm ở
[ARCHITECTURE.md](ARCHITECTURE.md).

## 1. Entry points

| File | Responsibility |
| --- | --- |
| `setup.sh` | Tạo venv, cài dependencies, build frontend |
| `run-local.sh` | Khởi tạo local paths/key và chạy một Uvicorn process |
| `webapp/api/main.py` | FastAPI composition root, API routes, startup recovery, SPA host |
| `webapp/frontend/src/main.tsx` | Mount React application |
| `webapp/frontend/src/router.tsx` | `/` redirect `/studio`, lazy-load Studio |
| `cli.py` | CLI chuyên sâu trên cùng tool registry |
| `bootstrap.py` | Import và verify toàn bộ tool/plugin surface |

## 2. Frontend modules

| Module | Responsibility |
| --- | --- |
| `StudioPage.tsx` | Novel selection, active panel, data refresh, modal/settings state |
| `Sidebar.tsx` | Library và novel selection/delete |
| `CreateNovelModal.tsx` | Thu input DNA, genre/hybrid và author reference metadata |
| `PipelineBoard.tsx` | Run theo chương, persistent status poll, breaker/recovery controls |
| `ChaptersPanel.tsx` | Danh sách và đọc chương |
| `DocsPanel.tsx` | Planning/worldbuilding documents và regenerate stub |
| `DoctorPanel.tsx` | Structural health report |
| `AnalyzePanel.tsx` | AI-flavor/language analysis |
| `NovelCliPanel.tsx` | Advanced CLI-like control surface |
| `GraphPanel.tsx` | Narrative graph projection |
| `SettingsModal.tsx` | OpenAI-compatible provider configuration |
| `ProviderStatusPill.tsx` | Hiển thị trạng thái cấu hình, không auto-probe provider |
| `packages/api-client` | Typed request/response boundary |

## 3. Backend modules

| Module | Responsibility |
| --- | --- |
| `webapp/api/deps.py` | Resolve/create internal local owner |
| `webapp/api/schemas.py` | Pydantic request contracts |
| `webapp/api/service.py` | Application facade và workspace/pipeline orchestration |
| `webapp/api/run_jobs.py` | Persistent async jobs, commands, usage ledger, startup reconciliation |
| `webapp/api/dna_form.py` | DNA form rules, deterministic genre/style routing |
| `webapp/api/dna_genre_fields.py` | Genre-specific form fields |
| `webapp/api/dna_genre_render.py` | Render genre sections vào PROJECT_DNA |
| `webapp/api/novel_paths.py` | Owner-scoped storage paths |
| `webapp/api/provenance.py` | Stable copyright, canonical source và provenance metadata |
| `webapp/api/studio_routes.py` | Narrative graph endpoint |
| `webapp/db/models.py` | SQLAlchemy operational models |
| `webapp/db/session.py` | SQLite engine/session factory |

## 4. API families

### Meta và provider

```text
GET  /api/health
GET  /api/provenance
GET  /api/tools
GET  /api/schedule
GET  /api/provider
GET  /api/settings
PUT  /api/settings
POST /api/settings/test
```

### Novel và DNA

```text
GET/POST       /api/novels
GET/DELETE     /api/novels/{slug}
GET            /api/dna-template
POST           /api/dna-generate
POST           /api/novels/{slug}/enrich
GET/POST       /api/novels/{slug}/artifact
GET            /api/novels/{slug}/docs
POST           /api/novels/{slug}/docs/regenerate
```

### Pipeline và run jobs

```text
POST /api/novels/{slug}/pipeline/plan-next
POST /api/novels/{slug}/pipeline/record-result
POST /api/novels/{slug}/pipeline/resume
POST /api/novels/{slug}/pipeline/recover
POST /api/novels/{slug}/run-step
POST /api/novels/{slug}/run-async
GET  /api/novels/{slug}/run-status
POST /api/novels/{slug}/runs
GET  /api/novels/{slug}/runs/{job_id}
POST/GET /api/novels/{slug}/runs/{job_id}/commands
```

### Canon inspection và analysis

```text
GET  /api/novels/{slug}/chapters
GET  /api/novels/{slug}/chapters/{number}
POST /api/novels/{slug}/sync
GET  /api/novels/{slug}/doctor
GET  /api/novels/{slug}/diagnostics
GET  /api/novels/{slug}/graph
POST /api/analyze/ai-flavor
POST /api/analyze/language-guard
```

API không có auth/account/billing/publication route.

## 5. Tool registry

### Pipeline và canon

| Tool | Responsibility |
| --- | --- |
| `novelkit_pipeline` | DAG, task lifecycle, breaker, queue và resume |
| `novelkit_sync` | Review gate, promote chapter, commit/reindex |
| `novelkit_dna` | Parse/enrich DNA và bootstrap planning docs |
| `novelkit_compass` | Long-form compass, arc/volume expansion |
| `novelkit_graph` | Build/query narrative graph |

### Quality và continuity

| Tool | Responsibility |
| --- | --- |
| `novelkit_gate` | Review scoring và verdict |
| `novelkit_language_guard` | Genre language constraints |
| `novelkit_ai_flavor` | Detect AI-like prose patterns |
| `novelkit_cool_point` | Cool-point analysis |
| `novelkit_style_coherence` | Project voice statistics và repetition guard |
| `novelkit_strand` | Thread/seed/payoff tracking |
| `novelkit_diagnostics` | Read-only creative/runtime diagnostics |

### Context và direction

| Tool | Responsibility |
| --- | --- |
| `novelkit_reference` | Reference text/profile processing |
| `novelkit_recall` | Assemble bounded writer context |
| `novelkit_steer` | Route operator intervention |
| `novelkit-context` | Authority-aware context retrieval plugin |
| `memory.add/search/rotate/build_context` | Per-novel memory provider operations |

## 6. Provider modules

| Module | Responsibility |
| --- | --- |
| `provider/llm_client.py` | OpenAI-compatible completion request |
| `provider/resolver.py` | Resolve effective config/model |
| `provider/settings_db.py` | Persist settings per internal owner |
| `provider/crypto.py` | Fernet encryption/decryption |
| `webapp/api/provider_catalog.py` | UI presets; không phải credential store |

## 7. SQLite model graph

```text
User (one internal local owner)
 ├─ Novel[]
 └─ UserLLMSettings (one, encrypted key)

RunJobRecord
 ├─ RunCommandRecord[]
 └─ UsageLedgerRecord[] (logical job_id link)
```

`Novel.id` là UUID dùng trong path. `Novel.slug` là tên ổn định trong API/UI.

## 8. Workspace layout

```text
storage/users/<owner-id>/novels/<novel-uuid>/
├── PROJECT_DNA.md
├── PROJECT_DNA.form.json
├── PROJECT_DNA.meta.json
├── PLAN.md
├── GOAL_TRACKER.md
├── database/
├── outlines/
├── drafts/
├── reviews/
├── chapters/
├── summaries/
├── memory/
├── style_vault/
├── logs/
│   ├── pipeline_state.json
│   ├── pipeline_status.json
│   ├── checkpoints.jsonl
│   └── transactions/
├── .rag/
└── .commits/
```

File/folder có thể xuất hiện theo tiến độ; không phải novel mới nào cũng có tất
cả ngay khi tạo.

## 9. Data classification

| Class | Ví dụ | Commit? |
| --- | --- | --- |
| Source code/config | `webapp/`, `tools/`, `config/` | Có |
| Product docs/canon templates | root docs, `skills/novelkit-canon/` | Có |
| Build/cache | `.venv`, `node_modules`, `dist`, `__pycache__` | Không |
| Operational metadata | `.data/` | Không |
| Secrets | `.secrets/`, `.env` | Không |
| User manuscript | `storage/`, `workspaces/` | Không |

## 10. Core invariants

1. API path không được thoát novel workspace.
2. Một novel chỉ có một active run.
3. LLM không trực tiếp mutate pipeline state.
4. Writer không trực tiếp promote draft vào canonical chapter.
5. Canon thắng derivative context.
6. Provider key không trở lại client ở dạng rõ.
7. Persisted error/usage không chứa raw prompt hoặc key.
8. Startup không giữ active job từ process đã chết.
9. Completed job không bị startup reconciliation thay đổi.
10. UI dùng persistent run status, không chỉ React state của một tab.

## 11. Verification map

| Boundary | Tests |
| --- | --- |
| Lite API/product scope | `tests/test_lite_api.py` |
| HTTP/service flows | `tests/test_webapi.py`, `tests/test_webapi_llm.py` |
| Persistent jobs/recovery | `tests/test_run_jobs.py`, `tests/test_run_lock_leak.py` |
| Pipeline/state/sync | `tests/test_pipeline_*.py`, `tests/test_sync_tool.py` |
| Canon/model wiring | `tests/test_canon_reaches_model.py`, `tests/test_system_canon_wiring.py` |
| Frontend control policy | `webapp/frontend/tests/*.test.mjs` |
| Registry completeness | `tests/test_tool_registry_complete.py` |
