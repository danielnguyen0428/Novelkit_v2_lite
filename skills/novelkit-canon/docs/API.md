# API.md — Giao Thức Giao Tiếp Novel Agents (Orchestrator ↔ Specialist)

**Author:** Dũng Nguyễn  
**Project:** NovelKit  
**Version:** 2.1.06

> Ghi chú thuật ngữ:  
> • **Novel Agents — Orchestrator** (runtime ID: `Lãng Khách`) là tổng quản pipeline.  
> • **Novel Agents — Specialist** là 5 vai chuyên trách (Character Architect, World Builder, Plot Weaver, Prose Writer, Quality Auditor).  
> NovelKit giữ nhãn `Lãng Khách` trong control plane SQLite + dispatcher để không phá lịch sử task; trong các code-block prompt bên dưới, ký hiệu `LỆNH TỪ LÃNG KHÁCH` là format runtime đang chạy thực tế và phải giữ nguyên.

## Tổng Quan

Mọi giao tiếp trong hệ thống đều đi qua Orchestrator (Hub-and-Spoke).
Specialist KHÔNG BAO GIỜ giao tiếp trực tiếp với nhau.

```
Specialist A ←→ Orchestrator ←→ Specialist B
                (NEVER: A ←→ B)
```

## Dispatch Protocol — Orchestrator Gửi Lệnh Cho Specialist

Khi Orchestrator triệu hồi một Specialist, message PHẢI có format dưới đây. Tiêu đề `LỆNH TỪ LÃNG KHÁCH` là literal format đang được dispatcher emit; KHÔNG đổi để tránh phá prompt parser.

```markdown
## 📜 LỆNH TỪ LÃNG KHÁCH

**Giai đoạn:** [Phase 1/2/3/4]
**Nhiệm vụ:** [Mô tả cụ thể]
**Novel:** [Tên tác phẩm]
**Tham chiếu:** [Danh sách file cần đọc — ĐẦY ĐỦ đường dẫn]

### Context đã chuẩn bị:
[Orchestrator paste trực tiếp context cần thiết — KHÔNG yêu cầu agent tự tìm]

### Yêu cầu output:
- Format: [mô tả]
- Ghi vào: [đường dẫn file cụ thể]
- Checklist: [list những gì PHẢI có trong output]

### Ràng buộc:
- [Luật cần tuân thủ]
- [File cấm đọc/ghi]
```

## Response Protocol — Specialist Trả Lời Orchestrator

```markdown
## 📋 BÁO CÁO TỪ [TÊN SPECIALIST]

**Nhiệm vụ:** [echo lại nhiệm vụ]
**Trạng thái:** ✅ Hoàn thành / ⚠️ Hoàn thành có vấn đề / ❌ Thất bại

### Output:
- File đã tạo/sửa: [danh sách đường dẫn]

### Flags (nếu có):
- 🚨 [Vấn đề cần Orchestrator xử lý]
- 💡 [Gợi ý cho giai đoạn tiếp theo]
- ❓ [Câu hỏi cần human quyết định]
- ❌ CONFLICT: [data mâu thuẫn với canonical source — xem CONTRACTS.md]
- ⚠️ DESIGN_CONFLICT: [outline/plan conflict với world rules]
- ⚠️ OUTLINE_UNCLEAR: [outline thiếu thông tin cần thiết để viết]
- 🚨 CANON_CONFLICT: [DB entries tự mâu thuẫn — cần canonical owner sửa]

### Tóm tắt:
[2-3 câu mô tả đã làm gì]
```

## Pipeline Commands — Lệnh Cụ Thể Cho Từng Phase

### Phase 1: Khai Thiên

#### → [Character Architect]: Tạo nhân vật
```
LỆNH: CREATE_CHARACTERS
Input: PROJECT_DNA.md
Output: database/characters/[name].md (mỗi nhân vật 1 file)
Thêm: database/characters/relationship_map.md
Checklist:
  □ Mỗi nhân vật có Want ≠ Need
  □ Mỗi nhân vật có ≥1 flaw thật sự
  □ Mỗi nhân vật có ≥3 relationships
  □ Character Arc planned
  □ Voice/speech pattern defined
```

#### → [Character Architect]: Cập nhật nhân vật (sau mỗi chương)
```
LỆNH: UPDATE_CHARACTERS
Input: chapter_XXX.md + review notes
Update: database/characters/[affected].md → phần "Trạng thái Hiện Tại"
Checklist:
  □ Location updated
  □ Injuries/conditions updated
  □ Items/inventory updated
  □ Knowledge updated (biết gì mới)
  □ Relationship changes logged
  □ Emotional state updated
```

#### → [World Builder]: Xây thế giới
```
LỆNH: BUILD_WORLD
Input: PROJECT_DNA.md + system/[genre]/ consistency rules (shared canon)
Output: database/worldbuilding/*.md + database/systems/*.md
Checklist:
  □ Geography with distances
  □ History with conflicts
  □ Political structure with power dynamics
  □ Economy basics (who produces what)
  □ Core system with CLEAR LIMITS
  □ Factions with motivations
```
Ghi chú canon:
- `system/[genre]/*` là shared canon dùng chung cho toàn vũ trụ.
- `SOUL.md` của từng tổ đội chỉ là prompt specialization để thi hành tốt hơn.
- Nếu `SOUL.md` xung đột với `system/[genre]/*`, canon trong `system/` thắng.

### Phase 2: Bố Cục

