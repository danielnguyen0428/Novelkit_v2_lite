# Changelog — NovelKit V2 Lite

Changelog này chỉ theo dõi sản phẩm Lite độc lập.

## Unreleased

- Khởi tạo repo độc lập `Novelkit_v2_lite`.
- Viết lại README, kiến trúc, runbook và knowledge graph theo runtime local hiện tại.
- Công khai theo giấy phép source-available phi thương mại, không phái sinh.
- Thêm provenance manifest, API endpoint và HTTP/frontend/package metadata;
  không thêm telemetry.
- Bổ sung README English, Simplified Chinese, Korean và Japanese với language
  switcher nhất quán.
- Thêm Mermaid diagrams cho product loop, system context, run sequence,
  long-form pipeline, job lifecycle, data authority, storage và knowledge graph.
- Bổ sung positioning business về genre craft, long-term memory, Quality Gate,
  production readiness, catalog scale và partnership với Full NovelKit.

## 2026-08-28 — Lite repository baseline

### Product boundary

- Single-operator, local-only FastAPI + React Studio.
- Một internal owner; không có login, billing, public catalog hoặc publishing.
- Bring-your-own OpenAI-compatible provider với API key mã hóa local.

### Studio

- `/` đi thẳng vào `/studio`.
- Thư viện trống hiển thị create action trong Studio.
- Run chính dùng số chương và background job persistent.
- UI poll run status để đồng bộ qua reload/tab khác.

### Runtime safety

- SQLite lưu operational metadata, encrypted provider settings và usage ledger.
- Owner-scoped file workspace giữ narrative canon.
- Per-novel thread/file lock chống hai run ghi đồng thời.
- Startup thu hồi job `queued/running/pausing` từ process cũ bằng
  `failed/process_restarted`.

### Author references

- Giữ nguyên tên/mã của 40 author reference profile.
- Profile chỉ còn nhận diện trung tính; runtime không dùng tên tác giả để mô
  phỏng nhịp, từ vựng, cấu trúc hoặc cấm kỵ.
- Project voice lấy từ `PROJECT_DNA` và genre register.
