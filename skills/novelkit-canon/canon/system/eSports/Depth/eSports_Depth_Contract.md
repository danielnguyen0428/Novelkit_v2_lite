# eSports Depth Contract

## Source of Truth

Thứ tự ưu tiên file cho thể loại eSports:

1. `PROJECT_DNA.md` — luật tối cao của dự án cụ thể
2. `eSports_Operating_Guide.md` — quy tắc vận hành thể loại
3. `eSports_Depth_Contract.md` — hợp đồng chiều sâu (file này)
4. `vocabulary.txt` — từ vựng chuyên biệt thể loại
5. Per-novel canon files — tài liệu canon riêng từng tác phẩm

Khi có xung đột giữa các file, file có thứ tự ưu tiên cao hơn luôn thắng.

## Positive Standard

Một chương eSports đạt chuẩn là chương mà stakes trận đấu hoặc xung đột đội rõ ràng và cao hơn chương trước; cảnh thi đấu (nếu có) tạo cảm giác thời gian thực với nhịp văn nhanh và quyết định tức thì; xung đột nội bộ đội hiện diện song song với thách thức bên ngoài; đời thực của nhân vật được phản ánh; và mỗi cảnh tập luyện có mục tiêu đo lường được — tất cả phục vụ hành trình cạnh tranh và trưởng thành của nhân vật.

## Texture Tier System

| Tier | Tên | Tiêu chí đánh giá |
|------|-----|-------------------|
| **Tier 1** | Bắt buộc | Stakes leo thang; xung đột đội rõ; cảnh thi đấu nhịp thời gian thực; đời thực hiện diện |
| **Tier 2** | Khuyến nghị | Meta-game tiến hoá; motif bàn tay/màn hình; tâm lý thi đấu sâu; đối thủ có chiều sâu |
| **Tier 3** | Tuỳ chọn | Bình luận viên/khán giả như nhân vật; phân tích chiến thuật tích hợp; góc nhìn ngành |

Đánh giá dựa trên tier:
- Tier 1 thiếu → HARD_FAIL
- Tier 2 thiếu → PASS_WITH_FLAGS
- Tier 3 thiếu → không ảnh hưởng verdict

## Scene Types

| Tag | Mô tả | Yêu cầu đặc biệt |
|-----|--------|-------------------|
| `MATCH` | Cảnh thi đấu chính thức | Nhịp văn nhanh; stakes rõ; quyết định tức thì |
| `TRAINING` | Cảnh tập luyện | Mục tiêu cụ thể; thất bại/thành công đo lường được |
| `TEAM_CONFLICT` | Cảnh xung đột nội bộ đội | Phải có stakes cho cả đội, không chỉ cá nhân |
| `STRATEGY` | Cảnh bàn chiến thuật/phân tích | Phải lồng vào xung đột hoặc áp lực thời gian |
| `OFFSCREEN` | Cảnh đời thực ngoài game | Phải kết nối với áp lực thi đấu hoặc phát triển nhân vật |
| `RIVAL` | Cảnh tương tác với đối thủ | Phải xây dựng chiều sâu cho đối thủ, không chỉ đe doạ |

## Progression Contract

**Macro Progression (toàn tác phẩm):**

- Arc 1: Thiết lập đội và mục tiêu — giới thiệu dynamics, xác định thách thức đầu tiên.
- Arc 2: Leo thang cạnh tranh — đối thủ mạnh hơn, meta thay đổi, xung đột đội bùng phát.
- Arc 3: Khủng hoảng — thất bại lớn, đội có nguy cơ tan rã, giới hạn cá nhân bộc lộ.
- Arc 4: Giải quyết — chiến thắng có ý nghĩa, hoặc thất bại nhưng trưởng thành, hoặc tái sinh.

**Micro Progression (mỗi chương):**

- Mỗi chương phải tiến ít nhất một bước: kỹ năng cải thiện, mối quan hệ đội thay đổi, hoặc stakes tăng.
- Cảnh tập luyện không được chiếm quá 30% chương.
- Mỗi trận đấu phải có stakes cao hơn trận trước (về ý nghĩa, không nhất thiết về giải thưởng).

## Review Verdict Rules

| Verdict | Điều kiện |
|---------|-----------|
| **PASS** | Đủ Tier 1; stakes leo thang; xung đột đội hiện diện; cảnh thi đấu có nhịp đúng; đời thực được phản ánh |
| **PASS_WITH_FLAGS** | Đủ Tier 1 nhưng thiếu Tier 2; hoặc đối thủ chưa có chiều sâu; hoặc meta-game chưa tiến hoá |
| **HARD_FAIL_TEXTURE** | Thiếu Tier 1 — stakes không leo thang, hoặc cảnh thi đấu nhịp chậm như tường thuật, hoặc đội không có xung đột |
| **HARD_FAIL_DEPTH** | Progression đứng yên; nhân vật chính bất bại; hoặc đời thực hoàn toàn vắng mặt |
| **HARD_FAIL_OPERATING** | Vi phạm Operating Rules — giải thích kỹ thuật dài dòng, đội hoàn hảo, hoặc tập luyện >30% |

## Genre Conflict Rule

Khi có xung đột giữa bất kỳ quy tắc nào trong Depth Contract này với `PROJECT_DNA.md` hoặc per-novel canon, **PROJECT_DNA.md và per-novel canon luôn thắng.**

Thứ tự phân xử:
1. PROJECT_DNA.md (luật tối cao)
2. Per-novel canon (tài liệu canon riêng tác phẩm)
3. eSports Operating Guide
4. eSports Depth Contract (file này)

Reviewer không được đánh HARD_FAIL dựa trên quy tắc thể loại nếu PROJECT_DNA.md hoặc canon cho phép ngoại lệ rõ ràng.
