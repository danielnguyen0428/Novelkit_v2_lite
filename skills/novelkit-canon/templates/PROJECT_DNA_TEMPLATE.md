# PROJECT_DNA.md — [Tên tác phẩm]
---
generated: [YYYY-MM-DD]
genre: [xianxia | urban | romance | time_travel | sci_fi | meta_genre | hybrid]
genre_primary: [genre chính nếu hybrid, bỏ trống nếu đơn genre]
genre_secondary: [genre phụ nếu hybrid, bỏ trống nếu đơn genre]
hybrid_ratio: [70-30 | 60-40 | 50-50]   # Chỉ dùng khi genre = hybrid
style_model: [MÃ_ĐẠI_THẦN]
style_blend: [MÃ1][%]-[MÃ2][%]   # Tùy chọn, nếu pha trộn
worldbuilding_guide: [MÃ_GUIDE]   # Xianxia: nếu mã có _Worldbuilding_Complete.md thì ghi luôn mã đó
sub_agents_squad: [sub_agents | sub_agents_do_thi | sub_agents_ngon_tinh | sub_agents_xuyen_khong | sub_agents_khoa_huyen | sub_agents_he_thong]
sub_agents_squad_secondary: [squad phụ nếu hybrid, bỏ trống nếu đơn genre]
canon_pack: [system/Xianxia | system/Urban | system/Romance | system/Time Travel | system/Sci-fi | system/Meta Genre]
canon_pack_secondary: [canon pack phụ nếu hybrid, bỏ trống nếu đơn genre]
status: draft
target_chapters: 120
arc_count: 8
target_words_per_chapter: 2500
cultivation_speed: [fast | slow | ultra_slow]   # Xianxia: nhanh/chậm/siêu chậm, truyền tới Plot Weaver/Prose Writer/Sync
cultivation_age_benchmarks: []                  # Xianxia: vd ["51 tuổi -> Trúc Cơ hậu kỳ"], dùng làm neo pacing
---

> **File này là SINGLE SOURCE OF TRUTH cho toàn bộ hệ thống Agentic AI.**
> Mọi Sub-Agent (World Builder → Character Architect → Plot Weaver → Prose Writer → Quality Auditor)
> ĐỌC file này TRƯỚC KHI bắt đầu bất kỳ tác vụ nào.

---

## I. HẠT GIỐNG (Seed)

- **Tên tác phẩm:**
- **Logline (1 câu pitch):**
- **Logline TEST:** _[Nhân vật] phải [hành động] trước khi [stakes], nhưng [trở ngại lớn nhất]._
- **Thể loại chính:**
- **Thể loại phụ:** _(nếu hybrid, vd: Đô Thị + Tu Chân)_
- **Đối tượng độc giả:** _(nam/nữ, lứa tuổi, sở thích)_
- **USP (Unique Selling Point):** _(Điều gì khiến truyện này KHÁC mọi truyện cùng thể loại?)_
- **Ước tính tổng số chương:** _(khớp với `target_chapters` trong frontmatter)_
- **Ước tính số Arc:** _(khớp với `arc_count` trong frontmatter)_

---

## II. THỂ LOẠI & ROUTING

> Chọn **MỘT** thể loại chính. Hệ thống sẽ tự động route tới squad và canon pack tương ứng.
> Nếu là **Hybrid**, chọn thể loại chính + thể loại phụ ở bảng dưới.

| # | Thể Loại | Squad | Canon Pack | Số Đại Thần | Chọn |
|---|---|---|---|---|---|
| 1 | **Tiên Hiệp** (Xianxia) | `sub_agents/` | `system/Xianxia/` | 10 | ☐ |
| 2 | **Đô Thị** (Urban) | `sub_agents_do_thi/` | `system/Urban/` | 5 | ☐ |
| 3 | **Ngôn Tình** (Romance) | `sub_agents_ngon_tinh/` | `system/Romance/` | 5 | ☐ |
| 4 | **Xuyên Không** (Time Travel / Lịch Sử) | `sub_agents_xuyen_khong/` | `system/Time Travel/` | 10 | ☐ |
| 5 | **Khoa Huyễn** (Sci-Fi) | `sub_agents_khoa_huyen/` | `system/Sci-fi/` | 5 | ☐ |
| 6 | **Hệ Thống** (Meta Genre / System) | `sub_agents_he_thong/` | `system/Meta Genre/` | 5 | ☐ |
| 7 | **🔀 Hybrid** (Pha Trộn Thể Loại) | _xem bên dưới_ | _xem bên dưới_ | _tùy combo_ | ☐ |