#### → [Plot Weaver]: Outline batch
```
LỆNH: OUTLINE_CHAPTERS
Input: 
  - DATABASE đầy đủ (characters, world, systems)
  - system/[genre]/*_consistency_rules.md
  - GOAL_TRACKER.md (BẮT BUỘC)
  - database/plot_threads/* (BẮT BUỘC)
  - Previous outlines + chapters (nếu không phải batch đầu)
Params:
  - chapters: [X to Y] (thường 3-5 chương/batch)
  - arc: [X]
Output: 
  - outlines/arc_X/chapter_XXX_outline.md
  - UPDATE: database/plot_threads/seeds_tracker.md
  - UPDATE: database/plot_threads/threads_master.md
Checklist:
  □ Three-Act Eight-Sequence compliance
  □ ≥2 plot threads advanced per chapter
  □ Seeds planted + harvested as scheduled
  □ Character Arc beats included
  □ Emotional trajectory per chapter
  □ No outline violates consistency_rules
```

### Phase 3: Hạ Bút

#### → [Prose Writer]: Viết chương
```
LỆNH: WRITE_CHAPTER
Input (CURATED BY ORCHESTRATOR):
  - outlines/arc_X/chapter_XXX_outline.md
  - system/[genre]/*_style.md
  - 2-3 random entries from style_vault/ (Orchestrator chọn)
  - Relevant character profiles (SUBSET, not all)
  - Relevant world/system info (SUBSET)
  - 2-3 chương gần nhất (continuity)
Output: chapters/chapter_XXX.md
Checklist:
  □ 2500+ chữ
  □ Follows outline beats
  □ Follows style guide
  □ Hook opening (3 câu đầu phải cuốn)
  □ Cliffhanger/punch ending
  □ Metadata section complete
  □ Show-don't-tell compliant
  □ No infodump >100 chữ liên tục
```

### Phase 4: Đạo Kiếp

#### → [Quality Auditor]: Review
```
LỆNH: REVIEW_CHAPTER
Input:
  - chapters/chapter_XXX.md
  - DATABASE đầy đủ (đối chiếu)
  - outlines/arc_X/chapter_XXX_outline.md (đúng plan?)
  - system/[genre]/*_consistency_rules.md
  - GOAL_TRACKER.md
Output:
  - reviews/chapter_XXX_review.md
  - UPDATE: style_vault/ (nếu có đoạn hay)
Decision:
  - ≥85 → PASS (report to Orchestrator)
  - 70-84 → SOFT-FAIL (tự sửa chapter, report)
  - <70 → HARD-FAIL (report với chi tiết lỗi)
```

### Post-Chapter: DB Update

#### → Orchestrator orchestrates:
```
LỆNH SEQUENCE (sau mỗi PASS):
1. [Character Architect]: UPDATE_CHARACTERS
2. Orchestrator: UPDATE GOAL_TRACKER.md
3. Orchestrator: UPDATE PLAN.md
4. Orchestrator: UPDATE memory/Memory.md
5. Orchestrator: UPDATE master_timeline.md
6. Orchestrator: LOG to logs/pipeline_log.md
7. Orchestrator: CHECK overdue alerts
```

## Error Handling

### HARD-FAIL Loop (with Circuit Breaker)
```
Attempt 1: [Prose Writer] writes → [Quality Auditor] reviews → HARD-FAIL
  → Orchestrator sends review notes to [Prose Writer]
  → [Prose Writer] rewrites (with review feedback)
  → circuit_breaker.hard_fail_count += 1
Attempt 2: → [Quality Auditor] reviews again
  → If HARD-FAIL again: circuit_breaker.hard_fail_count = 2 → BREAKER TRIGGERED
  → ESCALATE to Orchestrator → human
  → Human decides: retry / modify outline / skip
  → Reset circuit_breaker for next chapter

MAX ATTEMPTS PER CHAPTER:
  hard_fail:   2 (absolute)
  soft_fail:   3 (consecutive)
  total:       5 (all attempts combined)
  Exceeded → ESCALATE regardless
```

### SOFT-FAIL Accumulation
```
If 3 consecutive SOFT-FAILs on same chapter:
  → Pattern indicates deeper issue than surface fixes
  → ESCALATE — likely outline or context problem
  → Orchestrator may re-dispatch [Plot Weaver] for outline revision
```

### Outline Conflict
```
If [Quality Auditor] finds outline itself is flawed:
  → Report to Orchestrator with 🚨 CANON_CONFLICT flag
  → Orchestrator checks CONTRACTS.md for canonical authority
  → Sends to [Plot Weaver] for outline revision (max 2 revisions)
  → Pipeline restarts from Phase 3 with revised outline
  → If 2 outline revisions fail → ESCALATE to human
```

### Canonical Conflict Resolution
```
[Quality Auditor] flags CANON_CONFLICT in review:
  → Orchestrator reads CONTRACTS.md canonical authority table
  → Identifies: which data is canonical? who owns it?
  → Routes fix to canonical owner
  → After fix: re-run affected pipeline step
  → If design-level (rules need changing): ESCALATE to human
  → Log in pipeline_status.json → conflict_log[]
```

## Token Optimization

### Context Window Management
Orchestrator PHẢI curate context cho mỗi agent call:
- **[Character Architect]:** Only relevant characters + DNA
- **[World Builder]:** Only world/system files + DNA  
- **[Plot Weaver]:** Full DB access BUT summarized (Orchestrator tóm tắt files dài)
- **[Prose Writer]:** SUBSET only — Orchestrator picks relevant excerpts
- **[Quality Auditor]:** Full access BUT prioritize: chapter + outline + relevant DB entries

### Compression Rules
- Character files >500 words → Orchestrator summarizes to 200 words for [Prose Writer]
- World files → Only sections relevant to current chapter location
- Previous chapters → Only last 2-3, summarized if >3000 words each
