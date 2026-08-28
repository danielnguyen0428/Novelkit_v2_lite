# NovelKit V2 Lite

Studio sáng tác tiểu thuyết dài kỳ bằng AI, chạy hoàn toàn trên máy của một
người dùng. Giao diện React, API FastAPI, SQLite, pipeline và workspace truyện
được đóng gói trong cùng một repo và khởi động bằng một lệnh.

NovelKit V2 Lite là một sản phẩm local-first độc lập. Đây không phải cấu hình
deploy thu nhỏ của một hệ SaaS: runtime không có đăng nhập, tenant, billing,
credit, catalog công khai hay luồng xuất bản công khai.

## Điểm chính

- Vào thẳng Studio tại `/studio`; không có landing page.
- Tạo và hoàn thiện `PROJECT_DNA` theo thể loại hoặc hybrid genre.
- Chạy pipeline nền theo số chương: dựng thế giới, dàn ý, viết, review và sync.
- Quản lý chương, tài liệu, doctor, phân tích, NovelCLI và knowledge graph.
- Dùng endpoint OpenAI-compatible do người dùng tự cấu hình.
- Lưu database, khóa mã hóa và toàn bộ bản thảo trên máy local.
- Tự thu hồi background job mồ côi sau khi service bị restart.

## Kiến trúc trong một hình

```text
Browser
  └─ React Studio
       └─ typed API client
            └─ FastAPI (127.0.0.1)
                 ├─ NovelKitService
                 ├─ persistent run jobs
                 ├─ deterministic pipeline + creative tools
                 ├─ OpenAI-compatible provider
                 ├─ SQLite operational metadata
                 └─ file-first novel workspaces
```

Frontend production được FastAPI phục vụ cùng origin. Không cần chạy web server,
worker queue hay database server riêng.

## Yêu cầu

- Python 3.11 trở lên.
- Node.js 20.19 trở lên hoặc 22.12 trở lên.
- npm.

## Cài đặt

```bash
git clone https://github.com/danielnguyen0428/Novelkit_v2_lite.git
cd Novelkit_v2_lite
./setup.sh
```

`setup.sh` tạo `.venv`, cài Python dependencies, cài frontend dependencies và
build React SPA.

## Chạy

```bash
./run-local.sh
```

Mở <http://127.0.0.1:8000/studio>. Dừng service bằng `Ctrl+C`.

Đổi port khi cần:

```bash
PORT=8080 ./run-local.sh
```

Service mặc định chỉ bind `127.0.0.1`. Không đổi `HOST` thành địa chỉ public nếu
chưa đặt một lớp authentication đáng tin cậy phía trước.

## Cấu hình AI provider

Mở **Settings** trong Studio và nhập:

- base URL tương thích OpenAI API;
- model;
- API key;
- temperature và giới hạn output token nếu cần.

API key được mã hóa trước khi ghi vào SQLite. Khóa mã hóa local nằm tại
`.secrets/master.key` và không được commit. Cũng có thể cấu hình bằng các biến
trong [.env.example](.env.example).

## Dữ liệu local

| Đường dẫn | Vai trò |
| --- | --- |
| `.data/novelkit-lite.db` | Novel metadata, provider settings đã mã hóa, run jobs và usage ledger |
| `.secrets/master.key` | Khóa giải mã provider API key |
| `storage/users/.../novels/<uuid>/` | Workspace canon và artifact của truyện tạo từ Studio |
| `workspaces/` | Root tương thích cho CLI/runtime cũ còn được giữ trong gói |

Các đường dẫn trên đều nằm trong `.gitignore`. Khi backup, phải giữ database,
master key và `storage/` cùng một snapshot; mất master key sẽ làm API key đã lưu
không thể giải mã.

## Phát triển

Backend test trọng tâm:

```bash
./.venv/bin/python -m pytest tests/test_lite_api.py tests/test_webapi.py tests/test_run_jobs.py -q
```

Frontend test và build:

```bash
node --test webapp/frontend/tests/*.test.mjs
npm run build --prefix webapp/frontend
```

Chạy frontend dev server riêng khi cần HMR:

```bash
npm run dev --prefix webapp/frontend
```

Vite proxy `/api` về FastAPI tại `127.0.0.1:8000`.

## Tài liệu

- [ARCHITECTURE.md](ARCHITECTURE.md): ranh giới hệ thống, luồng dữ liệu và bất biến.
- [RUNBOOK.md](RUNBOOK.md): cài đặt, vận hành, backup và xử lý sự cố.
- [KNOWLEDGE_GRAPH.md](KNOWLEDGE_GRAPH.md): mô hình tri thức và quyền sở hữu dữ liệu.
- [KNOWLEDGE_GRAPH_DETAIL.md](KNOWLEDGE_GRAPH_DETAIL.md): bản đồ module, API và artifact.
- [CHANGELOG.md](CHANGELOG.md): thay đổi của riêng bản Lite.

## Phạm vi không có trong Lite

- OAuth, session đăng nhập và quản trị tài khoản.
- Multi-user hoặc multi-tenant isolation qua network.
- Gói mua, thanh toán, credit và usage quota thương mại.
- Public reader, catalog hoặc publishing service.
- Redis, Celery, PostgreSQL hay worker cluster.
- Quản lý API key tập trung trên cloud.

Nếu cần expose ra mạng, hãy coi FastAPI hiện tại là một service nội bộ và đặt
authentication/TLS/reverse proxy ở phía trước.
