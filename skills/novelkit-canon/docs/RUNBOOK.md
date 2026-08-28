# RUNBOOK.md — Vận Hành NovelKit

**Author:** Dũng Nguyễn  
**Version:** 2.1.06

Runbook này mô tả cách vận hành hệ thống theo runtime hiện tại. Nó tập trung vào orchestration, memory, control plane và quality gates, không thay đổi nghiệp vụ văn phong trong `STYLE_GUIDE.md`.

## 1. Khởi Tạo Tác Phẩm

### Bước 1: Chọn genre và squad

Novel Agents Orchestrator route theo prompt squad phù hợp:

- `sub_agents/` cho Xianxia
- `sub_agents_ngon_tinh/` cho Romance
- `sub_agents_xuyen_khong/` cho Transmigration
- `sub_agents_he_thong/` cho System
- `sub_agents_do_thi/` cho Urban
- `sub_agents_khoa_huyen/` cho Sci-fi

Lưu ý vận hành:

- prompt squads hiện có 6
- shared canon trong `system/` hiện có 16 (Xianxia, Urban, Romance, Time Travel, Sci-fi, Meta Genre, Rules Horror, Cthulhu, War Espionage, Apocalypse, Many Children, Substitute, Short Form, Dark Theme, eSports, Streaming)

Mọi genre đều đã có canon pack. Có thể chạy production cho cả 16.

### Bước 1b: Hybrid Genre (tùy chọn)

Nếu truyện pha trộn 2 thể loại, khai báo trong `PROJECT_DNA.md` frontmatter:

```yaml
genre: hybrid
genre_secondary: <genre phụ>         # vd: xianxia, urban, romance...
hybrid_ratio: 70-30                    # hoặc 60-40, 50-50
canon_pack: system/<Primary>/
canon_pack_secondary: system/<Secondary>/
```

Quy tắc:

- Primary quyết định squad, Đại Thần, consistency rules CHÍNH
- Secondary bổ sung canon đọc thêm (nới lỏng vocabulary blacklist, thêm worldbuilding)
- Xung đột rule ⇒ primary thắng
- Quality Auditor kiểm tra cả 2 rule sets khi review

Các combo đã có template: Đô Thị + Tu Chân, Xuyên Không + Hệ Thống, Tiên Hiệp + Khoa Huyễn, Ngôn Tình + Xuyên Không, Đô Thị + Hệ Thống, Khoa Huyễn + Hệ Thống. Chi tiết tại [`templates/PROJECT_DNA_TEMPLATE.md`](/Users/meow/.openclaw/workspace/templates/PROJECT_DNA_TEMPLATE.md).

### Bước 2: Phỏng vấn PROJECT_DNA

Novel Agents Orchestrator thu thập thông tin nền cho truyện:

1. seed/logline
2. style direction
3. world
4. main character
5. cast
6. antagonist
7. plot direction
8. tone / cấm kỵ

### Bước 3: Scaffold

```bash
./scripts/scaffold.sh <ten_truyen_snake_case>
```

### Bước 4: Initialize control plane

```bash
python -m scripts.control_plane init novels/<ten_truyen>
python -m scripts.control_plane seed novels/<ten_truyen> --from-chapter 1 --to-chapter 50
```

Nếu đã có artifact cũ:

```bash
python -m scripts.control_plane adopt novels/<ten_truyen> --from-chapter 1 --to-chapter 50
```

### Bước 5: Build retrieval layers

```bash
python -m scripts.rag_context index novels/<ten_truyen>
python -m scripts.vector_db index novels/<ten_truyen>
```

### Bước 6: Chạy preflight health check

```bash
python -m scripts.control_plane doctor novels/<ten_truyen>
```

Không nên chạy autonomous loop nếu `doctor` còn issue mức `error`.

### Bước 7: Release sign-off trước khi chốt build

Checklist ngắn nằm ở [RELEASE_SIGNOFF.md](/Users/meow/.openclaw/workspace/RELEASE_SIGNOFF.md).

Lệnh gộp:

```bash
./scripts/signoff.sh
```

Smoke command tích hợp:

```bash
python -m scripts.release_signoff novels/smoke_test
```

## 2. Vòng Chạy Chính

Pipeline hiện hành:

1. bootstrap
2. outline
3. write
4. review
5. sync

### Lấy task tiếp theo

```bash
python -m scripts.control_plane next novels/<ten_truyen>
```

Payload `next` gồm:

- task metadata
- input/output paths
- context query
- retrieval context
- dispatcher envelope:

Mặc định `next` là read-only. Nếu cần claim thủ công trong DB, dùng:

```bash
python -m scripts.control_plane next novels/<ten_truyen> --claim
```
  - `role_binding` (agent role, squad family, workspace của sub-agent)
  - `runtime.cwd`
  - `runtime.argv` (`python -m scripts.task_runner ...`)
  - `prompt` theo đúng contract trong `API.md`

