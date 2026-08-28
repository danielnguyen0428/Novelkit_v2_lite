# Meta Genre Depth Contract

Mục đích: Contract index cho Quality Auditor và Verifier. Định nghĩa verdict rules và trỏ sang source of truth cho thể loại Hệ Thống / Meta Genre.

## Source of Truth

| Lớp | Source File | Vai trò |
|-----|------------|---------|
| Consistency Rules | `system/Meta Genre/MetaGenre_consistency_rules.md` | System rules, MC↔System relationship |
| Style Guide | `system/Meta Genre/MetaGenre_style.md` | Văn phong, đối thoại với System, cấu trúc chương |
| Genre Operating | `system/Meta Genre/Genre Operating/MetaGenre_Operating_Guide.md` | System mechanics, quest logic, evolution |

## Meta Genre Positive Standard

Mỗi chương Meta Genre phải thể hiện ít nhất một cơ chế System thực sự tác động đến một lựa chọn, xung đột, nhận thức, cái giá phải trả, hoặc hậu quả.

Các cơ chế được chấp nhận:
- System nhiệm vụ / điểm / skill có rules rõ và giới hạn
- Tương tác MC↔System (hợp tác / đối lập / ký sinh / mentor)
- Thế giới base ép System phải tuân theo (tu chân / hiện đại / hậu tận thế)
- Đối thủ cũng có System / dị năng / tổ chức đối lập
- Cái giá khi dùng System (thời gian, máu, linh hồn, danh tiếng)

## Texture Tier System

| Tier | Yêu cầu | Ý nghĩa |
|------|----------|---------|
| **Tier 1** (bắt buộc) | System vận hành trong scene với rules | quest trigger có điều kiện, skill có cooldown, evolution có requirement |
| **Tier 2** (bắt buộc) | Áp lực sinh tử/tâm lý/thế giới base | nguy hiểm thật từ thế giới base, tự vấn bản ngã, áp lực thời gian |
| **Tier 3** (hỗ trợ) | Items / rewards / stats | KHÔNG thay thế Tier 1/2 |

## Scene Types

Outline phải gắn tag cho mỗi cảnh chính:
- `system_interaction`: MC tương tác với System (quest, skill, panel)
- `evolution`: level up, rank up, class change, awakening
- `conflict`: chiến đấu với đối thủ có/không System
- `investigation`: tìm hiểu luật System, tìm kiếm bí mật
- `world_base`: tương tác với thế giới base (không qua System)
- `transition`: di chuyển, nghỉ ngơi, chuẩn bị

Ngay cả `transition` cũng phải có nhận thức về trạng thái System (cooldown, quest timer).

## System / Evolution Progression Contract

- Macro progression: thay đổi lớn về level/rank/class/evolution tier
- Meso progression: hoàn thành quest chain lớn, unlock feature System mới
- Micro progression: tăng stat nhỏ, nhận skill lẻ, thu thập vật phẩm

Cadence tham chiếu: ~10 chương có ~6 micro, ~3 meso, ~1 notable evolution/rank shift.

Evolution lớn yêu cầu:
- Ít nhất 2 loại fuel: xp tích lũy, items điều kiện, quest chain hoàn thành, trigger event
- Requirement rõ (System chỉ rõ cần gì) hoặc bottleneck ẩn phải giải mã
- Foreshadow 3-1-1 cho rank shift lớn
- Quá trình trên trang: thử nghiệm, đạt điều kiện, kích hoạt, aftermath
- Aftermath: năng lực mới tạo hệ quả (đối thủ mạnh lên, System yêu cầu nhiệm vụ khó hơn, cái giá mới)

## System Rules Rule

System KHÔNG được vạn năng. Mọi feature phải có:
- Trigger / precondition rõ
- Cooldown / giới hạn sử dụng
- Cost (tiền System, điểm, thời gian, máu, tuổi thọ)
- Failure mode (nếu dùng sai, quá lạm dụng)
- Interaction với thế giới base (System có thể bị phong tỏa, xung đột luật vũ trụ)

Không viết: "System cho MC vô địch." Phải viết: System cho MC skill A với cost B, cooldown C, trong điều kiện D; nếu dùng ngoài D, skill fail.

## Operating Systems

Meta Genre worldbuilding không phải phông. Khi chương dùng:
- **System core**: interface, ai tạo ra, mục tiêu của System, ai quan sát
- **Quest system**: nguồn phát, reward logic, fail consequence, time limit
- **Skill system**: học, nâng cấp, evolve, conflict giữa skills
- **Evolution path**: branching, locked paths, cost, prerequisite
- **Shop / inventory**: currency, rarity, availability, hidden items
- **Thế giới base**: luật vật lý + xã hội + thế lực — System phải tuân theo
- **Đối thủ có System**: đa System coexist, cách giao tiếp, cạnh tranh

Hệ thống nào xuất hiện phải có luật vận hành, ai kiểm soát, rủi ro khi đối đầu.

## Review Verdict Rules

| Verdict | Điều kiện |
|---------|-----------|
| `PASS` | Đủ Tier 1 + Tier 2, system progression hợp lý, world base rules rõ |
| `PASS_WITH_FLAGS` | 1 lớp depth yếu nhưng phục hồi được |
| `SOFT_FAIL_STYLE` | 2 lớp texture/depth yếu |
| `HARD_FAIL_DEPTH` | Cảnh không có System vận hành có rule, HOẶC System vạn năng không giới hạn, HOẶC evolution đột ngột thiếu fuel/foreshadow, HOẶC world base bị System lờ đi |

## MC↔System Relationship Rule

PROJECT_DNA.md khai báo relationship type:
- `hợp tác`: System là đồng minh, chia sẻ mục tiêu
- `đối lập`: System ép MC, có thể phản bội
- `ký sinh`: System cần MC sống, hút tài nguyên
- `mentor`: System dạy dỗ, có mục đích riêng

Mỗi chương phải thể hiện relationship này một lần — KHÔNG để System chỉ là panel thông báo. System phải có "tiếng nói" hoặc "hành vi" riêng trong câu chuyện.

## Không Conflict Rule

- Canon riêng truyện luôn thắng guide chung.
- System loại nào do `PROJECT_DNA.md` quyết định (tông chủ / phản diện / thợ săn / vô sỉ / thao túng).
