# Kiến trúc NovelKit V2 Lite

Tài liệu này mô tả code đang chạy trong repo Lite. Mục tiêu kiến trúc là giữ
pipeline sáng tác dài kỳ có kiểm soát, nhưng vận hành bằng một process local,
một operator và dữ liệu file-first.

## 1. Ranh giới sản phẩm

NovelKit V2 Lite có bốn ràng buộc nền:

1. **Local-only:** HTTP bind vào `127.0.0.1` theo mặc định.
2. **Single operator:** mọi request được ánh xạ tới một internal owner ổn định;
   không có login/session/OAuth.
3. **Bring-your-own provider:** model và API key do operator cấu hình.
4. **File-first canon:** nội dung truyện nằm trong workspace; SQLite giữ metadata
   vận hành, không thay thế canon.

Các ràng buộc này là kiến trúc chính thức, không phải feature flag.

## 2. System context

```text
┌──────────────────────────────────────────────────────────────┐
│ Local browser                                                │
│ React 18 + TypeScript + Vite                                 │
│ / → /studio                                                  │
└──────────────────────────────┬───────────────────────────────┘
                               │ JSON / same origin
┌──────────────────────────────▼───────────────────────────────┐
│ FastAPI                                                      │
│ Routes · validation · local-owner dependency · SPA hosting   │
└───────────────┬──────────────────────────┬───────────────────┘
                │                          │
┌───────────────▼──────────────┐  ┌────────▼──────────────────┐
│ NovelKitService             │  │ Persistent run jobs       │
│ workspace + pipeline facade │  │ DB state + daemon thread  │
└───────────────┬──────────────┘  └────────┬──────────────────┘
                └──────────────┬────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Creative runtime                                             │
│ PipelineEngine · PipelineStateStore · AutoNovelAdapter       │
│ 15 novelkit_* tools · context plugin · memory plugin         │
└───────────────┬──────────────────────────┬───────────────────┘
                │                          │ HTTPS
┌───────────────▼──────────────┐  ┌────────▼──────────────────┐
│ Local persistence           │  │ OpenAI-compatible API     │
│ SQLite + novel workspaces   │  │ selected by operator      │
└──────────────────────────────┘  └───────────────────────────┘
```

Không có message broker hoặc worker process riêng. Background run là daemon
thread của Uvicorn; metadata job được ghi vào SQLite để UI có thể theo dõi qua
reload hoặc tab khác.

## 3. Các lớp runtime

### 3.1 Studio frontend

- Entry: `webapp/frontend/src/main.tsx`.
- Router: `/` redirect thẳng sang `/studio`.
- `StudioPage` sở hữu novel selection, panel đang mở và provider state.
- `PipelineBoard` điều khiển run theo số chương và poll `/run-status`.
- `packages/api-client` là contract TypeScript dùng chung với HTTP API.
- Production assets nằm trong `webapp/frontend/dist/` và không commit.

Frontend không truy cập filesystem, SQLite hoặc provider trực tiếp.

### 3.2 HTTP application

`webapp/api/main.py` là composition root:

- dựng FastAPI và CORS cho Vite dev server;
- tạo schema SQLite khi startup;
- thu hồi `queued/running/pausing` job còn sót từ process trước;
- đăng ký API routes;
- phục vụ React SPA ở mọi non-API route hợp lệ.

`webapp/api/deps.py` tạo một local owner nội bộ. Owner này chỉ dùng để tái sử
dụng ownership boundary trong database và đường dẫn; nó không phải tài khoản.

### 3.3 Application service

`webapp/api/service.py` là facade giữa HTTP và creative runtime. Nó chịu trách
nhiệm:

- tạo/xóa/list novel và kiểm tra owner;
- render, enrich và lưu `PROJECT_DNA`;
- đọc/ghi artifact trong phạm vi workspace an toàn;
- nạp/lưu pipeline state với optimistic version;
- chạy adapter sáng tác, doctor, diagnostics, graph và sync;
- chuyển lỗi có thể sửa bởi người dùng thành HTTP status phù hợp.

Route handler phải mỏng; quyết định workspace và pipeline nằm ở service/tool.

### 3.4 Background run jobs

`webapp/api/run_jobs.py` lưu mỗi run trong bảng `run_jobs`, sau đó chạy
`NovelKitService.run()` trong daemon thread.

Trạng thái active: `queued`, `running`, `pausing`. Khi process kết thúc đột ngột,
thread không thể sống sót; startup kế tiếp chuyển các bản ghi active cũ sang:

```text
status=failed
error_code=process_restarted
stopped_reason=process_restarted
```

Nhờ đó job cũ không khóa nút chạy vô hạn. UI poll persistent job status mỗi bốn
giây và kết hợp nó với state local của tab.

### 3.5 Deterministic control plane

`PipelineEngine` quyết định task order, dependencies, retry, breaker và chapter
gating. `PipelineStateStore` ghi `logs/pipeline_state.json` nguyên tử và sinh
`pipeline_status.json` làm projection đọc nhanh.

Flow chương chuẩn:

```text
outline → write draft → self-check → review → sync
```

Writer chỉ tạo draft. `novelkit_sync` là đường promote nội dung đã qua gate vào
`chapters/`; task hoàn tất không được chạy lại khi resume.

### 3.6 Creative tools và plugins