### Hybrid Genre — Pha Trộn Thể Loại

> Nếu không phải Hybrid, bỏ qua phần này. Chi tiết routing rules, combo table và vocabulary rules xem `templates/HYBRID_GENRE_GUIDE.md`.

**Có phải Hybrid không?** ☐ Có / ☐ Không

#### Cấu Hình Hybrid

- **Thể loại CHÍNH (Primary):** _(genre chiếm tỷ trọng lớn nhất)_
- **Thể loại PHỤ (Secondary):** _(genre pha trộn vào)_
- **Tỷ lệ pha trộn:** _(70-30 / 60-40 / 50-50)_

#### Hệ Thống Sức Mạnh Hybrid — Quy Tắc Tương Tác

- **Hai hệ thống cùng tồn tại?** _(vd: tu luyện + công nghệ)_
- **Hệ thống nào mạnh hơn?** _(hay cân bằng?)_
- **Xung đột giữa 2 hệ thống:** _(vd: linh khí làm nhiễu công nghệ?)_
- **MC dùng hệ thống nào?** _(một / cả hai / chuyển đổi?)_
- **Giới hạn cross-system:** _(không thể vừa tu luyện vừa dùng công nghệ cùng lúc?)_

---

## III. PHONG CÁCH ĐẠI THẦN

> Chọn **MỘT** Đại Thần làm phong cách chính. Có thể pha trộn tối đa 2 Đại Thần.
> Format pha trộn: `MÃ1[%]-MÃ2[%]` (vd: `NC70-TD30`)

### A. Bảng Đại Thần Toàn Hệ Thống (40 Profiles)

> Xem catalog đầy đủ 40 Đại Thần (mã, DNA cốt lõi, file) tại `templates/AUTHOR_STYLE_CATALOG.md`.
> Dưới đây chỉ liệt kê mã Xianxia để tham chiếu nhanh:
> `NC` Nhĩ Căn | `TD` Tiêu Đỉnh | `CD` Thần Đông | `VN` Vong Ngữ | `TH` Ngã Cật Tây Hồng Thị | `OT` Mực Thích Lặn Nước | `TT` Thiên Tàm Thổ Đậu | `DG` Đường Gia Tam Thiếu | `PL` Phong Lăng Thiên Hạ | `PT` Phương Tưởng

### B. Lựa Chọn Phong Cách

- **Phong cách chính (Mã):**
- **Phong cách phụ (Mã):** _(tùy chọn)_
- **Tỷ lệ pha trộn:** _(vd: NC70-TD30)_
- **Worldbuilding guide (Mã):** _(Xianxia: nếu mã Đại Thần có `_Worldbuilding_Complete.md`, ghi luôn mã đó; nếu bỏ trống, hệ thống tự resolve theo `style_model`)_
- **Worldbuilding guide (File):** _(đường dẫn file đạo thư dựng giới được khóa, nếu có)_
- **Quy tắc ưu tiên:** PROJECT_DNA/canon truyện (bao gồm lựa chọn style/worldbuilding đã khóa) > Worldbuilding guide đã chọn > Author Style đã chọn.
- **Giải thích:** PROJECT_DNA là nơi khóa truyện dùng guide/style nào; nếu canon truyện mâu thuẫn với đạo thư dựng giới hoặc văn phong đại thần, canon truyện thắng.
- **Ghi chú phong cách:** _(yêu cầu đặc biệt nào không?)_

### C. Đạo Thư Dựng Giới & Đường Dẫn Nạp

> Xem bảng Worldbuilding Complete files và đường dẫn nạp phong cách đầy đủ tại `templates/AUTHOR_STYLE_CATALOG.md`.
> Pipeline tự resolve path từ `style_model` và `worldbuilding_guide` trong frontmatter — user chỉ cần ghi mã.

