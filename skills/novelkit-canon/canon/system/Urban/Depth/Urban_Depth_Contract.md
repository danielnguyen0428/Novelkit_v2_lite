# Urban Depth Contract

Mục đích: Contract index cho Quality Auditor và Verifier. Định nghĩa verdict rules và trỏ sang source of truth cho từng lớp depth của thể loại Đô Thị.

## Source of Truth

| Lớp | Source File | Vai trò |
|-----|------------|---------|
| Consistency Rules | `system/Urban/Urban_consistency_rules.md` | Thế giới ngầm, gia tộc, pháp luật, siêu năng lực |
| Style Guide | `system/Urban/Urban_style.md` | Văn phong, đối thoại, cấu trúc chương |
| Genre Operating | `system/Urban/Genre Operating/Urban_Operating_Guide.md` | Cơ chế vận hành thế lực ngầm, quan trường, kinh tế |

## Urban Positive Standard

Mỗi chương Urban phải thể hiện ít nhất một cơ chế xã hội/quyền lực/dị năng thực sự tác động đến một lựa chọn, xung đột, nhận thức, cái giá phải trả, hoặc hậu quả.

Các cơ chế được chấp nhận:
- Thế giới ngầm / gia tộc / tổ chức bí mật áp lực lên MC
- Pháp luật / camera / mạng xã hội ràng buộc lựa chọn
- Quyền lực chính trị / kinh doanh / tài chính làm đòn bẩy hoặc trói buộc
- Siêu năng lực / dị năng (nếu có) với giới hạn và cái giá rõ
- Quan hệ nhân mạch / ân oán / thù hận cũ ép hành động

## Texture Tier System

| Tier | Yêu cầu | Ý nghĩa |
|------|----------|---------|
| **Tier 1** (bắt buộc) | Cơ chế quyền lực/xã hội vận hành trong scene | gia tộc can thiệp, pháp luật đe dọa, thế lực ngầm xuất đầu, dị năng tạo hậu quả |
| **Tier 2** (bắt buộc) | Áp lực tâm lý/xã hội hoặc rủi ro vật lý | danh tiếng bị đe dọa, mất việc, bị truy sát, căng thẳng gia đình, áp lực media |
| **Tier 3** (hỗ trợ) | Tài sản / vật phẩm / phương tiện | xe, đồng hồ, biệt thự, vũ khí — KHÔNG thay thế Tier 1/2 |

## Scene Types

Outline phải gắn tag cho mỗi cảnh chính:
- `power_move`: thương trường, chính trị, thế lực ngầm tranh đoạt
- `social_pressure`: gia tộc, bạn bè, media, dư luận ép lựa chọn
- `investigation`: truy tìm, thu thập chứng cứ, phân tích người và tình huống
- `confrontation`: đối đầu, deal-making, đàm phán dưới chênh lệch quyền lực
- `transition`: hồi phục, di chuyển, nhịp cảm xúc nhẹ

Ngay cả `transition` cũng cần nhận thức về áp lực đô thị, trừ khi outline giải thích rõ.

## Power/Status Progression Contract

- Macro progression: leo bậc thang quyền lực xuyên arc (vị thế xã hội, kinh tế, ảnh hưởng)
- Meso progression: giành một deal, triệt hạ một đối thủ, lật một cục diện
- Micro progression: thu thập thông tin, xây quan hệ, tích tài nguyên mỗi chương

Cadence tham chiếu: trong ~10 chương, có ~6 micro, ~3 meso, ~1 notable status/power shift. Lệch phải có lý do.

Các status flip lớn yêu cầu:
- Ít nhất 2 loại fuel: thông tin, tiền, quan hệ, đòn bẩy tâm lý, cơ hội timing
- Đối thủ / trở ngại rõ ràng trước khi lật cục diện
- Foreshadow 3-1-1 cho power flip lớn: 3 dấu xa, 1 dấu gần, 1 dấu trực tiếp
- Quá trình trên trang: tính toán, ra đòn, phản đòn, kết cục
- Aftermath: địa vị thay đổi, kẻ thù mới, cái giá xã hội/đạo đức

## Operating Systems

Urban worldbuilding không phải background. Khi chương dùng:
- **Gia tộc / dòng họ**: hierarchy, luật nội bộ, phân chia tài sản, kẻ kế thừa, cấm kỵ
- **Thế giới ngầm**: băng nhóm, địa bàn, luật ngầm, tiền lệ, kẻ thù truyền kiếp
- **Chính trị / quan trường**: chức vụ, bè phái, nhiệm vụ, thưởng phạt, điểm yếu cơ cấu
- **Thương trường**: thị phần, cổ phần, thâu tóm, phá sản, kiện tụng, hợp đồng
- **Media / dư luận**: scandal, PR, ảnh hưởng truyền thông, mạng xã hội
- **Dị năng / hệ thống đặc biệt** (nếu có): nguồn gốc, giới hạn, cái giá, rủi ro phát hiện

Hệ thống nào xuất hiện phải có luật, nguồn gốc, người kiểm soát, rủi ro và hậu quả.

## Review Verdict Rules

| Verdict | Điều kiện |
|---------|-----------|
| `PASS` | Đủ Tier 1 + Tier 2, status progression hợp lý, operating rules rõ |
| `PASS_WITH_FLAGS` | 1 lớp depth yếu nhưng phục hồi được |
| `SOFT_FAIL_STYLE` | 2 lớp texture/depth yếu |
| `HARD_FAIL_DEPTH` | Cảnh không có cơ chế quyền lực/xã hội vận hành, HOẶC lặp texture nông 3 chương, HOẶC status flip đột ngột thiếu fuel/foreshadow/process/aftermath, HOẶC operating systems xuất hiện như nhãn dán không có luật/rủi ro/hậu quả |

## Không Conflict Rule

- Canon riêng truyện (`PROJECT_DNA.md`, database, author style) luôn thắng guide chung.
- Guide chung không bắt mọi truyện dùng tất cả hệ; chỉ bắt hệ đã xuất hiện phải có luật, giá, nguồn gốc và hậu quả.
- Với Urban hiện đại, tôn trọng pháp luật và ràng buộc xã hội thực tế — không phá luật cơ bản trừ khi setting cho phép (vd hệ thống ngầm có miễn trừ).
