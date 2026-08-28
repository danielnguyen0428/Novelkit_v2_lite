# CONTRACTS.md — Agent Contracts & Canonical Authority

**Author:** Dũng Nguyễn  
**Version:** 2.1.06 Hybrid-Genre  
**Updated:** 2026-05-16

Tài liệu này định nghĩa:

- canonical owner của từng loại dữ liệu
- quy tắc phân xử khi mâu thuẫn
- contract input/output của từng role
- quyền sở hữu các artifact runtime sinh ra bởi control plane và memory layers

Mục tiêu là giữ cho hệ thống nhiều lớp nhớ vẫn chỉ có **một nguồn sự thật** cho mỗi loại dữ liệu.

## 1. Canonical Authority

Mỗi loại dữ liệu có MỘT canonical owner. Khi có mâu thuẫn:

- owner wins
- index/runtime stores không được override canonical files
- `SOUL.md` không được override shared canon

### 1.1 Canonical Data Owners

| Dữ liệu | Canonical Owner | Ghi bởi | Đọc bởi |
|---|---|---|---|
| `PROJECT_DNA.md` | **Human** | Human + Novel Agents — Orchestrator | Tất cả |
| `database/characters/*` | **Character Architect** | Character Architect | Tất cả |
| `database/worldbuilding/*` | **World Builder** | World Builder | Tất cả |
| `database/systems/*` | **World Builder** | World Builder | Tất cả |
| `database/plot_threads/*` | **Plot Weaver** | Plot Weaver | Tất cả |
| `database/timeline/*` | **Novel Agents — Orchestrator** | Orchestrator | Tất cả |
| `outlines/*` | **Plot Weaver** | Plot Weaver | Prose Writer, Quality Auditor, Orchestrator |
| `chapters/*` | **Prose Writer** | Prose Writer + Quality Auditor (soft-fix only) | Quality Auditor, Orchestrator |
| `reviews/*` | **Quality Auditor** | Quality Auditor | Orchestrator |
| `style_vault/*` | **Quality Auditor** | Quality Auditor | Prose Writer (qua Orchestrator) |
| `GOAL_TRACKER.md` | **Novel Agents — Orchestrator** | Orchestrator | Plot Weaver, Quality Auditor |
| `PLAN.md` | **Novel Agents — Orchestrator** | Orchestrator | Tất cả |
| `memory/Memory.md` (per novel) | **Novel Agents — Orchestrator** | Orchestrator | Orchestrator + retrieval layers |
| `memory/archive/*` | **Control Plane Runtime** | Memory rotation | Orchestrator + audit |
| `reviews/style_coherence/*` | **Control Plane Runtime** | Style audit | Human + Quality Auditor |
| `system/[genre]/*` | **Novel Agents — Orchestrator** | Orchestrator | Tất cả |
| `system/StoryDepth/*` | **Control Plane Runtime** | Orchestrator + Runtime | Tất cả |
| `workspace/MEMORY.md` | **Novel Agents — Orchestrator** | Orchestrator | Orchestrator (explicit retrieval only) |
| `logs/pipeline_log.md` | **Novel Agents — Orchestrator** | Orchestrator | Orchestrator + operator |
| `published/*` | **Control Plane Runtime** | `publish` command | Human + downstream export |

### 1.2 Runtime-Generated Artifacts

Các artifact dưới đây **không phải canon**. Chúng là runtime/index state được sinh từ canonical files:

| Dữ liệu | Runtime Owner | Sinh bởi | Vai trò |
|---|---|---|---|
| `.controlplane.sqlite3` | **Control Plane Runtime** | `scripts/control_plane.py` | Task DAG, retry, breaker, provenance |
| `logs/pipeline_status.json` | **Control Plane Runtime** | `scripts/control_plane.py` | Snapshot vận hành hiện tại |
| `.rag/*` | **RAG Runtime** | `scripts/rag_context.py` | Bootstrap retrieval index |
| `.vector_db/*` | **Vector Runtime** | `scripts/vector_db.py` | Semantic document index |
| `.mem0/history.db` | **Agent Memory Runtime** | `scripts/agent_memory.py` | Episodic memory history |
| `.mem0/qdrant/*` | **Agent Memory Runtime** | `scripts/agent_memory.py` | Episodic vector store |

Quy tắc:

1. Runtime artifacts là **derivative state**, không phải source of truth.
2. Khi derivative state conflict với canonical files, canonical files thắng.
3. Runtime artifacts có thể bị rebuild hoặc refresh mà không làm đổi canon.