- **Worldbuilding guide (Mã):** _(Xianxia: ghi mã Đại Thần có `_Worldbuilding_Complete.md`; bỏ trống = hệ thống tự resolve theo `style_model`)_
- **Ghi chú:** OT/PT chưa có Worldbuilding Complete riêng; nếu chọn hai mã này thì dùng Author Style + Xianxia consistency/world operating rules.

---

## IV. THẾ GIỚI QUAN

> Điền các mục phù hợp với thể loại đã chọn. Bỏ trống mục không liên quan.

### A. Nền Tảng Chung (Mọi Thể Loại)

- **Tên thế giới / Bối cảnh:**
- **Thời đại:** _(thượng cổ / trung đại / cận đại / hiện đại / tương lai)_
- **Loại hình / Quy mô:** _(đơn giới / đa tầng / đa vũ trụ / hành tinh đơn)_
- **Bí mật lịch sử / Lời nguyền:** _(nếu có — đây là nguồn mystery tốt)_
- **Địa điểm / Khu vực quan trọng:** _(liệt kê 3-5 locations chính)_

### B. Tiên Hiệp — Thế Giới Tu Chân _(chỉ điền nếu genre = Xianxia)_

- **Hệ thống Cảnh Giới:** _(custom hoặc dùng template chuẩn từ consistency_rules)_
- **Mốc Cultivation Clock ban đầu:** _(cảnh giới/tầng/CANON_GAP, căn cơ, thời gian đã tu luyện)_
- **Mốc tuổi tu luyện:** _(vd: 51 tuổi -> Trúc Cơ hậu kỳ; mỗi mốc ghi tuổi/thời gian, cảnh giới, lý do nhanh/chậm hơn benchmark)_
- **Tốc độ tu luyện:** _(Nhanh: 5-15 tiểu cảnh hoặc gần 1 đại cảnh mỗi 1-2 đại hồi / Chậm: 1 đại cảnh hoặc 2-4 tiểu cảnh trong một đại hồi / Siêu chậm: 0.5 đại cảnh hoặc 1-3 tiểu cảnh trong một đại hồi)_
- **Nhịp progression mong muốn:** _(vd: 6 micro / 3 meso / 1 breakthrough mỗi 10 chương, hoặc biến thể có lý do)_
- **Linh Mạch / Linh Khí:**
- **Tông Môn / Thế lực chính:** _(liệt kê 3-5 tông phái, mỗi tông 1 câu mô tả)_
- **Cấm địa / Bí cảnh:**
- **Bí cảnh / Tiểu giới:** _(nguồn gốc, chu kỳ mở, luật bên trong, entry limit, rủi ro, phần thưởng)_
- **Thiên Kiếp / Kiếp Nạn:** _(khi nào kích hoạt, loại kiếp, cách chuẩn bị, aftermath)_
- **Thiên Đạo / Nhân Quả / Khí Vận:** _(vô tình hay có ý chí, lời thề phản phệ, khí vận vận hành ra sao)_
- **Di tích / Truyền thừa / Kỷ nguyên cũ:** _(ai để lại, cấm chế, tiêu chí chọn người, hậu quả chính trị)_
- **Yêu thú / Linh thú / Ma tu / Quỷ tu:** _(luật tu luyện riêng, hóa hình, phản phệ, xã hội hoặc vai trò tài nguyên)_
- **Phi thăng / Tầng thế giới:** _(Nhân giới/Linh giới/Tiên giới, điều kiện lên giới, pháp tắc khác nhau)_
- **Kinh tế (Linh thạch / Đan dược):**

### C. Đô Thị — Thế Giới Hiện Đại _(chỉ điền nếu genre = Urban)_

- **Thành phố / Quốc gia:**
- **Hệ thống ngầm:** _(gia tộc, thế giới ngầm, tổ chức bí mật)_
- **Quy tắc xã hội:** _(pháp luật, camera, mạng xã hội — ràng buộc MC)_
- **Siêu năng lực / Hệ thống đặc biệt:** _(nếu có)_

### D. Ngôn Tình — Bối Cảnh Tình Cảm _(chỉ điền nếu genre = Romance)_