Runner dùng trực tiếp `dispatcher.runtime.argv` để chạy đúng agent/squad tương ứng mà không cần tự dựng prompt lại.

### Ghi nhận kết quả

```bash
python -m scripts.control_plane record novels/<ten_truyen> \
  --task chapter.0001.review \
  --result done \
  --score 88
```

Các trạng thái chính:

- `done`
- `soft_fail`
- `hard_fail`
- `blocked`
- `skipped`

### Resume khi pipeline chết giữa chừng

```bash
python -m scripts.control_plane resume novels/<ten_truyen>
```

`resume` sẽ không mù quáng tin output trên disk. Nếu artifact tồn tại nhưng thiếu provenance, task có thể bị block.

## 3. Retrieval Flow

Khi `next` build `retrieval_context`, hệ thống sẽ ghép context từ:

- `rag_context`
- `vector_db`
- `agent_memory` nếu có episodic memory phù hợp

Ý nghĩa từng lớp:

- `rag_context`: bootstrap recall nhẹ, nhanh
- `vector_db`: semantic recall trên tài liệu dài
- `agent_memory`: episodic recall theo arc/session

## 4. Memory Flow

### Canonical memory

Source of truth:

- `novels/<ten>/memory/Memory.md`
- `novels/<ten>/database/*`

### Semantic memory

```bash
python -m scripts.vector_db search novels/<ten_truyen> "query"
python -m scripts.vector_db context novels/<ten_truyen> "query"
```

### Episodic memory

```bash
python -m scripts.agent_memory add novels/<ten_truyen> --session "arc_1_chapter_5" --messages "..."
python -m scripts.agent_memory search novels/<ten_truyen> --session "arc_1_chapter_6" --query "..."
python -m scripts.agent_memory clear-session novels/<ten_truyen> --session "arc_1"
```

Điểm quan trọng:

- session cấp chapter tự collapse về scope arc
- Phase B dùng `.mem0/qdrant`, không dùng chung `.vector_db`

## 5. Review và Quality Gates

Chapter không được xem là tích hợp xong cho đến khi:

- review pass
- sync phase pass
- memory/index refresh pass
- `doctor` không trả blocking issue

Ngưỡng review hiện hành:

- `>= 85`: pass
- `70-84`: soft-fail
- `< 70`: hard-fail

## 6. Sync Phase

Sync phase là chỗ hệ thống biến output của chapter thành runtime state bền.

Nó làm các việc sau:

1. kiểm tra review gate
2. refresh `rag_context`
3. refresh `vector_db`
4. commit facts vào `agent_memory`
5. chạy `doctor`
6. block pipeline nếu phát hiện lỗi hạ tầng nghiêm trọng

## 7. Circuit Breaker

Nguyên tắc hiện tại:

- max hard-fail liên tiếp theo chapter
- max soft-fail liên tiếp theo chapter
- max total attempts theo chapter

Khi breaker mở:

- `next` sẽ không cấp task mới
- operator phải xem `doctor`, `status`, `pipeline_status.json`, và logs để xử lý

## 8. Operator Checklist

Trước khi chạy dài hơi:

- [ ] `.env` đúng key
- [ ] `python -m scripts.llm_config show` đúng provider
- [ ] `ollama serve` đang chạy nếu dùng embedding mặc định
- [ ] `doctor` xanh
- [ ] `rag_context` đã có index
- [ ] `vector_db` đã có index
- [ ] control plane đã `init` + `seed`

Sau mỗi batch:

- [ ] xem `status`
- [ ] xem `doctor`
- [ ] xác nhận `reviews/` và `chapters/` khớp với task state

## 9. Smoke Test Protocol

Vertical slice tham chiếu là:

- `novels/smoke_test`

Smoke test chuẩn:

1. scaffold
2. fill DNA
3. init + seed control plane
4. index rag/vector
5. chạy write/review/sync ít nhất một vòng
6. xác nhận `doctor` xanh
7. xác nhận retrieval context không lỗi `agent_memory`

## 10. Khi Nào Cần Can Thiệp Tay

Operator hoặc human nên can thiệp khi:

- review hard-fail lặp lại
- `doctor` báo lỗi provider/index/memory
- task bị `blocked`
- artifact tồn tại nhưng chưa có provenance
- canon file bị conflict hoặc stale

## 11. Không Được Làm

- không auto-load `workspace/MEMORY.md`
- không coi file có sẵn trên disk là `done` nếu chưa adopt/provenance
- không cho multiple processes đụng cùng một local store nếu runtime path chưa tách riêng
- không bỏ qua `doctor` trước autonomous runs dài
