# Substitute Depth Contract

## Source of Truth

Thứ tự ưu tiên file cho thể loại Substitute:

1. `PROJECT_DNA.md` — luật tối cao của dự án cụ thể
2. `Substitute_Operating_Guide.md` — quy tắc vận hành thể loại
3. `Substitute_Depth_Contract.md` — hợp đồng chiều sâu (file này)
4. `vocabulary.txt` — từ vựng chuyên biệt thể loại
5. Per-novel canon files — tài liệu canon riêng từng tác phẩm

Khi có xung đột giữa các file, file có thứ tự ưu tiên cao hơn luôn thắng.

## Positive Standard

Một chương Substitute đạt chuẩn là chương mà vết thương so sánh hiện diện tự nhiên trong hành động và đối thoại (không phải qua độc thoại giải thích); nhân vật chính đối diện ít nhất một khoảnh khắc bị nhầm lẫn hoặc so sánh với người tiền nhiệm; có lựa chọn rõ ràng với cái giá cảm xúc; và cuối chương, mối quan hệ hoặc nhận thức nội tâm đã dịch chuyển ít nhất một bậc so với đầu chương — tất cả được thể hiện qua hành động cụ thể chứ không phải tuyên bố trừu tượng.

## Texture Tier System

| Tier | Tên | Tiêu chí đánh giá |
|------|-----|-------------------|
| **Tier 1** | Bắt buộc | Vết thương so sánh hiện diện; xung đột danh tính trong cảnh chính; lựa chọn có cái giá; thay đổi trạng thái cuối cảnh |
| **Tier 2** | Khuyến nghị | Motif lặp (gương/vật kỷ niệm) xuất hiện; giọng văn phân biệt "đóng vai" vs. "là mình"; đối thoại tầng nghĩa kép |
| **Tier 3** | Tuỳ chọn | Cấu trúc song tuyến; ẩn dụ mở rộng xuyên suốt; POV người gốc xen kẽ |

Đánh giá dựa trên tier:
- Tier 1 thiếu → HARD_FAIL
- Tier 2 thiếu → PASS_WITH_FLAGS
- Tier 3 thiếu → không ảnh hưởng verdict

## Scene Types

| Tag | Mô tả | Yêu cầu đặc biệt |
|-----|--------|-------------------|
| `COMPARISON` | Cảnh đối chiếu trực tiếp với người gốc | Phải có phản ứng nội tâm của nhân vật chính |
| `MISIDENTITY` | Cảnh bị nhầm lẫn danh tính | Phải cho thấy cái giá cảm xúc của sự nhầm lẫn |
| `REVEAL` | Cảnh tiết lộ sự thật về vai trò thay thế | Phải có tiền đề từ chương trước |
| `RECLAMATION` | Cảnh đòi lại bản ngã | Phải có hành động cụ thể, không chỉ tuyên bố |
| `INTIMACY` | Cảnh thân mật — câu hỏi "yêu ai" hiện diện | Phải duy trì ambiguity hoặc giải quyết có cái giá |
| `CONFRONTATION` | Cảnh đối đầu về danh tính | Phải có stakes rõ ràng cho cả hai bên |

## Progression Contract

**Macro Progression (toàn tác phẩm):**

- Arc 1: Thiết lập vai trò thay thế — nhân vật chấp nhận hoặc bị ép vào vị trí.
- Arc 2: Nghi ngờ và manh mối — nhân vật bắt đầu nhận ra và phản kháng.
- Arc 3: Khủng hoảng danh tính — sự thật bộc lộ, mối quan hệ bị thử thách.
- Arc 4: Giải quyết — thay thế hoàn toàn (bi kịch) hoặc đòi lại bản ngã (giải phóng).

**Micro Progression (mỗi chương):**

- Mỗi chương phải tiến ít nhất một bước trên thang: chấp nhận → nghi ngờ → nhận ra → phản kháng → đối đầu → giải quyết.
- Không được đứng yên quá 2 chương liên tiếp trên cùng một bậc.

## Review Verdict Rules

| Verdict | Điều kiện |
|---------|-----------|
| **PASS** | Đủ Tier 1; progression tiến ít nhất 1 bước; scene vitality đủ 4 yếu tố; không vi phạm Operating Rules |
| **PASS_WITH_FLAGS** | Đủ Tier 1 nhưng thiếu Tier 2; hoặc progression hơi chậm nhưng không đứng yên; hoặc có 1 cảnh yếu scene vitality |
| **HARD_FAIL_TEXTURE** | Thiếu Tier 1 — vết thương so sánh không hiện diện, hoặc không có xung đột danh tính trong cảnh chính |
| **HARD_FAIL_DEPTH** | Progression đứng yên ≥2 chương; hoặc nhân vật chính thụ động hoàn toàn không có phản ứng nội tâm |
| **HARD_FAIL_OPERATING** | Vi phạm Operating Rules — tiết lộ không tiền đề, phản diện phẳng, hoặc lãng mạn hoá sự thay thế |

## Genre Conflict Rule

Khi có xung đột giữa bất kỳ quy tắc nào trong Depth Contract này với `PROJECT_DNA.md` hoặc per-novel canon, **PROJECT_DNA.md và per-novel canon luôn thắng.**

Thứ tự phân xử:
1. PROJECT_DNA.md (luật tối cao)
2. Per-novel canon (tài liệu canon riêng tác phẩm)
3. Substitute Operating Guide
4. Substitute Depth Contract (file này)

Reviewer không được đánh HARD_FAIL dựa trên quy tắc thể loại nếu PROJECT_DNA.md hoặc canon cho phép ngoại lệ rõ ràng.