- **Bối cảnh xã hội:** _(hiện đại / cổ đại / dân quốc / xuyên thời gian)_
- **Tầng lớp / Giai cấp:** _(khoảng cách giai cấp = conflict tự nhiên)_
- **Nghề nghiệp chính:** _(quan trọng cho worldbuilding hiện đại)_
- **Rào cản tình yêu:** _(gia tộc / giai cấp / hiểu lầm / bệnh tật / kẻ thứ ba)_

### E. Xuyên Không — Hai Thế Giới _(chỉ điền nếu genre = Time Travel)_

- **Thời đại gốc (MC đến từ):**
- **Thời đại đến (MC xuyên tới):**
- **Cơ chế xuyên không:** _(tai nạn / hệ thống / bảo vật / luân hồi)_
- **Thân phận gốc (người bị chiếm thân):**
- **Hệ thống chính trị thời đại đến:**
- **Kiến thức hiện đại MC có thể dùng:**
- **Paradox rules:** _(MC có thể thay đổi lịch sử không? Hậu quả?)_

### F. Khoa Huyễn — Vũ Trụ Khoa Học _(chỉ điền nếu genre = Sci-Fi)_

- **Cấp độ công nghệ:** _(Kardashev Scale: Type 0 → Type III)_
- **Nền văn minh:** _(đơn / đa nền văn minh / liên bang hành tinh)_
- **Quy luật vũ trụ:** _(hard SF rules / vật lý giả tưởng)_
- **Phương tiện di chuyển:** _(FTL? Wormhole? Generation ship?)_
- **Mối đe dọa chính:** _(ngoại lai / AI / entropy / xung đột nội bộ)_

### G. Hệ Thống / Meta Genre _(chỉ điền nếu genre = Meta Genre)_

- **Loại System:** _(tông chủ / phản diện nghịch tập / thợ săn / vô sỉ / thao túng)_
- **System Interface:** _(panel / giọng nói / ý niệm / companion)_
- **Quy tắc System cốt lõi:** _(nhiệm vụ? điểm? tiến hóa?)_
- **Thế giới base:** _(tu chân / hiện đại / hậu tận thế / dị giới)_
- **MC↔System relationship:** _(hợp tác / đối lập / ký sinh / mentor)_

---

## V. HỆ THỐNG SỨC MẠNH / CƠ CHẾ CỐT LÕI

> Mỗi thể loại có một "hệ thống" riêng. Điền phần phù hợp.

- **Tên hệ thống:** _(Tu luyện / Dị năng / Công nghệ / System / Quan trường / Tình cảm...)_
- **Các cấp bậc / Giai tầng chính:** _(liệt kê từ thấp đến cao)_
- **Cái giá đột phá / Hạn chế sức mạnh:** _(QUAN TRỌNG — không có sức mạnh miễn phí)_
- **Tài nguyên cốt lõi:** _(Linh thạch / Tiền / Điểm kinh nghiệm / Quan hệ / Tình cảm...)_
- **Bottleneck chính:** _(Nút thắt nào tạo kịch tính? MC kẹt ở đâu?)_
- **Fuel thăng cấp:** _(hard resources / soft resources / emotional catalysts cần tích lũy)_
- **Cái giá aftermath:** _(ổn cố cảnh giới, phản phệ, recovery, quan hệ bị ảnh hưởng)_
- **Kim Thủ Chỉ (Golden Finger):** _(MC có lợi thế gì? — PHẢI có giới hạn rõ ràng)_
- **Giới hạn Kim Thủ Chỉ:**

---

## VI. NHÂN VẬT CHÍNH

- **Tên:**
- **Tuổi ban đầu:**
- **Xuất thân:**
- **Nghề nghiệp / Thân phận:**
- **Ngoại hình (đặc điểm nhận dạng):**

### Tâm Lý & Nội Tâm

- **Want (muốn gì — mục tiêu bề mặt):**
- **Need (cần gì — KHÁC want):**
- **Lie (điều tin sai — niềm tin cần thay đổi):**
- **Ghost (quá khứ ám ảnh):**
- **Câu hỏi tồn tại:** _(1 câu hỏi triết lý xuyên suốt, vd: "Ta là ai?", "Có đáng sống không?")_

### Tính Cách