### 1.3 Shared Canon vs Prompt Specialization

`SOUL.md` của từng agent là lớp prompt specialization để thực thi tốt hơn nhiệm vụ, không phải nguồn canon.

Khi `SOUL.md` xung đột với `system/[genre]/*`:

- `system/[genre]/*` thắng
- nếu xung đột làm task không chạy được, Orchestrator phải resolve ở canonical owner hoặc escalate

Tất cả 16 genre packs (bao gồm 10 packs mới: Rules Horror, Cthulhu, War Espionage, Apocalypse, Many Children, Substitute, Short Form, Dark Theme, eSports, Streaming) tuân theo cùng authority rules: `system/[genre]/*` thắng `SOUL.md`, và `PROJECT_DNA.md` thắng shared canon khi có xung đột.

### 1.4 StoryDepth Cross-Genre Contract

`system/StoryDepth/CREATE_NOVEL_FIELD_EXECUTION.md` là guide thi triển dùng cho
mọi genre. Nó không thay thế canon thể loại và không thắng `PROJECT_DNA.md`;
vai trò của nó là buộc các field CREATE_NOVEL/PROJECT_DNA như Core Wound,
World Pressure, Scene Vitality, motif angle và reader loop phải thành hành động,
áp lực, lựa chọn và hậu quả trong artifact.

Canonical owner thực tế là **Control Plane Runtime** vì file này được resolve
qua `SHARED_WORLDBUILDING_GUIDE_TOKEN` trong `scripts/control_plane.py`.

## 2. Arbitration Protocol

### Khi nào conflict xảy ra?

- Plot Weaver dùng location chưa tồn tại trong worldbuilding
- Outline đẩy nhân vật hành động out-of-character
- Prose Writer viết power level vượt hệ thống
- Quality Auditor phát hiện chapter conflict với timeline hoặc rules
- Retrieval/index state trả về fact cũ khác với canonical files

### Quy trình phân xử

```text
BƯỚC 1: Quality Auditor hoặc Orchestrator phát hiện conflict
         -> gắn type + chỉ rõ canonical owner

BƯỚC 2: Orchestrator phân loại:

  (A) Agent output vi phạm canon hiện có
      -> trả về agent gốc sửa theo canonical files

  (B) Outline conflict với world/character rules
      -> gửi canonical data cho Plot Weaver sửa outline

  (C) Canon files tự mâu thuẫn nhau
      -> gửi cho canonical owner sửa

  (D) Design-level conflict
      -> escalate to Human

  (E) Runtime/index conflict
      -> rebuild / refresh runtime state
      -> không sửa canon chỉ vì runtime trả sai

BƯỚC 3: Sau khi sửa
         -> Orchestrator verify
         -> ghi conflict log nếu cần
```

### Conflict Log Format

```markdown
| Date | Chapter | Type | Description | Resolution | Owner |
|---|---|---|---|---|---|
| YYYY-MM-DD | Ch.X | CANON_CONFLICT | [mô tả] | [cách xử lý] | [ai sửa] |
```

## 3. Agent Contracts

### Character Architect

| Field | Spec |
|---|---|
| **Trigger** | `CREATE_CHARACTERS` / `UPDATE_CHARACTERS` |
| **Required Input** | `PROJECT_DNA.md` (create) / chapter + review notes (update) |
| **Output Path** | `database/characters/[name].md` |
| **Output Format** | Theo source of truth `templates/database/xianxia_character_template.md` |
| **Validation** | Want ≠ Need; ≥1 flaw; ≥3 relationships; voice defined |
| **Side Effects** | Update relationship map nếu có |
| **Error Signal** | `❌ CONFLICT: [description]` nếu DNA hoặc chapter delta mâu thuẫn canon hiện tại |

### World Builder

| Field | Spec |
|---|---|
| **Trigger** | `BUILD_WORLD` / `EXPAND_WORLD` |
| **Required Input** | `PROJECT_DNA.md` + `system/[genre]/` shared canon + `database/worldbuilding/_seed_brief.md` (nếu có, brief từ Story Studio) |
| **Output Path** | `database/worldbuilding/WorldOverview.md` (BẮT BUỘC, index canonical) + `database/worldbuilding/*.md` + `database/systems/*.md` |
| **Validation** | `WorldOverview.md` PHẢI tồn tại và link sang các file chi tiết; system phải có giới hạn; geography có distances; history có conflicts |
| **Side Effects** | Tạo thêm thư mục con khi cần |
| **Error Signal** | `❌ CONFLICT: [description]` nếu DNA yêu cầu vi phạm shared canon |

