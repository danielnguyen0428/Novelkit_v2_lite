# Pipeline Log — [Tên Tác Phẩm]

> Ghi chép mọi agent call, kết quả, escalations.
> Dùng để debug, optimize, và track progress.

## Log Entry Format

Mỗi entry PHẢI theo format:

```
### [YYYY-MM-DD HH:MM] — Phase [X] — [AGENT_NAME]: [COMMAND]

| Field | Value |
|---|---|
| Chapter | Ch.[X] |
| Attempt | [N]/5 |
| Result | ✅ PASS / ⚠️ SOFT-FAIL / ❌ HARD-FAIL / 📋 COMPLETE |
| Score | [XX]/100 (nếu review) |
| Files created | [list] |
| Files modified | [list] |
| Flags | [CANON_CONFLICT / DESIGN_CONFLICT / OUTLINE_UNCLEAR / none] |
| Duration | ~[X]s |

**Notes:** [Ghi chú ngắn — lỗi chính, điểm sáng, quyết định]

---
```

## Escalation Log Format

```
### 🚨 ESCALATION — [YYYY-MM-DD HH:MM] — Ch.[X]

| Field | Value |
|---|---|
| Trigger | Circuit breaker: [hard_fail×2 / soft_fail×3 / total×5] |
| Best score | [XX]/100 |
| Recurring errors | [top 2 lỗi lặp] |
| Human decision | [Option A: sửa outline / B: human sửa / C: skip / D: force pass] |
| Resolution | [mô tả ngắn] |
| Pipeline resumed | [YYYY-MM-DD HH:MM] |

---
```

## Conflict Log Format

```
### ⚖️ CONFLICT — [YYYY-MM-DD] — Ch.[X]

| Field | Value |
|---|---|
| Type | [CANON_CONFLICT / DESIGN_CONFLICT] |
| Between | [Agent/File A] vs [Agent/File B] |
| Description | [mô tả mâu thuẫn] |
| Canonical owner | [agent name] |
| Resolution | [ai sửa, sửa gì] |

---
```

## Session Log

### [Date — bắt đầu ghi từ đây]

---