- **Tính cách cốt lõi (1-2 câu):**
- **Điểm mạnh:**
- **Điểm yếu:**
- **Điểm mù (Blind Spots):** _(thứ MC không thấy về bản thân)_
- **Bí mật:** _(MC giấu điều gì?)_
- **Voice (giọng nói riêng):** _(cách nói, từ vựng, nhịp điệu)_

### Vị Trí Trên Phổ Tính Cách (Style DNA)

```
[Cực Lạnh] ←————————————————→ [Cực Hài]
  MC của bạn nằm ở: [          ]

[Cô Độc]  ←————————————————→ [Trọng Tình]
  MC của bạn nằm ở: [          ]

[Mưu Lược] ←————————————————→ [Bản Năng]
  MC của bạn nằm ở: [          ]
```

### MC Archetype _(tùy thể loại)_

- **Xuyên Không:** Linh Hồn Kép — tư duy hiện đại + vỏ bọc cổ đại
- **Hệ Thống:** _(tông chủ / phản diện nghịch tập / thợ săn / vô sỉ / thao túng)_
- **Đô Thị:** _(giả heo ăn thịt hổ / phong lưu / bá tổng / bình dân nghịch tập)_
- **Tiên Hiệp:** _(nghịch thiên / mê mang tìm đạo / hài hước vô sỉ / giản khiết)_

---

## VII. DÀN NHÂN VẬT

- **Số lượng nhân vật quan trọng:** _(khuyến nghị: 8-15 nhân vật có arc)_

### Tình Yêu / Đối Tác Chính

- **Tên:**
- **Kiểu tình yêu:** _(thanh mai trúc mã / kẻ thù thành yêu / cứu rỗi / tri kỷ / ngược tâm)_
- **Rào cản chính giữa hai người:**
- **Voice riêng:**

### Sư Phụ / Mentor

- **Tên:**
- **Vai trò trong arc MC:**
- **Bí mật Mentor giấu:**

### Huynh Đệ / Đồng Đội

- **Liệt kê (mỗi người 1 câu mô tả + voice riêng):**
  - 1.
  - 2.
  - 3.

### Relationship Matrix (Sơ Bộ)

```
[MC] ←→ [Nữ chính]: [loại quan hệ]
[MC] ←→ [Mentor]: [loại quan hệ]
[MC] ←→ [Phản diện]: [loại quan hệ]
[Nữ chính] ←→ [Phản diện]: [loại quan hệ — nếu có]
```

---

## VIII. PHẢN DIỆN

### Phản Diện Cuối Cùng (Final Boss)

- **Tên / Danh xưng:**
- **Loại phản diện:** _(tham vọng / bị định mệnh đẩy / hệ thống đối lập / tàn khốc có lý)_
- **Want phản diện:** _(hắn muốn gì — phải hợp lý)_
- **Khoảnh khắc "người":** _(1 cảnh cho thấy hắn cũng là con người)_
- **Thời điểm lộ diện:** _(chương bao nhiêu?)_
- **Vì sao hắn ĐÚNG (từ góc nhìn của hắn):**

### Phản Diện Arc (Boss mỗi Arc)

| Arc | Phản Diện | Loại | Mối Liên Hệ Với Boss Cuối | Ghi Chú |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

### Mini-boss / Chướng Ngại

- _(Liệt kê 2-3 nhân vật gây khó khăn nhỏ cho MC)_

---

## IX. CỐT TRUYỆN & CẤU TRÚC NARRATIVE

### A. Tổng Quan Cốt Truyện

- **Sự kiện khởi phát (Inciting Incident):**
- **Midpoint Twist:** _(mọi thứ MC tin → SAI)_
- **All Is Lost Moment:** _(MC ở điểm thấp nhất)_
- **Tầm nhìn Climax:**
- **Kiểu kết thúc:** _(HE / BE / Open / Bittersweet)_

### B. Three-Act Eight-Sequence (Sơ Bộ)

