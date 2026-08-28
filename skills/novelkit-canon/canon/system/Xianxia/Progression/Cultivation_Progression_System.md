# CULTIVATION PROGRESSION SYSTEM
## Module Bổ Sung Tu Luyện & Thăng Cấp — Agentic AI Tiên Hiệp
> **Phiên bản:** v3.00 | **Tích hợp với:** Tu Tiên Texture Floor v3.00
> **Vấn đề giải quyết:** Agent sáng tác thiếu nhất quán trong việc dệt các cột mốc tu luyện vào mạch truyện — thăng cấp bị bỏ sót, xuất hiện đột ngột, hoặc không có trọng lượng cảm xúc.

---

## MỤC LỤC

1. [Chẩn Đoán — Tại Sao Agent Thiếu Sót](#1-chẩn-đoán)
2. [Kiến Trúc Progression — Nhìn Toàn Cục](#2-kiến-trúc-progression)
3. [Cultivation Clock — Đồng Hồ Tu Luyện](#3-cultivation-clock)
4. [Hệ Thống Foreshadowing Thăng Cấp](#4-foreshadowing-thăng-cấp)
5. [Templates Cảnh Thăng Cấp Theo Loại](#5-templates-cảnh-thăng-cấp)
6. [Hệ Thống Bottleneck & Trắc Trở](#6-bottleneck--trắc-trở)
7. [Progression Tracker — Công Cụ Cho Agent](#7-progression-tracker)
   - [Luật Hành Trình Tu Luyện Cho Plot Weaver](#73-luật-hành-trình-tu-luyện-cho-plot-weaver)
8. [Tích Hợp Vào Arc Truyện](#8-tích-hợp-vào-arc-truyện)
9. [Quality Check — Kiểm Tra Trước Xuất Bản](#9-quality-check)

---

## 1. CHẨN ĐOÁN

### 1.1 Bốn thiếu sót thường gặp

Agent sáng tác tiên hiệp thường mắc bốn lỗi sau với nội dung tu luyện:

**Lỗi A — "Bỗng nhiên thăng cấp"**
Nhân vật đang làm việc khác → đột nhiên "bước vào Kết Đan Kỳ" không báo trước, không chuẩn bị, không cảm giác. Thường xảy ra vì agent tập trung vào plot mà quên tracking cảnh giới.

**Lỗi B — "Thăng cấp vô hình"**
Agent ghi nhận cảnh giới trong outline nhưng không viết cảnh thăng cấp thực sự — chỉ mention trong 1 câu hoặc bỏ qua hoàn toàn. Độc giả không cảm nhận được sự tăng trưởng.

**Lỗi C — "Tu luyện chỉ xuất hiện khi cần"**
Tu luyện chỉ được nhắc đến trước khi thăng cấp hoặc trước trận chiến lớn. Không có nền tảng tu luyện hàng ngày, không có nỗ lực tích lũy liên tục → thăng cấp thiếu xứng đáng.

**Lỗi D — "Tất cả thăng cấp đều giống nhau"**
Mọi cảnh đột phá đều có cùng cấu trúc: ngồi thiền → linh khí bùng nổ → mở mắt ra đã mạnh hơn. Thiếu đa dạng về điều kiện, cảm giác, và ý nghĩa.

### 1.2 Nguyên nhân gốc rễ

Agent không có **bộ nhớ progression** xuyên suốt các lần generate. Mỗi chương được viết độc lập — không có "đồng hồ tu luyện" chạy ngầm để agent biết:
- Nhân vật đang ở đâu trong hành trình tu luyện?
- Bao lâu nữa đến cột mốc tiếp theo?
- Đã có bao nhiêu "nhiên liệu" (cơ duyên, đan dược, nỗ lực) được tích lũy?

**Giải pháp:** Module này cung cấp **Cultivation Clock** + **Progression Tracker** — hai công cụ agent PHẢI check trước khi viết mỗi chương.

---

## 2. KIẾN TRÚC PROGRESSION

### 2.1 Ba tầng progression

Tu luyện trong tiểu thuyết tiên hiệp hoạt động trên ba tầng đồng thời:

```
TẦNG 1 — MACRO PROGRESSION (Arc truyện)
Hành trình từ Phàm Nhân → Đỉnh Cao Tiên Đạo
Mỗi cảnh giới lớn = 1 giai đoạn cuộc đời nhân vật
Thay đổi: nhân sinh quan, quan hệ, kẻ thù, sứ mệnh

TẦNG 2 — MESO PROGRESSION (Volume/Arc nhỏ)
Hành trình qua các tầng trong một cảnh giới
Mỗi tầng = 1 vòng tăng trưởng nhỏ (effort → obstacle → breakthrough)
Thay đổi: năng lực cụ thể, hiểu biết về pháp tắc, vị thế xã hội

TẦNG 3 — MICRO PROGRESSION (Chương)
Hoạt động tu luyện hàng ngày
Tích lũy nhỏ: linh khí, hiểu ngộ nhỏ, kinh nghiệm chiến đấu
KHÔNG thay đổi cảnh giới, nhưng XÂY NỀN cho Tầng 2
```

**Quy tắc tỷ lệ tham chiếu:** Trong 10 chương, phân bổ như sau để giữ density tu luyện, không phải để ép breakthrough:
- ~6 chương có Micro Progression (mention tu luyện hàng ngày)
- ~3 chương có Meso Progression (tiến triển trong tầng)
- ~1 chương có notable cultivation beat: blocked breakthrough, mở bottleneck, gặt fuel lớn, lĩnh ngộ kỹ thuật, đổi trạng thái Cultivation Clock, hoặc breakthrough chỉ khi hợp spacing/canon

Spacing rules ở mục 7.2 và Luật Hành Trình ở mục 7.3 luôn thắng nhịp tham chiếu 10 chương.

### 2.1.1 Tốc độ tu luyện theo khế ước truyện

Create Novel có thể khóa `cultivation_speed` trong `PROJECT_DNA.md`. Đây là trần nhịp tiến cảnh cho Plot Weaver, Prose Writer và Sync/Memory:

- Nhanh: 5-15 tiểu cảnh, hoặc gần 1 đại cảnh mỗi 1-2 đại hồi.
- Chậm: 1 đại cảnh hoặc 2-4 tiểu cảnh trong một đại hồi.
- Siêu chậm: 0.5 đại cảnh, hoặc 1-3 tiểu cảnh trong một đại hồi.

Nếu truyện khóa tốc độ, Mộng Yểm phải chia bình cảnh, cơ duyên, bí cảnh, di tích và đột phá theo đại hồi. Huyết Thủ không được tự nâng cảnh giới vượt tốc độ này; Lãng Khách phải ghi lại tốc độ và mọi sai lệch có lý do trong Cultivation Clock.

### 2.1.2 Mốc tuổi tu luyện và benchmark đại thần

Tuổi không phải trang trí. Tuổi là cách hệ thống nhắc agent rằng tu luyện cần thời gian, thất bại, bế quan, hồi phục và đổi đời sống.

Với phong cách Nhĩ Căn/Tiên Nghịch, dùng benchmark tuổi như neo pacing. Ví dụ đã khóa: **51 tuổi: Trúc Cơ hậu kỳ**. Mốc này không bắt truyện nào cũng giống Vương Lâm, nhưng bắt agent phải giải thích nếu nhân vật nhanh hoặc chậm hơn:

- nhanh hơn: phải có cơ duyên, bí cảnh, đan dược, truyền thừa, tử chiến, hóa phàm/ngộ đạo hoặc kim thủ chỉ đã gieo trước
- chậm hơn: phải có linh căn kém, thiếu tài nguyên, tâm kết, căn cơ rạn, bị truy sát, phong cấm tu vi hoặc bình cảnh rõ
- bằng nhịp benchmark: phải thấy năm tháng tu luyện, không nhảy cảnh giới bằng một câu

Mỗi outline/chapter Xianxia phải tự trả lời: **nhân vật đang ở tuổi/thời gian tu luyện nào, đang tiến/lùi/kẹt ở đâu, vì sao mốc tiếp theo chưa tới hoặc đã tới**.

### 2.2 Progression Fuel — Nhiên liệu thăng cấp

Thăng cấp không xảy ra ngẫu nhiên — nó là **kết quả của nhiên liệu tích lũy**. Agent phải track các loại nhiên liệu:

```yaml
LOẠI NHIÊN LIỆU:

hard_resources:
  - linh thạch tiêu thụ (ước lượng)
  - đan dược sử dụng (tên + phẩm chất)
  - linh địa tu luyện (thời gian + chất lượng)
  - vật phẩm đặc biệt (linh căn, cơ duyên)

soft_resources:
  - thời gian tu luyện (ước lượng tháng/năm trong truyện)
  - hiểu ngộ từ chiến đấu (số trận + cường độ)
  - truyền thừa nhận được (pháp môn, bí kỹ)
  - cơ duyên kỳ ngộ (gặp vật/người/cảnh đặc biệt)

emotional_catalysts:
  - áp lực sinh tử (gần chết → bùng phát tiềm năng)
  - mất mát người thân (đau đớn → ý chí)
  - thề nguyện và mục tiêu (động lực dài hạn)
  - "tâm kết" được giải thoát (rào cản tâm lý)
```

**Quy tắc:** Một cảnh thăng cấp PHẢI có ít nhất 2 loại nhiên liệu từ các chương trước đó làm nền tảng.

---

## 3. CULTIVATION CLOCK

### 3.1 Định nghĩa

Cultivation Clock là **bảng trạng thái tu luyện** mà agent cập nhật sau mỗi chương quan trọng. Đây là "bộ nhớ ngoại vi" giải quyết vấn đề agent không nhớ progression.

### 3.2 Format Cultivation Clock

```yaml
# CULTIVATION CLOCK — [Tên nhân vật chính]
# Cập nhật lần cuối: Chương [X]

current_state:
  realm: "Kết Đan Kỳ"
  sub_level: "Trung kỳ"
  dan_quality: "Trung phẩm Kim Đan"  # chỉ áp dụng từ Kết Đan trở lên
  approximate_age_in_story: "23 tuổi"
  cultivation_time_elapsed: "~2 năm kể từ đầu truyện"
  age_at_last_breakthrough: "21 tuổi"
  years_in_current_realm: "~1 năm 8 tháng"
  realm_age_benchmark: "benchmark truyện/đại thần: 51 tuổi -> Trúc Cơ hậu kỳ nếu áp dụng NC"
  pace_vs_benchmark: "nhanh hơn vì đã dùng Linh Mạch Động + sinh tử chiến Ch.22; cần hậu quả"

fuel_accumulated:
  hard_resources:
    - "Tiêu thụ ~800 hạ phẩm linh thạch (Chương 1-45)"
    - "Phục Nguyên Đan x3 (Chương 12, 23, 38)"
    - "Tu luyện tại Linh Mạch Động 60 ngày (Chương 30-35)"
    - "Ngưng Đan Đan thượng phẩm x1 (Chương 44 — chưa dùng)"

  soft_resources:
    - "Hiểu ngộ kiếm ý từ 12 trận chiến thực sự (Chương 8, 15, 22...)"
    - "Nhận truyền thừa Ngũ Hành Kiếm Pháp (Chương 20)"
    - "Ngộ đạo tại Thiên Kiếm Nhai 3 ngày (Chương 40)"

  emotional_catalysts:
    - "Gần chết tại trận Vân Lâm (Chương 22) → ý chí kiên định hơn"
    - "Mất Sư Đệ Lý Vân (Chương 35) → thề phục thù"

next_breakthrough:
  target: "Kết Đan Kỳ Hậu kỳ"
  fuel_needed:
    - "1 linh mạch tốt hoặc ~500 trung phẩm linh thạch"
    - "1 lần ngộ đạo quan trọng về Kiếm Đạo"
    - "1 cơ duyên hoặc catalyst cảm xúc"
  estimated_chapters_away: "~15-20 chương"
  foreshadow_count: 2  # đã foreshadow 2 lần, cần thêm 1-2 lần nữa

bottleneck_active:
  description: "Kiếm ý chưa đủ tinh thuần — vẫn còn 'sát ý' quá nặng"
  introduced_at: "Chương 38"
  resolution_hint: "Cần tìm hiểu về 'Nhân Kiếm Hợp Nhất' hoặc trải qua cảnh tình để hiểu"

recent_micro_progressions:
  - "Ch.43: Luyện Hóa thêm 50 trung phẩm linh thạch"
  - "Ch.44: Nhận Ngưng Đan Đan — chưa dùng"
  - "Ch.45: Hiểu thêm 1 lớp về Ngũ Hành Tương Khắc trong kiếm pháp"
```

### 3.3 Khi nào agent UPDATE Cultivation Clock

```
BẮT BUỘC update sau:
□ Bất kỳ cảnh thăng cấp / đột phá nào
□ Nhân vật nhận cơ duyên lớn (pháp bảo, đan dược quý, truyền thừa)
□ Trận chiến lớn có ảnh hưởng đến tu vi
□ Nhân vật trải qua sự kiện cảm xúc cực độ
□ Mỗi ~10 chương dù không có sự kiện lớn

KHÔNG cần update:
- Chương đối thoại thuần túy
- Chương di chuyển đơn thuần
- Cảnh flashback
```

---

## 4. FORESHADOWING THĂNG CẤP

### 4.1 Quy tắc 3-1-1

Mỗi cảnh thăng cấp lớn PHẢI được foreshadow theo cấu trúc **3-1-1**:

```
3 lần foreshadow XA (3-10 chương trước):
  → Dấu hiệu nhẹ, độc giả có thể bỏ qua
  → Nhiên liệu tích lũy được nhắc đến

1 lần foreshadow GẦN (1-3 chương trước):
  → Dấu hiệu rõ hơn, nhân vật chú ý
  → Cảm giác "sắp xảy ra điều gì đó"

1 lần foreshadow TRỰC TIẾP (ngay chương thăng cấp):
  → Dấu hiệu không thể bỏ qua
  → Thiên địa dị tượng nhỏ, linh lực bất ổn
```

### 4.2 Menu foreshadow theo loại dấu hiệu

**Dấu hiệu thể chất (XA — nhẹ):**
```
- Linh lực trong đan điền "cựa quậy" nhẹ vào buổi sáng
- Giấc ngủ ngắn hơn bình thường, tinh thần vẫn sảng khoái
- Thèm ăn một loại linh thảo nhất định
- Ngón tay vô thức vẽ pháp văn trong không khí
- Linh căn phản ứng nhạy hơn với môi trường xung quanh
```

**Dấu hiệu linh khí (XA — nhẹ):**
```
- Linh khí xung quanh nhân vật "tự động" tụ lại nhẹ khi ngồi
- Pháp bảo tự phát sáng mà không cần kích hoạt
- Tiểu động vật tiên thú bị thu hút lại gần hơn
- Thực vật linh gần người tăng trưởng nhanh hơn
```

**Dấu hiệu nội tâm (GẦN — rõ hơn):**
```
- Nhân vật cảm thấy "bức tường" trong tu luyện mỏng đi
- Hiểu ngộ cũ đột nhiên có chiều sâu mới
- Nằm mộng thấy cảnh giới kế tiếp (mơ hồ)
- Một câu nói của người khác đột nhiên "thấm" theo nghĩa khác
```

**Dấu hiệu thiên địa (TRỰC TIẾP — không thể bỏ qua):**
```
- Mây tụ không tán trên đầu
- Linh khí xung quanh bắt đầu xoáy vào nhân vật tự nhiên
- Tiếng sấm xa xôi dù trời quang (điềm Thiên Kiếp sắp đến)
- Kim Đan/Nguyên Anh rung động không ngừng
- Nhiệt độ cơ thể tăng bất thường (Hỏa linh căn) hoặc lạnh bất thường (Băng/Thủy)
```

### 4.3 Foreshadow ngược — Cảnh giới KHÔNG thể thăng

Cũng cần foreshadow khi nhân vật **BỊ CHẶN** ở một cảnh giới:
```
- Linh lực đầy nhưng "không đi đâu được" — như nước trong bình kín
- Tu luyện bình thường nhưng không cảm thấy tiến triển
- Tâm trạng bất ổn không rõ nguyên do (tâm kết)
- Người khác cùng cảnh giới đã vượt qua — nhân vật bắt đầu tự vấn
```

---

## 5. TEMPLATES CẢNH THĂNG CẤP THEO LOẠI

### TYPE A — Thăng cấp do Tích Lũy Thuần Túy
*Khi: Nhân vật tu luyện đủ lâu, đủ tài nguyên, không có sự kiện đặc biệt*

**Đặc điểm:** Bình lặng, xứng đáng, mang cảm giác "cuối cùng"

```
NHỊP 1 — Không khí bình thường:
Bối cảnh quen thuộc (phòng tu luyện, hang động cá nhân, dưới gốc cây cũ)
Không có gì bất thường — nhân vật chỉ đang tu luyện như mọi ngày

NHỊP 2 — Cảm giác khác lạ:
"Lần này... khác." Linh lực chảy trơn tru hơn mọi khi
Nhân vật không dám động đậy, sợ làm vỡ cảm giác này

NHỊP 3 — Đối mặt với bức tường:
Chạm đến điểm giới hạn quen thuộc — nhưng lần này bức tường mỏng hơn
Ký ức về tất cả những lần thất bại trước thoáng qua

NHỊP 4 — Vượt qua:
Không phải bùng nổ mạnh mẽ — là vỡ vụn nhẹ nhàng như băng tan
Linh lực tuôn ra rồi tái kiến thành hình mới, cảnh giới mới

NHỊP 5 — Hậu đột phá:
Mở mắt — thế giới sắc nét hơn, không gian rộng hơn trong tri giác
Một câu suy nghĩ về chặng đường đã qua
Một ánh nhìn về phía trước — còn xa lắm, nhưng hắn không sợ nữa

TEXTURE BẮT BUỘC:
✓ Cảm giác thể chất trong khi đột phá (nhiệt, lạnh, đau, tê, trống rỗng)
✓ Ít nhất 1 ký ức flash ngắn về người/khoảnh khắc đã thúc đẩy hắn
✓ Thiên địa dị tượng nhẹ (không cần hoành tráng — phù hợp cảnh giới thấp)
✓ Câu kết mở ra câu hỏi/thách thức mới
```

---

### TYPE B — Thăng cấp do Ngộ Đạo / Cơ Duyên
*Khi: Nhân vật gặp vật/người/cảnh đặc biệt kích hoạt hiểu ngộ đột ngột*

**Đặc điểm:** Bất ngờ nhưng có logic, mang chiều sâu triết học

```
NHỊP 1 — Cú kích hoạt:
Một chi tiết bình thường bỗng nhiên "sáng lên" trong mắt nhân vật
(Lá rơi, tiếng nước chảy, câu nói vô tình của người qua đường)
Nhân vật dừng lại — người ngoài không hiểu có gì đặc biệt

NHỊP 2 — Trạng thái Ngộ:
Thời gian như chậm lại hoặc dừng hẳn trong cảm nhận
Linh lực tự động vận hành — nhân vật không kiểm soát
Hình ảnh/khái niệm/pháp tắc hiện ra trong ý thức như tranh vẽ

NHỊP 3 — Hiểu ngộ nội dung:
Viết ra CÁI GÌ nhân vật hiểu được (pháp tắc, kiếm ý, đạo lý)
KHÔNG giải thích quá kỹ — gợi lên, không phân tích

NHỊP 4 — Đột phá tức thì hoặc trì hoãn:
Tức thì: Linh lực cộng hưởng với hiểu ngộ → thăng cấp ngay
Trì hoãn: Hiểu ngộ quá lớn, cần thời gian "tiêu hóa" → thăng cấp sau vài chương

NHỊP 5 — Trở về thực tại:
Thế giới "bình thường" trở lại nhưng nhân vật đã không còn như cũ
Đôi khi không ai xung quanh hiểu chuyện gì vừa xảy ra

TEXTURE BẮT BUỘC:
✓ Cú kích hoạt phải được foreshadow hoặc có logic nhìn lại
✓ Trạng thái Ngộ không được kéo dài quá 300 chữ — phải súc tích
✓ Nội dung hiểu ngộ phải liên quan đến bottleneck hiện tại của nhân vật
✓ Nhân vật có phản ứng khiêm tốn hoặc kính sợ — không tự mãn
```

---

### TYPE C — Thăng cấp trong Sinh Tử
*Khi: Nhân vật gần chết, tiềm năng bùng phát*

**Đặc điểm:** Mãnh liệt, đau đớn, thường để lại hậu quả

```
NHỊP 1 — Bờ vực:
Linh lực cạn kiệt hoặc gần cạn
Thương tích nghiêm trọng — mô tả cụ thể, không hoa mỹ
Nhân vật biết rõ mình sắp thua/chết

NHỊP 2 — Điều không thể từ bỏ:
Lý do tại sao nhân vật KHÔNG thể chết ở đây
(Người cần bảo vệ, thề nguyện chưa trả, kẻ thù chưa báo thù)
Đây là nhịp QUAN TRỌNG nhất — phải thật và nặng

NHỊP 3 — Bùng phát:
Tiềm năng ẩn giấu hoặc linh lực dự trữ sâu nhất bị kích hoạt
Đau đớn cực độ — cơ thể không được tạo ra cho điều này
Thường đi kèm thương tổn dư âm (cần hồi phục sau)

NHỊP 4 — Vượt qua cảnh giới trong khủng hoảng:
Cảnh giới mới không được kiểm soát hoàn toàn
Sức mạnh tăng nhưng không ổn định
Kết quả thường là thắng trận nhưng ngã xuống ngay sau

NHỊP 5 — Hậu quả:
Thức dậy — kiệt sức tột độ, có thể bị thương nặng
Cảnh giới mới đã ổn định nhưng có "vết nứt" hoặc cần thời gian bình phục
Nhân vật suy nghĩ: "Mình có thực sự kiểm soát được sức mạnh này không?"

TEXTURE BẮT BUỘC:
✓ Thương tổn phải thực sự — không hồi phục ngay lập tức
✓ Bùng phát có GIÁ PHẢI TRẢ rõ ràng (tuổi thọ, linh căn, tâm thần)
✓ Nhân vật sau đó KHÔNG tự mãn với cảnh giới mới — biết mình được quá may
✓ Ít nhất 1 người chứng kiến và phản ứng
```

---

### TYPE D — Thăng cấp Cưỡng Ép / Không Tự Nguyện
*Khi: Dùng đan dược cấm, bị cưỡng bức nâng cấp, trải qua biến đổi cơ thể*

**Đặc điểm:** Nguy hiểm, có mâu thuẫn nội tâm, thường dẫn đến subplot

```
NHỊP 1 — Quyết định hoặc bị ép buộc:
Nhân vật hoặc chủ động dùng phương pháp nguy hiểm (đan dược cấm, cưỡng ép đột phá)
Hoặc bị hoàn cảnh/người khác ép vào tình huống này

NHỊP 2 — Cơ thể phản loạn:
Năng lượng không chịu phục tùng — như thú dữ bị nhốt
Kinh mạch có thể bị xé hoặc cơ thể bốc khói, ra máu

NHỊP 3 — Cuộc chiến nội tâm:
Đây là thăng cấp với ý thức rõ ràng — nhân vật phải dùng ý chí kiểm soát
Thường có hình ảnh ẩn dụ (đối mặt bóng tối bản thân, ngọn lửa thiêu đốt)

NHỊP 4 — Kết quả không hoàn hảo:
Thăng cấp thành công nhưng nền tảng không vững
Hoặc: Nền tảng vững nhưng có ẩn họa (tạp khí, thiên kiếp sớm hơn)

NHỊP 5 — Mối lo mới:
Cảnh giới mới có nhưng mang theo vấn đề chưa giải quyết
Tạo ra subplot dài hơi: "Làm sao thanh lọc nền tảng?"

TEXTURE BẮT BUỘC:
✓ Người biết về việc này phải CAN NGĂN trước — tạo nặng nề cho quyết định
✓ Hậu quả âm ỉ PHẢI xuất hiện ít nhất 3-5 chương sau
✓ Không được để nhân vật "ổn hoàn toàn" sau loại thăng cấp này quá sớm
```

---

### TYPE E — Thăng cấp Nhỏ (Tầng trong cảnh giới)
*Khi: Tiến từ Sơ kỳ → Trung kỳ, hoặc Luyện Khí tầng 3 → tầng 4*

**Đặc điểm:** Ngắn gọn, không cần cảnh hoành tráng, nhưng PHẢI được mention

```
FORMAT NGẮN (100-200 chữ):

"Đêm đó hắn ngồi tu luyện đến canh tư.
Khi linh lực chạm đến vách ngăn quen thuộc, hắn không cưỡng bức — chỉ nhẹ nhàng ép sát vào, kiên nhẫn như nước mài đá.
Lần này... nó mở ra.
Không rầm rộ. Không thiên địa biến sắc. Chỉ là một tiếng tách khẽ khàng trong đan điền, rồi linh lực tuôn ra chậm rãi vào không gian mới.
Hắn mở mắt nhìn bàn tay — linh lực bây giờ đặc hơn một chút, sắc nét hơn một chút.
Luyện Khí Kỳ tầng năm.
Còn bốn tầng nữa."

TEXTURE BẮT BUỘC:
✓ Phải được mention, dù ngắn — không được bỏ qua
✓ Câu cuối thường nhìn về phía trước — tạo cảm giác hành trình còn dài
✓ Không cần thiên địa dị tượng — thăng cấp nhỏ thì dấu hiệu nhỏ
```

---

## 6. BOTTLENECK & TRẮC TRỞ

### 6.1 Tại sao Bottleneck quan trọng

Bottleneck (bức tường tu luyện) là thứ làm cho thăng cấp có **trọng lượng**. Không có bottleneck = thăng cấp vô nghĩa. Nhưng bottleneck cũng phải được **giải quyết hợp lý**, không phải "đột nhiên biến mất."

### 6.2 Phân loại Bottleneck

**Bottleneck Kỹ Thuật** — Thiếu phương pháp/tài nguyên
```
Vấn đề: Công pháp hiện tại không đủ để đột phá tiếp
Giải pháp hợp lý: Tìm công pháp cao cấp hơn, nhận truyền thừa, mua/đánh cắp/tìm được
Timeline: Có thể giải quyết trong 5-15 chương
```

**Bottleneck Tài Nguyên** — Thiếu linh thạch/đan dược
```
Vấn đề: Cần tài nguyên cấp cao mà không có
Giải pháp hợp lý: Nhiệm vụ kiếm tiền, tranh đoạt, may mắn gặp cơ duyên
Timeline: Có thể giải quyết trong 3-10 chương
```

**Bottleneck Nền Tảng** — Nền móng không vững
```
Vấn đề: Thăng cấp quá nhanh trước đây, nền tảng rỗng
Giải pháp hợp lý: Phải củng cố lại, không có lối tắt
Timeline: Dài nhất — 20-50 chương (tạo arc riêng)
```

**Bottleneck Tâm Kết** — Rào cản tâm lý/cảm xúc
```
Vấn đề: Một cảm xúc/ký ức/sợ hãi ngăn cản đột phá
Giải pháp hợp lý: Phải đối mặt và giải quyết cảm xúc đó (không thể ép linh lực vượt qua)
Timeline: Gắn liền với arc cảm xúc — thường giải quyết cùng một sự kiện plot lớn
Đây là loại GIÀU CẢM XÚC NHẤT — ưu tiên khi muốn depth
```

**Bottleneck Thiên Mệnh** — Bị thiên đạo/vận mệnh ngăn cản
```
Vấn đề: Nhân vật đang "đi ngược thiên đạo" hoặc cảnh giới vượt quá vận mệnh
Giải pháp hợp lý: Thay đổi vận mệnh (arc lớn), nhận được thiên cơ, hoặc hy sinh gì đó
Timeline: Arc chính của toàn bộ truyện — không giải quyết nhanh
```

### 6.3 Viết cảnh "Nhân vật Thất Bại Đột Phá"

Đây là cảnh **thường bị bỏ qua nhưng cực kỳ quan trọng** — nó cho thấy con đường tu tiên không dễ dàng.

```
TEMPLATE THẤT BẠI ĐỘT PHÁ (200-400 chữ):

Hắn ngồi xuống lần thứ [X] trong tháng này.
Hít thở. Linh lực vận hành theo quy trình quen thuộc.
Chạm đến vách ngăn — đây rồi.
Hắn dồn ý chí, đẩy lên—

Phản lực.

Linh lực trào ngược, kinh mạch đau nhói. Hắn nghiến răng không để rên, từ từ thu linh lực về, hóa giải áp lực.
Một lúc sau hắn mở mắt.
Thất bại. Lần [X].
[Cảm xúc phản ứng — tức giận? chấp nhận? tự vấn?]
[Suy nghĩ về nguyên nhân — tài nguyên? phương pháp? nội tâm?]
[Quyết định tiếp theo — tiếp tục cách này? thay đổi phương pháp?]

TEXTURE BẮT BUỘC:
✓ Thất bại phải có CẢM GIÁC VẬT LÝ rõ ràng
✓ Phản ứng cảm xúc phải THẬT — không quá bình thản, không quá tuyệt vọng
✓ Phải có ít nhất 1 suy nghĩ tích cực hoặc insight từ lần thất bại này
✓ Câu kết phải có hướng về phía trước
```

---

## 7. PROGRESSION TRACKER

### 7.1 Master Progression Chart

Agent PHẢI duy trì bảng này cho toàn bộ truyện từ đầu:

```markdown
## PROGRESSION CHART — [Tên truyện]

| Chương | Cảnh giới | Tầng | Sự kiện Tu Luyện | Nhiên liệu Tích Lũy | Bottleneck |
|--------|-----------|------|-----------------|---------------------|------------|
| 1-5    | Luyện Khí | 1    | Mới bắt đầu     | Linh thạch cha để lại | Kinh mạch yếu |
| 10     | Luyện Khí | 3    | Thăng TYPE E    | +Trúc Cơ Đan x1     | — |
| 18     | Luyện Khí | 5    | Thăng TYPE A    | Tu luyện Linh Mạch   | — |
| 25     | Luyện Khí | 7    | Cố thủ (Type D fail) | Đan dược cưỡng ép | Nền tảng rạn |
| 35     | Luyện Khí | 9    | Thăng TYPE C    | Sinh tử trận đấu    | Tâm kết: cha |
| 40     | Trúc Cơ   | Sơ   | Đột Phá lớn     | Giải tâm kết        | Nền tảng rạn |
...
```

### 7.2 Spacing Rules — Khoảng cách giữa các thăng cấp

```yaml
THĂNG CẤP NHỎ (tầng trong cảnh giới thấp):
  min_chapters_between: 5
  max_chapters_between: 15
  note: "Quá dày = mất ý nghĩa. Quá thưa = độc giả quên mất hành trình"

THĂNG CẤP LỚN (vào cảnh giới mới):
  min_chapters_between: 30
  max_chapters_between: 80
  note: "Mỗi cảnh giới lớn nên là 1 giai đoạn cuộc đời rõ ràng"

BOTTLENECK DURATION:
  min_chapters: 10
  max_chapters: 40
  note: "Bottleneck quá ngắn = không có sức nặng. Quá dài = độc giả nản"

SAU TYPE C/D BREAKTHROUGH:
  mandatory_recovery_chapters: 3-5
  note: "Nhân vật PHẢI có thời gian phục hồi và tiêu hóa cảnh giới mới"
```

Thứ tự ưu tiên: canon/`PROJECT_DNA.md` → spacing rules 7.2 → Luật Hành Trình 7.3 → density tham chiếu 10 chương ở mục 2.1. Không dùng density 10 chương để cưỡng ép breakthrough.

### 7.3 Luật Hành Trình Tu Luyện Cho Plot Weaver

Đây là source of truth cho các luật progression cấp outline. `sub_agents/mong_yem/SOUL.md` chỉ gọi sang mục này, không định nghĩa lại.

Các luật dưới đây không thay thế canon riêng của truyện. Nếu `PROJECT_DNA.md`, database canon, hoặc Author Style đã khóa hệ cảnh giới riêng thì dùng hệ đó. Nếu chưa khóa, dùng khung cảnh giới chuẩn tại `system/Xianxia/Xianxia_consistency_rules.md`.

#### Luật 1 — Tiết Tấu Thăng Cảnh

Nhịp dưới đây là nhịp **cột mốc tu luyện quan trọng**: breakthrough, blocked breakthrough, mở bottleneck mới, gặt fuel lớn, lĩnh ngộ kỹ thuật mới, hoặc đổi trạng thái Cultivation Clock. Realm-up lớn vẫn phải tuân thủ spacing rules ở mục 7.2.

| Phong vị | Nhịp cột mốc tu luyện |
|---|---|
| Sảng văn | Mỗi 8-12 chương |
| Trung dung | Mỗi 15-25 chương |
| Trầm bút | Mỗi 30-50 chương |

Nếu lệch nhịp, outline hoặc memory phải ghi lý do: arc đang điều tra, hồi phục sau đại chiến, nhân vật bị phong cấm tu vi, hoặc genre phụ đang tạm chiếm trọng tâm.

#### Luật 2 — Không Lặp Loại Cơ Duyên

Hai breakthrough liên tiếp không được dùng cùng một loại cơ duyên, trừ khi lần sau là hậu quả trực tiếp của lần trước và outline ghi rõ biến thể.

| Loại | Mô tả | Mapping với type progression |
|---|---|---|
| Chiến Kiếp | Đột phá trong sinh tử giao tranh, bị dồn tới tuyệt cảnh | Type C |
| Cảm Ngộ | Thiền định, lĩnh hội đạo lý, ý cảnh mở đường | Type B |
| Tích Lũy | Linh thạch, đan dược, linh địa, công phu ngày tháng đủ ngưỡng | Type A / Type E |
| Cơ Duyên | Bí cảnh, di vật tiền bối, truyền thừa, thiên địa linh vật | Type B |
| Chấp Niệm | Biến cố cảm xúc, lời thề, thù hận, mất mát, tâm kết | Emotional catalyst |
| Song Hợp | Kết hợp hai loại trên | Chỉ dùng cho mốc lớn |

#### Luật 3 — Ngưỡng Thất Bại Trước Đại Cảnh Giới

Trước một realm-up lớn, phải có ít nhất một beat `blocked` hoặc một lần thử đột phá thất bại được ghi trong outline/memory:

- thất bại vì thiếu linh lực, tài nguyên, tâm cảnh, ý cảnh, căn cơ, hoặc bị nhiễu loạn từ bên ngoài
- phản ứng tâm lý sau thất bại: nhẫn chịu, dao động, ngộ ra, hoặc đổi chiến lược
- fuel/bottleneck được cập nhật sau thất bại

Với truyện sảng nhanh, beat này có thể ngắn nhưng không được biến mất.

#### Luật 4 — Chương Tròn Phải Có Trọng Tâm

Các mốc chương 50, 100, 150, 200... nên trùng hoặc nằm trong vòng ±3 chương với một trong các điểm sau:

- breakthrough hoặc blocked breakthrough quan trọng
- kết thúc đại arc với trận chiến/quyết định lớn
- biến cố không thể đảo ngược làm đổi Cultivation Clock, quan hệ thế lực, tài nguyên, hoặc thiên mệnh

Nếu chapter target nhỏ hơn 50, áp dụng luật này cho midpoint và final arc climax.

#### Luật 5 — Mọi Đột Phá Có Giá

Mỗi breakthrough hoặc forced breakthrough phải ghi giá trong `fuel_delta` hoặc `Breakthrough Event`:

- hữu hình: linh thạch, đan dược, linh thảo, thọ nguyên, huyết khí
- thời gian: số ngày/tháng/năm bế quan hoặc hồi phục
- thể phách: kiệt sức, hôn mê, kinh mạch tổn thương, căn cơ rạn
- vô hình: quan hệ rạn nứt, niềm tin sụp đổ, từ bỏ một thứ không lấy lại được

#### Luật 6 — Mỗi Đại Cảnh Giới Có Thiên Sắc

Mỗi major realm hoặc major power-state phải có `thien_sac`: trạng thái cảm xúc, góc nhìn thiên hạ, và cách nhân vật nhìn lại chính mình sau khi bước sang nấc mới.

Không định nghĩa lại bảng cảnh giới trong outline. Lấy cảnh giới từ `PROJECT_DNA.md`/database; nếu chưa có canon riêng thì dùng khung chuẩn trong `system/Xianxia/Xianxia_consistency_rules.md`.

#### Luật 7 — Sau Đột Phá Phải Có Nhân Chứng Hoặc Hậu Chấn

Sau mỗi breakthrough, outline phải ghi rõ ai biết, ai không biết, phản ứng của ít nhất một nhân vật hoặc thế lực cụ thể, và hậu quả có cần cập nhật memory/database hay không.

Không viết mơ hồ kiểu "mọi người đều kinh ngạc". Phải có tên người, nhóm, tông môn, hoặc cơ chế thiên địa phản ứng.

#### Luật 8 — Bí cảnh/di tích/tài nguyên phải đổi trục tu luyện

Bí cảnh, di tích, săn tài nguyên, luyện pháp bảo hoặc thử thách đạo tâm chỉ được tính là `cultivation_journey_beat` khi nó tạo một trong các thay đổi sau:

- thêm hoặc mất `hard_resources`, `soft_resources`, hoặc `emotional_catalysts`
- mở, làm mỏng, làm nặng hoặc đổi hướng `active_bottleneck`
- làm thay đổi `current_state`, `years_in_current_realm`, `pace_vs_benchmark`, hoặc `next_breakthrough`
- gây thương tích căn cơ, phản phệ pháp lực, nợ nhân quả, mất thọ nguyên hoặc nhu cầu ổn cố
- ép nhân vật đổi pháp môn, đổi nơi tu luyện, đổi mục tiêu tiểu cảnh hoặc chấp nhận thất bại

Nếu một chương chỉ viết "vào bí cảnh", "lấy truyền thừa", "thu tài nguyên" nhưng không đổi bất kỳ mục nào ở trên, đó là texture rỗng, không phải hành trình tu luyện.

### 7.4 Cultivation Density — Mật độ mention tu luyện

Để tu luyện cảm giác "chạy ngầm" xuyên suốt truyện:

```
HÀNG NGÀY (không cần cảnh riêng — chỉ cần 1-2 câu):
"Sáng sớm hắn vẫn dậy canh ba để tu luyện — thói quen bảy năm không đổi."
"Tranh thủ lúc chờ đợi, hắn khẽ vận công, dẫn linh khí lưu chuyển một vòng."

HÀNG TUẦN (50-100 chữ, mention trong chương):
Thêm chi tiết nhỏ về tiến triển, khó khăn gặp phải, hoặc điều đang thử nghiệm.

HÀNG THÁNG (100-300 chữ, có thể là cảnh nhỏ):
Kiểm tra trạng thái, nhận ra mình đã tiến bộ bao nhiêu, đặt mục tiêu tiếp theo.

MỖI ARC (Cảnh thăng cấp đầy đủ):
Một trong 5 TYPE ở trên, với đầy đủ 5 nhịp.
```

**Mật độ quá trình nhìn thấy được:** Trong một cụm 3 chương liên tiếp, phải có ít nhất 1 cảnh hoặc đoạn ngắn có đủ ba phần:

1. **Hành động tu luyện:** dẫn khí, vận chuyển chu thiên, luyện hóa, đả tọa, xung kích bình cảnh, ổn cố, tôi luyện pháp bảo/công pháp.
2. **Nội tại phản ứng:** kinh mạch, đan điền/khí hải, thức hải/thần thức, đạo tâm/tâm ma, chân nguyên/linh lực đổi trạng thái.
3. **Kết quả cụ thể:** tu vi tiến/lùi, bình cảnh mỏng/dày hơn, tài nguyên hao hụt, căn cơ tổn thương, cần đổi pháp môn, hoặc phải ghi thất bại.

"Không đột phá", "chưa khóa tiểu cảnh", "tu luyện một lúc" không được tính nếu thiếu quá trình. Slow/ultra slow không có nghĩa là ít tu luyện; nó nghĩa là nhiều tích lũy, nhiều bế tắc, nhiều ổn cố và nhiều năm tháng hơn trước khi đổi cảnh giới.

**Độ sâu quá trình tu luyện:** Khi chương đã mở cảnh tu luyện, luyện hóa, bế quan, xung kích bình cảnh hoặc đột phá, đoạn đó phải có ít nhất 4/6 lớp:

1. **Hành động cụ thể:** đả tọa, dẫn khí, vận chuyển chu thiên, luyện hóa, xung kích bình cảnh, ổn cố, tôi luyện pháp bảo/công pháp.
2. **Cảm giác thân thể:** đau, tê, nóng, lạnh, nghẹn, rạn, chảy ngược, kiệt sức, huyết khí/xương/hơi thở đổi khác.
3. **Nội giới phản ứng:** kinh mạch, đan điền/khí hải, thức hải/thần thức, đạo tâm/tâm ma, chân nguyên/linh lực/dược lực biến đổi.
4. **Nhiên liệu/tích lũy:** linh thạch, đan dược, dược lực, năm tháng bế quan, tài nguyên bí cảnh, chiến đấu tôi luyện, cảm xúc hoặc ý chí làm chất xúc tác.
5. **Chướng ngại/thất bại:** bình cảnh, thiếu tài nguyên, tâm cảnh chưa đủ, phản phệ, tẩu hỏa, công pháp chưa thông, thử phá cảnh thất bại.
6. **Kết quả/hậu quả:** tu vi tiến/lùi, bình cảnh mỏng/dày hơn, căn cơ rạn, pháp bảo hỏng, phải hồi phục/ổn cố, hoặc đổi chiến lược tu luyện.

Bế quan không được tua thành "ba tháng sau tu vi tăng". Nếu bỏ qua thời gian, phải ghi cái gì đã được tích lũy, cái gì nghẽn lại, thân thể/nội giới đổi ra sao, và sau khi xuất quan nhân vật phải trả cái giá gì.

---

## 8. TÍCH HỢP VÀO ARC TRUYỆN

### 8.1 Cấu trúc Arc Lý Tưởng — 4 pha

```
PHA 1 — THIẾT LẬP (20% arc):
- Nhân vật ở cảnh giới X, gặp thử thách vượt quá khả năng
- Bottleneck hiện tại được giới thiệu
- Tài nguyên & cơ duyên bắt đầu tích lũy

PHA 2 — NỖ LỰC (40% arc):
- Tu luyện chăm chỉ với nhiều cảnh Micro/Meso
- Gặp thất bại đột phá ít nhất 1 lần
- Thăng vài tầng nhỏ (TYPE E)
- Bottleneck trở nên cấp bách hơn

PHA 3 — KHỦNG HOẢNG (20% arc):
- Sự kiện buộc nhân vật phải đột phá ngay bây giờ
- Điều kiện không lý tưởng (thường là sinh tử, áp lực cực độ)
- Bottleneck được giải quyết qua sự kiện cảm xúc/plot

PHA 4 — BREAKTHROUGH & AFTERMATH (20% arc):
- Cảnh thăng cấp lớn (TYPE A, B, hoặc C)
- Ổn định cảnh giới mới
- Nhìn lại arc, nhìn về arc tiếp theo
- Giới thiệu bottleneck MỚI của cảnh giới kế tiếp
```

### 8.2 Liên kết Tu Luyện với Plot Events

Mọi sự kiện plot lớn đều nên có **hàm ý tu luyện**:

| Sự kiện Plot | Liên kết Tu Luyện |
|-------------|------------------|
| Mất người thân | Tâm kết → bottleneck / hoặc đau đớn → catalyst |
| Kết nghĩa huynh đệ | Học được phương pháp mới / thêm động lực |
| Bị phản bội | Tâm kết → cần giải quyết để tiếp tục |
| Vào tông môn | Tiếp cận tài nguyên mới, công pháp cấp cao |
| Chiến thắng kẻ thù lớn | Hiểu ngộ từ chiến đấu, fuel tích lũy |
| Lạc vào cấm địa | Cơ duyên thiên hạ hữu, linh khí dày đặc |
| Gặp bậc tiền bối | Truyền thừa, chỉ điểm, thay đổi phương hướng |

### 8.3 Không được để Tu Luyện Cô Lập với Cảm Xúc

Sai lầm lớn nhất: Tu luyện chỉ là "system" — con số tăng, không có ý nghĩa con người.

**Mỗi cột mốc tu luyện lớn phải trả lời 1 trong các câu hỏi:**
- Điều này thay đổi gì trong quan hệ của nhân vật?
- Nhân vật gần hơn hay xa hơn điều họ thực sự muốn?
- Cảnh giới mới mang đến sức mạnh — nhưng đánh mất gì?
- Ai sẽ phản ứng khác với nhân vật sau thay đổi này?

---

## 9. QUALITY CHECK

### 9.1 Checklist Agent — Trước khi viết chương có thăng cấp

```
KIỂM TRA CHUẨN BỊ:
□ Cultivation Clock đã được update lên chương trước nhất?
□ Tuổi/thời gian tu luyện hiện tại và `years_in_current_realm` đã rõ?
□ Nếu dùng benchmark Nhĩ Căn/Tiên Nghịch, đã ghi nhanh/chậm hơn mốc tuổi vì sao?
□ Đã có ít nhất 2 loại nhiên liệu được tích lũy trong các chương trước?
□ Đã foreshadow ít nhất 3 lần (3-1-1 rule)?
□ Bottleneck hiện tại đã được giới thiệu đủ sớm?
□ Khoảng cách từ lần thăng cấp trước có đủ (spacing rules)?
□ Loại cơ duyên có khác breakthrough liền trước hoặc đã giải thích biến thể?
□ Nếu là realm-up lớn, đã có beat blocked/thất bại trước đó?

KIỂM TRA KHI VIẾT:
□ Đã xác định TYPE thăng cấp phù hợp với hoàn cảnh?
□ 5 nhịp của TYPE đó đã đủ?
□ Cảm giác thể chất trong quá trình đột phá?
□ Ít nhất 1 kết nối cảm xúc (ký ức, người thân, thề nguyện)?
□ Thiên địa dị tượng phù hợp cảnh giới (không quá to, không quá nhỏ)?
□ Thiên sắc của cảnh giới/trạng thái mới đã hiện ra qua cảm giác và góc nhìn?
□ Có nhân chứng hoặc hậu chấn cụ thể sau đột phá?
□ Câu kết có hướng về phía trước?

KIỂM TRA SAU KHI VIẾT:
□ Update Cultivation Clock ngay sau chương này?
□ Ghi nhận nhiên liệu đã tiêu thụ?
□ Ghi tuổi hoặc thời gian đã trôi qua sau bế quan, bí cảnh, hồi phục hoặc đột phá?
□ Xác định bottleneck mới cho cảnh giới tiếp theo?
□ Plan foreshadow cho lần thăng cấp tiếp theo (ít nhất biết 3 lần foreshadow sẽ đặt ở đâu)?
```

### 9.2 Checklist Arc — Sau khi hoàn thành một arc lớn

```
NHÌN LẠI ARC:
□ Progression Chart đã đầy đủ và nhất quán?
□ Tỷ lệ thăng cấp Type phân bổ đa dạng (không toàn TYPE A hoặc toàn TYPE C)?
□ Ít nhất 1 cảnh thất bại đột phá trong arc?
□ Ít nhất 1 Bottleneck được giải quyết?
□ Cultivation density đủ (mention tu luyện đủ thường xuyên)?
□ Tu luyện được liên kết với ít nhất 2 sự kiện plot chính?
□ Mỗi thăng cấp lớn có kết nối cảm xúc?

NHÌN VỀ ARC TIẾP THEO:
□ Bottleneck mới của cảnh giới tiếp theo đã được gieo hạt?
□ Tài nguyên/cơ duyên cần thiết cho arc tiếp theo đã có hướng xuất hiện?
□ Nhân vật có mục tiêu tu luyện rõ ràng sang arc tiếp theo?
```

---

## PHỤ LỤC A — Ví Dụ Cultivation Clock Đầy Đủ

```yaml
# CULTIVATION CLOCK — Lâm Vô Thương
# Cập nhật lần cuối: Chương 67

current_state:
  realm: "Kết Đan Kỳ"
  sub_level: "Sơ kỳ"
  dan_quality: "Hạ phẩm Thanh Đan — nứt một góc nhỏ (do TYPE D Ch.52)"
  age_in_story: "19 tuổi"
  cultivation_years: "4 năm 3 tháng"

recent_progression_history:
  - "Ch.20: Luyện Khí → Trúc Cơ (TYPE B — ngộ đạo từ trận mưa lớn)"
  - "Ch.38: Trúc Cơ Trung → Hậu (TYPE A — tích lũy thuần túy)"
  - "Ch.52: Trúc Cơ → Kết Đan (TYPE D — cưỡng ép, đan có vết nứt)"

fuel_accumulated_since_last_breakthrough:
  hard:
    - "~200 trung phẩm linh thạch (Chương 53-67)"
    - "Thanh Linh Đan x2 dùng để ổn định đan (Ch.55, 60)"
  soft:
    - "Hiểu ngộ từ 3 trận (Ch.58, 62, 66)"
    - "Đọc xong Kiếm Kinh thượng quyển (Ch.64)"
  emotional:
    - "Gặp lại cô nương Lục Tuyết Nhi (Ch.63) — cảm xúc phức tạp"

current_bottleneck:
  name: "Thanh Đan Bất Hoàn"
  description: "Kim Đan có vết nứt do đột phá cưỡng ép — linh lực bị rò rỉ 10-15%, không thể vận công toàn lực"
  introduced: "Ch.52"
  resolution_path: "Cần Bổ Đan Đan thượng phẩm HOẶC thiền định trong Linh Mạch cấp cao ít nhất 30 ngày"
  urgency: "Trung — chưa cản trở sinh tử nhưng cản trở đột phá tiếp theo"

next_breakthrough:
  target: "Kết Đan Trung kỳ"
  required_fuel:
    - "[BẮT BUỘC] Giải quyết Thanh Đan Bất Hoàn trước"
    - "Thêm ~500 trung phẩm hoặc 50 thượng phẩm linh thạch"
    - "1 lần ngộ đạo về Kiếm Đạo (đọc xong Kiếm Kinh hạ quyển?)"
  foreshadow_done: 1  # cần thêm 2 lần nữa
  estimated_chapters: "~25-35 chương"
  recommended_type: "TYPE A hoặc TYPE B (TYPE C đã dùng lần trước)"

side_notes:
  - "Lục Tuyết Nhi biết về vết nứt đan — có thể subplot giúp đỡ/chữa trị"
  - "Thiên Kiếm Tông có Linh Mạch cấp 3 — nhân vật chưa có quyền vào"
  - "Kiếm Kinh hạ quyển đang ở tay Tông Chủ — cần cơ hội tiếp cận"
```

---

## PHỤ LỤC B — Từ Điển Cảm Giác Thể Chất Theo Cảnh Giới

```
LUYỆN KHÍ → TRÚC CƠ:
Cảm giác: "Như hàng nghìn mảnh thủy tinh nhỏ trong huyết mạch đột nhiên sắp xếp thành hình — đau nhói rồi tê liệt rồi... trống rỗng. Và trong trống rỗng đó có gì đó vững chắc hơn trước rất nhiều."

TRÚC CƠ → KẾT ĐAN:
Cảm giác: "Linh lực không còn là nước chảy — nó cô đặc lại, xoáy tròn trong đan điền, nóng như than hồng. Rồi tất cả nén lại thành một điểm — đau đến mức hắn không còn cảm giác nữa. Rồi nổ ra. Và trong đó có vật gì cứng, tròn, ấm áp — Kim Đan đã kết thành."

KẾT ĐAN → NGUYÊN ANH:
Cảm giác: "Kim Đan vỡ tan — hắn tưởng mình chết đến nơi. Nhưng từ trong đống mảnh vỡ đó, có thứ gì đó đứng dậy. Không phải thân xác hắn — mà là MỘT BẢN SAO của hắn, trong suốt, ngồi trong đan điền, mở mắt nhìn hắn lần đầu tiên."

NGUYÊN ANH → HÓA THẦN:
Cảm giác: "Ranh giới giữa bản thân và thiên địa... mờ đi. Hắn vẫn là hắn. Nhưng đồng thời hắn cảm nhận được gió thổi ở phía đông núi, cá bơi dưới hồ sâu trăm trượng, tiếng bước chân người đi trong thung lũng. Không phải nghe — mà là BIẾT."
```

---

*Module này là BỔ SUNG bắt buộc cho Tu Tiên Texture Floor v3.00.*
*Agent sáng tác phải đọc cả hai tài liệu trước khi bắt đầu chương mới.*
*Cultivation Clock phải được khởi tạo từ Chương 1 và cập nhật xuyên suốt.*