Với Xianxia, World Builder phải dùng thêm shared canon sublayer `system/Xianxia/Worldbuilding guide/` qua guide đã resolve từ `worldbuilding_guide` hoặc fallback `style_model`. Guide này là tài nguyên đọc, không phải canon riêng của novel; output lâu dài vẫn phải ghi vào `database/worldbuilding/` và `database/systems/`.

### Plot Weaver

| Field | Spec |
|---|---|
| **Trigger** | `OUTLINE_CHAPTERS` / `REVISE_OUTLINE` |
| **Required Input** | Canon DB đã curate + `GOAL_TRACKER.md` + `database/plot_threads/*` + rules liên quan |
| **Pre-check** | Phải đọc goals, plot threads, canon constraints trước khi outline |
| **Output Path** | `outlines/arc_X/chapter_XXX_outline.md` |
| **Validation** | Outline không được vi phạm character/world rules; seeds phải có lifecycle rõ |
| **Side Effects** | Update trackers thuộc `database/plot_threads/*` |
| **Error Signal** | `⚠️ DESIGN_CONFLICT: [description]` nếu goals mâu thuẫn canon |

### Prose Writer

| Field | Spec |
|---|---|
| **Trigger** | `WRITE_CHAPTER` / `REWRITE_CHAPTER` |
| **Required Input** | Outline + style guide + relevant canon subset + retrieval context |
| **Output Path** | `chapters/chapter_XXX.md` |
| **Output Format** | Theo layout chapter hiện hành của project |
| **Validation** | Hook opening; coherent scenes; cliffhanger hoặc close đúng mục đích chương |
| **Error Signal** | `⚠️ OUTLINE_UNCLEAR: [description]` nếu outline thiếu thông tin bắt buộc |

### Quality Auditor

| Field | Spec |
|---|---|
| **Trigger** | `REVIEW_CHAPTER` |
| **Required Input** | Chapter + relevant canon DB + outline + `GOAL_TRACKER.md` + `STYLE_GUIDE.md` + shared canon trong `system/[genre]/` |
| **Output Path** | `reviews/chapter_XXX_review.md` |
| **Output Format** | Rubric + verdict + findings + highlights + style-vault candidates |
| **Decisions** | `>=85 PASS` / `70-84 SOFT-FAIL` / `<70 HARD-FAIL` |
| **Registry Check** | Phải đối chiếu timeline/location/event registry nếu có |
| **Style Adherence** | Được dùng `SOUL.md` để specialization thêm, không được override shared canon |
| **Early Score Lift** | Chương 1-5 giữ nguyên ngưỡng; reviewer không hạ chuẩn nhưng chấm theo bằng chứng mở truyện: scene promise, choice có giá, micro-payoff, world/canon anchors |
| **Harem Voice & Agency** | Nếu truyện khai báo harem/đạo lữ, reviewer phải kiểm voice fingerprint, agency, philosophical question, relationship dynamic và flag `HAREM_VOICE_COLLAPSE` khi các giọng bị nhập làm một |
| **Side Effects** | Update `style_vault/` nếu có đoạn đủ chuẩn; soft-fix chapter nếu policy cho phép |
| **Error Signal** | `🚨 CANON_CONFLICT: [description]` nếu phát hiện canon mismatch |

### Novel Agents — Orchestrator

| Field | Spec |
|---|---|
| **Trigger** | Điều phối tổng thể |
| **Required Input** | Toàn bộ runtime state + canonical files cần thiết |
| **Owns** | `PLAN.md`, `GOAL_TRACKER.md`, `memory/Memory.md`, `logs/pipeline_log.md`, shared canon maintenance |
| **Runtime Duties** | seed, adopt, next, record, resume, doctor, sync gating |
| **Authority** | Resolve conflict routing; không tự rewrite canonical files của owner khác nếu chưa qua protocol |

## 4. Sync & Memory Contracts

### Sync Phase Contract

Task `sync` chỉ được xem là thành công khi:

1. review gate pass
2. `rag_context` refresh thành công
3. `vector_db` refresh thành công
4. `agent_memory` commit thành công
5. `doctor` không trả blocking issue