| Hồi | Đoạn | Chapters (ước tính) | Mục Đích | Sự Kiện Chính |
|---|---|---|---|---|
| I (25%) | 1: Status Quo → Inciting | Ch.1 - Ch.__ | Hook + giới thiệu | |
| I | 2: Predicament → Lock-in | Ch.__ - Ch.__ | Không đường lùi | |
| II (50%) | 3: First Obstacle | Ch.__ - Ch.__ | Trở ngại thật sự | |
| II | 4: Midpoint Twist ⚡ | Ch.__ - Ch.__ | Câu chuyện LẬT | |
| II | 5: Subplot Deepening | Ch.__ - Ch.__ | Chiều sâu | |
| II | 6: All Is Lost ⚡⚡ | Ch.__ - Ch.__ | MC thấp nhất | |
| III (25%) | 7: New Plan + Twist | Ch.__ - Ch.__ | MC thay đổi | |
| III | 8: Climax → Resolution ⚡⚡⚡ | Ch.__ - Ch.__ | Kết thúc | |

### C. Arc Planning

| Arc | Tên Arc | Chapters | Phản Diện | MC Cảnh Giới/Trạng Thái | Sự Kiện Chính |
|---|---|---|---|---|---|
| 1 | | Ch.1 - Ch.__ | | | |
| 2 | | Ch.__ - Ch.__ | | | |
| 3 | | Ch.__ - Ch.__ | | | |

### D. Seed Master — Phục Bút Xuyên Suốt

> Mỗi seed là một "lời hứa ngầm" với độc giả. PHẢI THU HOẠCH.

| Seed | Cài Đặt Tại | Thu Hoạch Tại | Mô Tả |
|---|---|---|---|
| Seed 1 (chính) | Arc 1 | Climax | _(phục bút xuyên suốt toàn truyện)_ |
| Seed 2 | | | |
| Seed 3 | | | |

### E. Thread Registry (Tuyến Truyện)

| Thread | Loại | Bắt Đầu | Kết Thúc | Ghi Chú |
|---|---|---|---|---|
| Quest (nhiệm vụ chính) | Main | Ch.1 | Ch.cuối | |
| Fire (tình cảm/quan hệ) | Sub | | | |
| Constellation (thế giới/bí ẩn) | Sub | | | |

---

## X. GIỌNG VĂN & CẤM KỴ

### A. Giọng Văn Tổng Quan

- **Từ khóa giọng văn:** _(3-5 tính từ, vd: bi tráng, lạnh lùng, hài hước, triết lý)_
- **Cảm xúc nền:** _(cảm xúc bao trùm toàn truyện)_
- **Chủ đề cốt lõi:** _(truyện muốn "nói" gì?)_
- **Sensory palette:** _(giác quan ưu tiên: thị → thính → xúc → khứu → vị)_

### B. Anti-AI DNA Checklist

> Prose Writer & Quality Auditor PHẢI tuân thủ. Vi phạm = HARD-FAIL.

```
CẤM TUYỆT ĐỐI:
  □ "vô cùng", "cực kỳ", "rất" (dùng hình ảnh thay thế)
  □ "Không chỉ... mà còn..."
  □ "Điều này cho thấy/chứng minh/phản ánh..."
  □ "Mang đến cảm giác...", "Tạo nên một bức tranh..."
  □ "Hòa quyện/đan xen/giao thoa...", "Sự kết hợp hoàn hảo..."
  □ Mở 3+ đoạn liên tiếp bằng cùng chủ ngữ
  □ Độ dài đoạn đều tăm tắp 5+ đoạn liên tiếp
  □ Rule of three vô thức (3 tính từ, 3 ví dụ liên tiếp)
  □ "Hắn cảm thấy [tính từ cảm xúc]" — phải SHOW, không TELL
  □ Infodump > 100 chữ liên tục
  □ Xianxia: tiếng lóng/chửi thề/meme/tham chiếu văn hóa hiện đại
  □ Xianxia cổ phong: giờ-phút kiểu đồng hồ hiện đại ("sáu giờ", "hai tiếng", "ba mươi phút")
  □ Xianxia/VN: 3+ câu cực ngắn liên tiếp ngoài giao chiến hoặc kinh biến thật sự
  □ Hài cưỡng ép bằng punchline, chơi chữ hoặc tiếng cười tập thể
```

### C. Cấm Kỵ Riêng

- **Cấm kỵ theo Đại Thần:** _(tham chiếu profile Đại Thần đã chọn)_
- **Cấm kỵ riêng của tác phẩm:** _(bổ sung nếu cần)_

