# Romance Depth Contract

Mục đích: Contract index cho Quality Auditor và Verifier. Định nghĩa verdict rules và trỏ sang source of truth cho từng lớp depth của thể loại Ngôn Tình.

## Source of Truth

| Lớp | Source File | Vai trò |
|-----|------------|---------|
| Consistency Rules | `system/Romance/Romance_consistency_rules.md` | Xã hội, giai cấp, rào cản tình yêu |
| Style Guide | `system/Romance/Romance_style.md` | Văn phong, đối thoại tình cảm, cấu trúc chương |

## Romance Positive Standard

Mỗi chương Romance phải thể hiện ít nhất một cơ chế cảm xúc/quan hệ/xã hội thực sự tác động đến một lựa chọn, xung đột, nhận thức, cái giá phải trả, hoặc hậu quả.

Các cơ chế được chấp nhận:
- Quan hệ tình cảm thay đổi trạng thái (tiến gần, lùi xa, đứng yên có lý do)
- Rào cản xã hội / giai cấp / gia đình ép lựa chọn
- Hiểu lầm / bí mật / quá khứ ám ảnh tạo căng thẳng
- Tình địch / kẻ thứ ba can thiệp
- Sự kiện bên ngoài (bệnh tật, xa cách, công việc) thay đổi cục diện

## Texture Tier System

| Tier | Yêu cầu | Ý nghĩa |
|------|----------|---------|
| **Tier 1** (bắt buộc) | Cơ chế cảm xúc vận hành trong scene | lựa chọn tình cảm có giá, hiểu lầm leo thang, trái tim đối đầu lý trí, ân nghĩa ép hành động |
| **Tier 2** (bắt buộc) | Áp lực xã hội/nội tâm hoặc rủi ro quan hệ | gia đình can thiệp, bị hiểu lầm, đánh mất người quan trọng, tự vấn bản thân |
| **Tier 3** (hỗ trợ) | Bối cảnh vật chất / thời gian | nhà hàng, bữa tiệc, chuyến đi — KHÔNG thay thế Tier 1/2 |

## Scene Types

Outline phải gắn tag cho mỗi cảnh chính:
- `intimacy_beat`: khoảnh khắc gần gũi (thể xác, tâm hồn, hoặc chia sẻ bí mật)
- `conflict_beat`: cãi nhau, hiểu lầm, xa cách, phản bội
- `social_pressure`: gia đình, bạn bè, dư luận ép quan hệ
- `investigation`: phát hiện bí mật, nghi ngờ, truy tìm sự thật về người yêu
- `transition`: công việc, cuộc sống thường nhật, hồi phục cảm xúc

Ngay cả `transition` cũng cần nhận thức cảm xúc về mối quan hệ, trừ khi outline giải thích rõ.

## Relationship Progression Contract

- Macro progression: 4 stages tình yêu — Chú ý → Quan tâm → Nhận ra → Chấp nhận
- Meso progression: một beat lớn (lần gặp đầu, nụ hôn đầu, lần cãi nhau lớn, chia tay, đoàn tụ)
- Micro progression: ánh nhìn, lời nói ẩn ý, hành động nhỏ thể hiện tình cảm

Cadence tham chiếu: trong ~10 chương, có ~6 micro (ánh mắt, câu nói ẩn ý), ~3 meso (tương tác rõ), ~1 stage shift lớn. Lệch phải có lý do.

Stage shift lớn yêu cầu:
- Ít nhất 2 loại fuel: hành động hy sinh, phát hiện sự thật, áp lực ngoại cảnh, cảm xúc tích tụ
- Rào cản rõ ràng trước khi vượt qua (gia đình, hiểu lầm, giai cấp, thời gian)
- Foreshadow 3-1-1 cho relationship flip lớn (tỏ tình, chia tay, cưới, chết): 3 dấu xa, 1 dấu gần, 1 dấu trực tiếp
- Quá trình trên trang: hành động được kiếm (earned), không đột ngột
- Aftermath: mối quan hệ thay đổi trạng thái, ảnh hưởng đến các tuyến khác (bạn bè, gia đình, công việc)

## Operating Systems

Romance worldbuilding không phải phông. Khi chương dùng:
- **Gia đình / dòng họ**: cấm kỵ, áp lực hôn nhân, thừa kế, danh dự
- **Giai cấp / nghề nghiệp**: khoảng cách thu nhập, môi trường xã hội, định kiến
- **Quá khứ / ghost**: vết thương cũ ảnh hưởng khả năng yêu
- **Tình địch / kẻ thứ ba**: động cơ, chiến thuật, thời điểm can thiệp
- **Bối cảnh thời gian** (nếu xuyên không/cổ trang): luật hôn nhân, vị thế phụ nữ, quyền thừa kế

Hệ thống nào xuất hiện phải có luật, áp lực cụ thể, hậu quả khi vi phạm.

## Review Verdict Rules

| Verdict | Điều kiện |
|---------|-----------|
| `PASS` | Đủ Tier 1 + Tier 2, relationship progression có earned, social rules rõ |
| `PASS_WITH_FLAGS` | 1 lớp depth yếu nhưng phục hồi được |
| `SOFT_FAIL_STYLE` | 2 lớp texture/depth yếu |
| `HARD_FAIL_DEPTH` | Cảnh không có cơ chế cảm xúc/quan hệ vận hành, HOẶC instant love không foreshadow, HOẶC relationship flip thiếu fuel/earned process, HOẶC social systems xuất hiện như nhãn dán |

## Show-Don't-Tell Rule

Cảm xúc phải được SHOW qua:
- Hành động (không chạm nhau nhưng đứng gần, né tiếp xúc mắt, cử chỉ vô thức)
- Biểu cảm vi tế (hơi thở ngắn, ngón tay siết, môi mím)
- Lời nói ẩn ý (subtext, không nói thẳng)
- Quyết định có giá (chọn ở lại, chọn rời đi, chọn im lặng)

KHÔNG viết: "Nàng cảm thấy rất đau lòng."
Reviewer phải hard-fail nếu chương dùng `cảm thấy [tính từ cảm xúc]` quá 2 lần.

## Không Conflict Rule

- Canon riêng truyện luôn thắng guide chung.
- Guide không bắt mọi truyện cùng 1 công thức tình cảm; chỉ bắt có cơ chế earned và hậu quả.