### Provenance Contract

Artifact tồn tại trên disk **không đồng nghĩa** với `done`.

Muốn một output được xem là trusted:

- phải có provenance fingerprint trong control plane
- hoặc phải được `adopt` explicit

### Memory Contract

- `memory/Memory.md` là canon memory theo novel
- `.vector_db/*` là semantic derivative
- `.mem0/*` là episodic derivative
- `workspace/MEMORY.md` là curated workspace memory và không được auto-load mặc định
- `Memory.md` chỉ giữ active/current/unresolved state. Khi quá dài, control
  plane rotate resolved state sang `memory/archive/` trước khi rebuild RAG/vector.
- Style coherence audit định kỳ ghi `reviews/style_coherence/*` để theo dõi drift
  so với baseline chương 1-3; report này không tự override review score.

### Provider Failover Contract

- Active provider vẫn nằm trong `llm_config.json.llm`.
- Python-side LLM calls được phép dùng `llm.fallbacks[]` hoặc `LLM_FALLBACKS`
  theo thứ tự primary → fallback.
- Khi đổi provider/model cho creative lane, phải xem style audit gần nhất trước
  khi chạy dài để tránh drift do khác model.

### Publish Contract

`publish` tạo artifact xuất bản nội bộ, không phải platform export:

- `published/chapter_NNN.md` là bản markdown đã qua review gate.
- `published/chapter_NNN.meta.json` ghi score, outcome, word count, checksum.
- `published/manifest.json` là index chương đã xuất bản.
- Nếu republish, bản cũ được copy vào `published/backups/` trước khi ghi đè.

## 5. Runtime Tokens

Một số input path trong task DAG dùng **token** thay vì literal path. Tokens
được resolve bởi `scripts/cp_genre.resolve_task_paths()` ngay trước khi
dispatcher build envelope. Reviewer audit task spec phải hiểu các token này
để không nhầm chúng là path lỗi.

| Token | Resolver target | Định nghĩa | Resolve tại |
|---|---|---|---|
| `@shared_canon` | `system/<primary_genre>/` | Pack canon thể loại chính từ `PROJECT_DNA.md::genre` | `cp_genre.py::resolve_task_paths` |
| `@shared_canon_secondary` | `system/<secondary_genre>/` | Pack canon thứ hai cho hybrid (vd `genre=hybrid`, `genre_secondary=xianxia`) | `cp_genre.py::resolve_task_paths` |
| `@worldbuilding_guide` | List file `*_Worldbuilding_Complete.md` + `system/StoryDepth/CREATE_NOVEL_FIELD_EXECUTION.md` | Author Style + StoryDepth cross-genre guide | `cp_genre.py::resolve_task_paths` qua `XIANXIA_WORLDBUILDING_GUIDES`, `STORY_DEPTH_GUIDES`, `GENRE_OPERATING_GUIDES` |
| `[genre]` (placeholder) | Replace `[genre]` literal trong path bằng primary genre | Vd `system/[genre]/Depth/` → `system/xianxia/Depth/` | `cp_genre.py::resolve_task_paths` |

Constants nguồn: `scripts/cp_constants.py::SHARED_CANON_TOKEN`,
`SHARED_CANON_SECONDARY_TOKEN`, `SHARED_WORLDBUILDING_GUIDE_TOKEN`,
`GENRE_PLACEHOLDER`. Các name này được export qua `__all__`; thêm token mới
phải bổ sung cả 3 chỗ:

1. constant trong `cp_constants.py` + entry trong `__all__`
2. nhánh resolver trong `cp_genre.resolve_task_paths`
3. dòng mới trong bảng phía trên

Quy tắc:
- Token không được xuất hiện trong **output_paths** — tasks phải ghi vào path
  thật (`database/characters/`, `chapters/chapter_NNN.md`).
- Token chỉ là input reference. Sau resolve, dispatcher có thể inject thành
  inline excerpt hoặc giữ làm path để agent đọc khi cần.
- Nếu resolver fail (vd `genre_secondary` không có), token được drop quietly
  — không raise — để tasks single-genre vẫn chạy.

## 6. Nguyên Tắc Cuối Cùng

1. Canon files thắng runtime stores.
2. Shared canon thắng prompt specialization.
3. Owner thắng non-owner.
4. Runtime state có thể rebuild; canon thì phải được sửa đúng owner.
5. Nếu conflict không giải được bằng authority hiện có, escalate to Human.
