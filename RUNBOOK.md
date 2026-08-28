# Runbook NovelKit V2 Lite

Runbook này dành cho một operator chạy NovelKit trên máy local.

## 1. Cài đặt lần đầu

```bash
./setup.sh
```

Script thực hiện bốn việc:

1. kiểm tra `python3` và `npm`;
2. tạo `.venv`;
3. cài `webapp/requirements.txt` cùng pytest;
4. cài và build frontend production.

Chạy lại `setup.sh` khi dependencies thay đổi hoặc frontend build bị thiếu.

## 2. Khởi động và dừng

```bash
./run-local.sh
```

Mặc định:

- host: `127.0.0.1`;
- port: `8000`;
- Studio: <http://127.0.0.1:8000/studio>;
- health: <http://127.0.0.1:8000/api/health>.

Dừng foreground service bằng `Ctrl+C`.

Đổi port:

```bash
PORT=8080 ./run-local.sh
```

Chỉ đổi host khi đã có authentication proxy:

```bash
HOST=127.0.0.1 PORT=8080 ./run-local.sh
```

## 3. Kiểm tra service

```bash
curl -fsS http://127.0.0.1:8000/api/health
```

Kết quả bình thường:

```json
{"status":"ok","tools":20}
```

Kiểm tra frontend:

```bash
curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/studio
```

Kết quả mong đợi: `200`.

## 4. Cấu hình provider

Cách ưu tiên là dùng **Settings** trong Studio. Có thể dùng environment:

```bash
export NOVELKIT_LLM_BASE_URL='https://api.openai.com/v1'
export NOVELKIT_LLM_MODEL='your-model'
export NOVELKIT_LLM_API_KEY='your-key'
./run-local.sh
```

Các biến hỗ trợ nằm trong `.env.example`. `run-local.sh` không tự source `.env`;
nếu dùng file, hãy export biến bằng shell hoặc công cụ quản lý môi trường của anh.

Nút **Test provider** mới tạo một request kiểm tra. Topbar không tự tiêu token để
probe provider.

## 5. Dữ liệu và backup

### Những gì phải backup

```text
.data/novelkit-lite.db
.secrets/master.key
storage/
workspaces/        # nếu có novel/CLI artifact cũ trong đây
```

### Snapshot nhất quán

1. Dừng service bằng `Ctrl+C`.
2. Sao chép bốn vị trí trên vào cùng một thư mục backup.
3. Khởi động lại service.

Không backup riêng database mà bỏ master key: provider API key trong database sẽ
không thể giải mã. Không backup riêng `storage/`: SQLite giữ mapping slug và UUID.

### Restore

1. Dừng service.
2. Đặt lại database, master key và storage từ cùng snapshot.
3. Kiểm tra quyền đọc file `.secrets/master.key`.
4. Chạy `./run-local.sh` và gọi `/api/health`.
5. Mở Studio, kiểm tra danh sách novel và một artifact trước khi chạy AI.

## 6. Background run

Nút **Để AI tự viết** gửi một job chạy theo số chương. UI poll
`/api/novels/<slug>/run-status` mỗi bốn giây.

Job có thể ở các trạng thái:

| Trạng thái | Ý nghĩa |
| --- | --- |
| `queued` | Đã ghi DB, thread chuẩn bị chạy |
| `running` | Creative loop đang giữ lock novel |
| `pausing` | Đang chờ ranh giới an toàn để pause |
| `completed` | Run kết thúc bình thường |
| `failed` | Run dừng vì lỗi hoặc process restart |

Nếu service chết giữa run, lần startup kế tiếp tự đánh dấu job mồ côi là
`failed/process_restarted`. Nội dung đã sync vẫn giữ nguyên; operator có thể bấm
chạy lại để tiếp tục task kế.

## 7. Xử lý sự cố

### Studio không mở

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
./run-local.sh
```

Nếu port bận, dùng port khác. Nếu báo thiếu frontend build, chạy:

```bash
npm run build --prefix webapp/frontend
```

### Nút AI bị khóa

Kiểm tra run status:

```bash
curl -fsS http://127.0.0.1:8000/api/novels/<slug>/run-status
```

- `queued/running/pausing`: một job thật đang chạy; chờ hoặc kiểm tra process.
- `failed` với `process_restarted`: job cũ đã được thu hồi; reload Studio.
- breaker mở: dùng hành động khôi phục trong Studio sau khi đọc lỗi.
- DNA chưa hoàn chỉnh: hoàn thiện `PROJECT_DNA` trước khi viết.
- provider chưa cấu hình: mở Settings.

Không sửa trực tiếp bảng `run_jobs` khi service đang chạy.

### Provider lỗi

1. Mở Settings.
2. Kiểm tra base URL có kết thúc đúng `/v1` theo provider.
3. Kiểm tra model ID.
4. Bấm **Test provider**.
5. Nếu đổi master key, nhập lại API key.

API không persist raw provider exception có thể chứa prompt/key; run job chỉ giữ
stable error code.

### Novel hiện `missing`

SQLite còn record nhưng owner-scoped directory trong `storage/` không tồn tại.
Khôi phục `storage/` từ cùng snapshot database hoặc xóa record bằng UI nếu novel
không còn cần thiết.

## 8. Development mode

Terminal 1:

```bash
./run-local.sh
```

Terminal 2:

```bash
npm run dev --prefix webapp/frontend
```

Mở URL Vite hiển thị trong terminal. Proxy mặc định chuyển `/api` về
`http://127.0.0.1:8000`.

## 9. Verification

Backend regression gần HTTP/job boundary:

```bash
./.venv/bin/python -m pytest \
  tests/test_lite_api.py \
  tests/test_webapi.py \
  tests/test_run_jobs.py -q
```

Frontend:

```bash
node --test webapp/frontend/tests/*.test.mjs
npm run build --prefix webapp/frontend
```

Registry:

```bash
./.venv/bin/python -c 'import bootstrap; print(bootstrap.verify_registry())'
```

## 10. Security checklist

- Service chỉ bind loopback.
- `.data/`, `.secrets/`, `storage/`, `workspaces/` và `.env` không được track.
- `master.key` có quyền file hạn chế và đi cùng backup database.
- Không paste API key vào issue/log.
- Trước khi push, chạy `git status --ignored` và secret scan.
- Không publish repo kèm novel workspace hoặc provider configuration.