`bootstrap.py` đăng ký 15 tool `novelkit_*`. Hai plugin bổ sung context retrieval
và memory operations; HTTP health hiện nhìn thấy tổng cộng 20 capability entry.

Mọi tool được gọi qua `delegate.delegate_tool`, tạo một seam duy nhất giữa
application service và domain capability. Subagent `SOUL.md` chỉ cung cấp vai
trò sáng tác; chúng không sở hữu pipeline state.

### 3.7 Provider boundary

`provider/llm_client.py` gọi Chat Completions-compatible endpoint. Resolver nạp
setting đã lưu trong SQLite hoặc environment. API key:

- được mã hóa bằng Fernet trước khi ghi database;
- không được trả lại ở dạng rõ qua API;
- cần `.secrets/master.key` để giải mã;
- không xuất hiện trong usage ledger hoặc error message persisted.

## 4. Persistence và quyền sở hữu

### SQLite: operational metadata

`.data/novelkit-lite.db` chứa:

- internal local owner;
- novel metadata và mapping slug → workspace UUID;
- provider configuration đã mã hóa;
- persistent run jobs và run commands;
- usage ledger đã redacted.

### Workspace: narrative canon

Studio tạo workspace tại:

```text
storage/users/<owner-id>/novels/<novel-uuid>/
```

Canon gồm `PROJECT_DNA`, database nhân vật/thế giới, outlines, chapters, reviews,
summaries và curated memory. Logs, RAG index, checkpoints và status projection là
runtime/derivative; chúng không được ưu tiên cao hơn canon khi build context.

`workspaces/` vẫn tồn tại như compatibility root cho các đường CLI/runtime cũ,
nhưng novel tạo từ Studio dùng owner-scoped `storage/`.

## 5. Các luồng chính

### Tạo novel

```text
CreateNovelModal
  → POST /api/novels
  → validate fields + deterministic routing
  → insert Novel row
  → create owner-scoped workspace
  → write PROJECT_DNA + metadata sidecars
  → bootstrap planning docs + RAG index
  → seed compass pipeline
```

### Chạy AI theo chương

```text
PipelineBoard
  → POST /run-async
  → persist queued RunJobRecord
  → daemon thread marks running
  → service acquires per-novel thread + file lock
  → adapter executes ready tasks
  → provider calls generate artifacts
  → gate/review/sync advance canon
  → job completes or fails with redacted code
```

### Startup/recovery

```text
process starts
  → create_all
  → fail orphaned active run records
  → UI reloads
  → pipeline resume releases orphan task claims
  → operator may start the next run
```

## 6. Concurrency và failure safety

- Một novel chỉ có một run tại một thời điểm.
- In-process `threading.Lock` kết hợp advisory file lock `.run.lock`.
- Lock acquisition không chờ; conflict trả `alreadyRunning` thay vì ghi đè state.
- State dùng digest/version để phát hiện stale write.
- Sync dùng manifest và content hashes để hỗ trợ idempotency/recovery.
- Persisted exception chỉ giữ stable error code, không giữ prompt, key hoặc bản
  thảo.
- Job mồ côi được thu hồi ở startup; task claim mồ côi được release bằng resume.

## 7. Security model

Lite không có authentication vì chỉ dành cho loopback. Mọi API mutation được xem
là có toàn quyền với dữ liệu local. Do đó:

- không bind vào interface công khai;
- không commit `.data`, `.secrets`, `storage`, `workspaces` hoặc `.env`;
- không gửi backup chứa master key hoặc bản thảo cho bên thứ ba;
- nếu expose qua LAN/Internet, bắt buộc thêm TLS và authentication proxy.

## 8. Bố cục repo

```text
webapp/api/              FastAPI routes, service, jobs, schemas
webapp/frontend/         React Studio và frontend tests
webapp/db/               SQLAlchemy models/session
packages/api-client/     TypeScript API contract
provider/                provider resolver, HTTP client, encryption
integrations/autonovel/  adapter và LLM creative loop
tools/                   deterministic domain capabilities
plugins/                 context-engine và memory-provider
skills/novelkit-canon/   genre canon, templates và domain rules
subagents/               creative role profiles
config/                  runtime/domain configuration
tests/                   backend, property và integration tests
LICENSE                  điều khoản source-available NC/ND
NOTICE                   thông báo bản quyền và provenance ID
PROVENANCE.json          manifest nguồn gốc cho máy đọc
```

## 9. Provenance và quyền riêng tư

Mỗi HTTP response mang header `X-NovelKit-Provenance`; endpoint
`GET /api/provenance` trả cùng metadata với `PROVENANCE.json`. Frontend và package
metadata cũng giữ canonical repository và provenance ID. Đây là các dấu thụ động
để đối chiếu nguồn gốc, không phải telemetry: runtime không gọi về server của tác
giả và không gửi dữ liệu người dùng.

Giấy phép yêu cầu giữ nguyên các dấu này trên bản sao được phép phân phối. Repo
public vẫn không thể làm một marker trong source trở thành bất khả xóa; bằng
chứng gốc được neo thêm bằng lịch sử Git, origin commit và release tag.

## 10. Những thứ cố ý không có

Không có OAuth, account API, tenant switching, payment, credit, public catalog,
reader page, publishing backend, Redis/Celery, PostgreSQL hay cloud secrets
manager. Thêm một trong các phần này là thay đổi product boundary, không phải
việc bật cấu hình.