### D. Blacklist Từ Vựng Theo Thể Loại

- **Tiên Hiệp:** Cấm từ hiện đại (năng lượng, power), tiếng lóng/chửi thề/meme và giờ-phút kiểu đồng hồ hiện đại trong bối cảnh cổ phong → dùng linh khí, chân nguyên, canh giờ
- **Đô Thị:** Cấm từ tu chân (đan điền, linh khí) trừ hybrid
- **Romance:** Cấm bạo lực đẫm máu quá mức
- **Sci-Fi:** Cấm phép thuật / siêu nhiên không có giải thích khoa học
- **Xuyên Không:** Cấm MC dùng kiến thức tương lai quá bừa bãi
- **Hệ Thống:** Cấm System toàn năng — PHẢI có giới hạn/cái giá

### E. Creative Premise Contract

> User không cần tự điền hết. Bước `Tự sinh PROJECT_DNA` sẽ tự sinh nếu đang để trống.
> Motif phổ biến ĐƯỢC dùng; mục này khóa góc thi triển cụ thể để truyện không đúng form mà nhạt.

- **Core Wound:** [Chờ hệ thống tự sinh ở bước Tự sinh PROJECT_DNA]
- **Irreversible Choice:** [Chờ hệ thống tự sinh ở bước Tự sinh PROJECT_DNA]
- **Moral Contradiction:** [Chờ hệ thống tự sinh ở bước Tự sinh PROJECT_DNA]
- **World Pressure:** [Chờ hệ thống tự sinh ở bước Tự sinh PROJECT_DNA]
- **Motif Execution Angle:** [Chờ hệ thống tự sinh ở bước Tự sinh PROJECT_DNA]
- **Reader Addiction Loop:** [Chờ hệ thống tự sinh ở bước Tự sinh PROJECT_DNA]
- **Scene Promise:** [Chờ hệ thống tự sinh ở bước Tự sinh PROJECT_DNA]
- **Scene Vitality Contract:** [Chờ hệ thống tự sinh ở bước Tự sinh PROJECT_DNA]

---

## XI. NHỊP ĐỘ & CẤU TRÚC TỰ SINH

> Các mục dưới đây được `enrich_dna` tự sinh từ seed ở Section I-X.
> User không cần tự điền — chỉ review và sửa sau khi hệ thống sinh xong.

- **Dàn thế câu dẫn:** [Tự sinh]
- **Nhịp tiểu sảng / đại sảng / cảm xúc lớn:** [Tự sinh]
- **Mục tiêu đan tuyến:** [Tự sinh]
- **Nhịp tu luyện theo đại hồi:** [Tự sinh]
- **Chương tích lũy và chương bùng nổ:** [Tự sinh]
- **Mỗi chương phải trả:** [Tự sinh]
- **Sổ phục bút:** [Tự sinh]
- **Sổ tuyến truyện:** [Tự sinh]
- **Bậc thang trùm đại hồi:** [Tự sinh]
- **Tiểu chướng / Chướng ngại:** [Tự sinh]

### Thước đo cố định

- **Số từ mỗi chương:** 2500
- **Điểm chất lượng tối thiểu:** 85/100
- **Phục bút mỗi chương:** ≥ 1
- **Giới hạn giải thích liền mạch:** ≤ 100 chữ

---

## XII. KHẾ ƯỚC THI TRIỂN HẠT GIỐNG

> Được `enrich_dna` tự sinh. Khóa cách từng field DNA biến thành hành động trong cảnh.

- **Cách thi triển cốt cách nhân vật chính:** [Tự sinh]
- **Cách vận dụng thế câu dẫn:** [Tự sinh]
- **Cách thi triển văn phong:** [Tự sinh]
- **Cách lộ thiên địa:** [Tự sinh]
- **Cách bối cảnh ép lựa chọn:** [Tự sinh]
- **Cách giữ tốc độ tu luyện:** [Tự sinh]

> Quy tắc chiều sâu và verdict rules xem `system/Xianxia/Depth/Xianxia_Depth_Contract.md`.

---

## XIII. SỔ KIỂM KHỞI TẠO (Pre-flight)

> Human + Lãng Khách đánh dấu xong trước khi seed/gieo chương.

### A. Nội Dung Đã Điền

