# Time Travel Depth Contract

Mục đích: Contract index cho Quality Auditor và Verifier. Định nghĩa verdict rules và trỏ sang source of truth cho từng lớp depth của thể loại Xuyên Không / Lịch Sử.

## Source of Truth

| Lớp | Source File | Vai trò |
|-----|------------|---------|
| Consistency Rules | `system/Time Travel/TimeTravel_consistency_rules.md` | Cơ chế xuyên không, paradox, lịch sử |
| Style Guide | `system/Time Travel/TimeTravel_style.md` | Văn phong, đối thoại, cấu trúc chương |
| Genre Operating | `system/Time Travel/Genre Operating/TimeTravel_Operating_Guide.md` | Quan trường, kinh tế, quân sự thời đại đến |

## Time Travel Positive Standard

Mỗi chương Time Travel phải thể hiện ít nhất một cơ chế lịch sử/kiến thức hiện đại/quan trường thực sự tác động đến một lựa chọn, xung đột, nhận thức, cái giá phải trả, hoặc hậu quả.

Các cơ chế được chấp nhận:
- Kiến thức hiện đại áp dụng vào bối cảnh cổ (nông nghiệp, quân sự, y thuật, thương mại)
- Luật pháp / quan trường thời đại đến ép lựa chọn
- Thân phận gốc (người bị chiếm thân) để lại nợ nần, ân oán, danh tiếng
- Paradox / nhân quả thay đổi lịch sử có hậu quả
- Chênh lệch quyền lực chính trị / quân sự ép hành động

## Texture Tier System

| Tier | Yêu cầu | Ý nghĩa |
|------|----------|---------|
| **Tier 1** (bắt buộc) | Cơ chế lịch sử/quan trường/kiến thức hiện đại vận hành | MC dùng kiến thức hiện đại có giá, quan trường áp lực, luật pháp đe dọa, thân phận cũ trỗi dậy |
| **Tier 2** (bắt buộc) | Áp lực chính trị/xã hội/tâm lý hai thế giới | tự vấn bản ngã, nhớ nhà, rủi ro lộ thân phận, trách nhiệm không muốn |
| **Tier 3** (hỗ trợ) | Vật phẩm / công nghệ cổ / thư tịch | KHÔNG thay thế Tier 1/2 |

## Scene Types

Outline phải gắn tag cho mỗi cảnh chính:
- `knowledge_leverage`: MC dùng kiến thức hiện đại giải quyết vấn đề cổ
- `court_politics`: quan trường, triều đình, phe phái
- `identity_crisis`: thân phận gốc vs linh hồn hiện đại
- `investigation`: điều tra mưu đồ, tìm hiểu lịch sử, phân tích đối thủ
- `military_campaign`: chiến tranh, chiến dịch, chiến thuật
- `transition`: di chuyển, nghỉ ngơi, xử lý việc nhà

Ngay cả `transition` cũng cần nhận thức về 2 thế giới (hiện đại + cổ đại).

## Status / Knowledge Progression Contract

- Macro progression: leo bậc thang xã hội thời đại đến (phẩm hàm, thực lực, ảnh hưởng)
- Meso progression: một chiến thắng chính trị / quân sự / kinh tế thay đổi cục diện
- Micro progression: xây quan hệ, tích kiến thức, chuẩn bị đòn bẩy

Cadence tham chiếu: ~10 chương có ~6 micro, ~3 meso, ~1 status shift lớn.

Status shift lớn yêu cầu:
- Ít nhất 2 loại fuel: kiến thức, quan hệ, tài sản, thời cơ, thông tin lịch sử
- Đối thủ / trở ngại rõ trước khi vượt qua
- Foreshadow 3-1-1 cho status flip lớn (phong hầu, bị truy sát, lật phe)
- Quá trình trên trang: tính toán, thi triển, phản đòn, aftermath
- Aftermath: địa vị đổi, kẻ thù mới, paradox history nếu có

## Paradox / Butterfly Effect Rule

Mỗi hành động thay đổi lịch sử lớn phải có:
- Ghi rõ mức độ thay đổi (nhỏ: ngày cụ thể / lớn: sự kiện lịch sử / tuyệt đối: triều đại)
- Hậu quả lan tỏa (người khác bị ảnh hưởng, tương lai MC biết có còn đúng)
- Sự chủ động hay vô tình của MC

Không viết: "MC thay đổi lịch sử." Phải viết: MC làm gì, ai chịu hậu quả, tương lai MC biết giờ còn đúng bao nhiêu %.

## Operating Systems

Time Travel worldbuilding không phải background. Khi chương dùng:
- **Quan trường / triều đình**: phẩm hàm, phe phái, nhiệm vụ, thăng giáng, cấm kỵ
- **Quân sự**: binh chủng, hậu cần, chiến thuật, tướng lĩnh, thời tiết
- **Kinh tế cổ**: tiền tệ, thuế, buôn bán, đổi chác, độc quyền
- **Xã hội giai cấp**: quý tộc, sĩ, nông, công, thương, nô, hạng người
- **Văn hóa / tôn giáo**: lễ nghi, tục lệ, kiêng kỵ, tín ngưỡng
- **Gia tộc / danh dự**: tông pháp, thừa kế, nợ máu, nghi lễ hôn nhân

Hệ thống nào xuất hiện phải có luật, áp lực cụ thể, hậu quả khi vi phạm.

## Review Verdict Rules

| Verdict | Điều kiện |
|---------|-----------|
| `PASS` | Đủ Tier 1 + Tier 2, status progression hợp lý, operating rules rõ, paradox có hậu quả |
| `PASS_WITH_FLAGS` | 1 lớp depth yếu nhưng phục hồi được |
| `SOFT_FAIL_STYLE` | 2 lớp texture/depth yếu |
| `HARD_FAIL_DEPTH` | Cảnh không có cơ chế lịch sử/quan trường vận hành, HOẶC MC dùng kiến thức hiện đại miễn phí (không cái giá), HOẶC status flip đột ngột, HOẶC paradox không có butterfly effect |

## Anti-Godlike Rule

MC có kiến thức hiện đại là lợi thế, nhưng KHÔNG phải miễn phí:
- Không biết tường tận chi tiết lịch sử (nhớ mơ hồ)
- Không có quan hệ / quyền lực ở thời đại đến
- Thân thể cũ yếu / thương tích / thân phận bất lợi
- Kiến thức hiện đại cần thời gian + tài nguyên để áp dụng (vd: làm súng cần sắt, thợ, thuốc súng)
- Không ai tin MC — phải xây dựng uy tín từ đầu

Reviewer phải hard-fail nếu MC dùng kiến thức hiện đại giải quyết vấn đề mà không có chuẩn bị hoặc cái giá.

## Không Conflict Rule

- Canon riêng truyện luôn thắng guide chung.
- Paradox rules do `PROJECT_DNA.md` quyết định — guide không ép mọi truyện cùng 1 loại (shared timeline, parallel universe, reset loop).
