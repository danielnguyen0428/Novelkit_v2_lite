# Streaming Depth Contract

## Source of Truth

Thứ tự ưu tiên file cho thể loại Streaming:

1. `PROJECT_DNA.md` — luật tối cao của dự án cụ thể
2. `Streaming_Operating_Guide.md` — quy tắc vận hành thể loại
3. `Streaming_Depth_Contract.md` — hợp đồng chiều sâu (file này)
4. `vocabulary.txt` — từ vựng chuyên biệt thể loại
5. Per-novel canon files — tài liệu canon riêng từng tác phẩm

Khi có xung đột giữa các file, file có thứ tự ưu tiên cao hơn luôn thắng.

## Positive Standard

Một chương Streaming đạt chuẩn là chương mà khoảng cách giữa persona và con người thật được thể hiện rõ qua hành vi on/off camera; khán giả hiện diện như lực lượng sống ảnh hưởng quyết định nhân vật; áp lực nền tảng hoặc kinh tế tạo stakes thực; ranh giới parasocial được khám phá hoặc bị thử thách; và mỗi lựa chọn có cái giá rõ ràng giữa sự nghiệp và bản ngã — tất cả phục vụ câu hỏi trung tâm về danh tính trong thời đại số.

## Texture Tier System

| Tier | Tên | Tiêu chí đánh giá |
|------|-----|-------------------|
| **Tier 1** | Bắt buộc | Persona vs. bản ngã rõ; khán giả là lực lượng sống; áp lực nền tảng; ranh giới parasocial |
| **Tier 2** | Khuyến nghị | Khoảnh khắc viral có hậu quả; kinh tế sáng tạo; cảnh on/off camera tương phản; motif mặt nạ/con số |
| **Tier 3** | Tuỳ chọn | Comment mạng như giọng hợp xướng; cấu trúc chương mô phỏng stream; góc nhìn ngành |

Đánh giá dựa trên tier:
- Tier 1 thiếu → HARD_FAIL
- Tier 2 thiếu → PASS_WITH_FLAGS
- Tier 3 thiếu → không ảnh hưởng verdict

## Scene Types

| Tag | Mô tả | Yêu cầu đặc biệt |
|-----|--------|-------------------|
| `ON_AIR` | Cảnh trên sóng/đang stream | Phải cho thấy persona hoạt động; khán giả phản ứng |
| `OFF_AIR` | Cảnh ngoài sóng — con người thật | Phải tương phản với persona; cho thấy cái giá |
| `VIRAL` | Cảnh bùng nổ — nội dung viral | Phải có hậu quả (tích cực lẫn tiêu cực) |
| `PARASOCIAL` | Cảnh ranh giới parasocial bị thử thách | Phải có stakes cho cả streamer và fan |
| `PLATFORM` | Cảnh áp lực nền tảng — thuật toán/chính sách | Phải ảnh hưởng trực tiếp đến sinh kế hoặc chiến lược |
| `IDENTITY` | Cảnh khủng hoảng bản ngã — mặt nạ rơi | Phải có hậu quả kéo dài, không chỉ khoảnh khắc |

## Progression Contract

**Macro Progression (toàn tác phẩm):**

- Arc 1: Thiết lập persona và nền tảng — giới thiệu khoảng cách persona/bản ngã, xây dựng khán giả.
- Arc 2: Leo thang — thành công tạo áp lực lớn hơn, persona nuốt chửng bản ngã, ranh giới mờ.
- Arc 3: Khủng hoảng — scandal, burnout, hoặc mặt nạ rơi. Mối quan hệ thật bị đe doạ.
- Arc 4: Giải quyết — tái định nghĩa mối quan hệ với khán giả, hoặc rời bỏ, hoặc tìm cân bằng mới.

**Micro Progression (mỗi chương):**

- Mỗi chương phải đẩy khoảng cách persona/bản ngã xa hơn hoặc gần hơn — không đứng yên.
- Áp lực khán giả/nền tảng phải tích luỹ — chương sau nặng hơn chương trước.
- Ít nhất 30% cảnh phải diễn ra "trên sóng" hoặc trong quá trình tạo nội dung.

## Review Verdict Rules

| Verdict | Điều kiện |
|---------|-----------|
| **PASS** | Đủ Tier 1; progression đẩy khoảng cách persona/bản ngã; khán giả ảnh hưởng quyết định; áp lực tích luỹ |
| **PASS_WITH_FLAGS** | Đủ Tier 1 nhưng thiếu Tier 2; hoặc kinh tế chưa hiện diện; hoặc cảnh on/off chưa tương phản rõ |
| **HARD_FAIL_TEXTURE** | Thiếu Tier 1 — persona/bản ngã không phân biệt, hoặc khán giả là NPC, hoặc không có áp lực nền tảng |
| **HARD_FAIL_DEPTH** | Progression đứng yên; hoặc nổi tiếng không hậu quả; hoặc khoảng cách persona không thay đổi |
| **HARD_FAIL_OPERATING** | Vi phạm Operating Rules — viral giải quyết mọi thứ, bỏ qua kinh tế, hoặc khán giả không ảnh hưởng cốt truyện |

## Genre Conflict Rule

Khi có xung đột giữa bất kỳ quy tắc nào trong Depth Contract này với `PROJECT_DNA.md` hoặc per-novel canon, **PROJECT_DNA.md và per-novel canon luôn thắng.**

Thứ tự phân xử:
1. PROJECT_DNA.md (luật tối cao)
2. Per-novel canon (tài liệu canon riêng tác phẩm)
3. Streaming Operating Guide
4. Streaming Depth Contract (file này)

Reviewer không được đánh HARD_FAIL dựa trên quy tắc thể loại nếu PROJECT_DNA.md hoặc canon cho phép ngoại lệ rõ ràng.