```
□ Section I   — Hạt giống: lời dẫn + dấu riêng rõ ràng
□ Section II  — Thể loại đã chọn, điều phối xác nhận
□ Section II  — (Hybrid) Nhánh chính + nhánh phụ + tỷ lệ + quy tắc tương tác
□ Section III — Mã Đại Thần + đạo thư dựng giới đã khóa nếu có
□ Section IV  — Thế giới quan: ít nhất 3 địa danh + 1 bí mật lịch sử
□ Section V   — Đạo pháp/Sức mạnh: cấp bậc + giới hạn + nút thắt rõ
□ Section VI  — Nhân vật chính: mong cầu ≠ thiếu khuyết, có vết thương cũ, niềm tin sai, giọng riêng
□ Section VII — ≥ 3 nhân vật phụ quan trọng có giọng riêng
□ Section VIII — Phản diện cuối có want + khoảnh khắc "người"
□ Section IX  — Biến cố khởi phát + cú lật giữa truyện + đại cao trào đã có ý tưởng
□ Section X   — Cấm kỵ Đại Thần đã đọc, sổ cấm văn phong máy móc nắm rõ
□ Section XI  — Nhịp độ + cấu trúc tự sinh đã review (sau enrich_dna)
□ Section XII — Khế ước thi triển hạt giống đã review (sau enrich_dna)
```

### B. Hệ Thống Sẵn Sàng

```
□ Canon pack tồn tại: system/[Genre]/ có consistency_rules + style
□ (Hybrid) Canon pack PHỤ tồn tại: system/[Genre_Phụ]/ có consistency_rules + style
□ Author Style file tồn tại: system/[Genre]/Author Style/[MÃ]_*
□ Sub-agent squad đã có SOUL.md cho tất cả 5 agents
□ .env đúng key (LLM provider)
□ Ollama serve đang chạy (nếu dùng embedding mặc định)
```

### C. Lệnh Scaffold

```bash
# 1. Tạo cấu trúc thư mục
./scripts/scaffold.sh <ten_truyen_snake_case>

# 2. Copy PROJECT_DNA.md đã điền vào novel folder
cp PROJECT_DNA.md novels/<ten_truyen>/PROJECT_DNA.md

# 3. Khởi tạo control plane
python -m scripts.control_plane init novels/<ten_truyen>
python -m scripts.control_plane seed novels/<ten_truyen> --from-chapter 1 --to-chapter <target>

# 4. Build retrieval layers
python -m scripts.rag_context index novels/<ten_truyen>
python -m scripts.vector_db index novels/<ten_truyen>

# 5. Health check
python -m scripts.control_plane doctor novels/<ten_truyen>
```

---

---

## XIV. HYBRID GENRE EXAMPLES

> Các ví dụ combo hybrid phổ biến. Dùng làm tham chiếu khi khai báo hybrid trong frontmatter.

```yaml
# --- Hybrid Genre Examples ---
# Example: Đô Thị + Mạt Thế (urban with apocalypse pressure)
# genre: hybrid
# genre_secondary: apocalypse
# hybrid_ratio: 60-40

# Example: Tiên Hiệp + Hắc Ám (xianxia with dark themes)
# genre: hybrid
# genre_secondary: dark theme
# hybrid_ratio: 70-30

# Example: Ngôn Tình + Thế Thân (romance with substitute trope)
# genre: hybrid
# genre_secondary: substitute
# hybrid_ratio: 60-40

# Example: Hệ Thống + Quy Tắc Quái Đàm (system with rules horror)
# genre: hybrid
# genre_secondary: rules horror
# hybrid_ratio: 50-50

# Example: Đô Thị + eSports (urban with esports focus)
# genre: hybrid
# genre_secondary: esports
# hybrid_ratio: 55-45
```

---

*File này là SINGLE SOURCE OF TRUTH cho toàn bộ hệ thống Agentic AI.*
*Phiên bản: 2.1.04 — Đại Viên Mãn | Tương thích: Workflow v2.1.04 Hybrid-Genre*
*Pipeline: World Builder → Character Architect → Plot Weaver → Prose Writer → Quality Auditor*
*Orchestrator: Lãng Khách (浪客) — Tổng Quản*
