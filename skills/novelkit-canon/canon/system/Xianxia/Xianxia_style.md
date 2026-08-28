# Xianxia Style Guide
# Dành cho: Prose Writer (viết chương)
> **Phiên bản:** v3.00

## Tông Chỉ Hành Văn

### 8.1 Phong Cách Miêu Tả — Floor Chung / Mặc Định Nhĩ Căn

Các mẫu dưới đây là floor kỹ thuật miêu tả cho Xianxia và dùng DNA Nhĩ Căn làm mặc định khi truyện chưa khai báo Author Style. Nếu `PROJECT_DNA.md` đã chọn mã Đại Thần, Author Style tương ứng thắng các ví dụ phong cách ở mục này.

#### 8.1.1 Miêu Tả Chiến Đấu

```yaml
MIÊU TẢ CHIẾN ĐẤU:
  tông_chỉ: Mãnh liệt, hình tượng hóa cao, giàu nhịp điệu
  
  nguyên_tắc_cốt_lõi:
    - Dùng ĐỘNG TỪ MẠNH, bỏ trạng từ thừa
    - Miêu tả HIỆU ỨNG chứ không liệt kê tên chiêu
    - Tốc độ câu tăng dần theo cường độ chiến đấu
    - Xen kẽ tâm lý giữa các chiêu thức
    - Mỗi trận đấu phải có STAKES rõ ràng — đánh vì cái gì?
    - Chiến đấu có NHỊP: tấn công → phản kích → biến cố → escalation
    - Kỹ năng có tên — gọi tên chiêu thức, nhưng MÔ TẢ hiệu ứng
    
  ví_dụ_đối_chiếu:
    ❌_xấu: "Hắn tung ra một chưởng cực kỳ mạnh mẽ."
    ✅_tốt: |
      "Chưởng ấn rơi xuống. Không gian nứt vỡ thành mạng nhện. 
       Trước khi tiếng nổ kịp vang, mặt đất đã sụp."
    
    ❌_xấu_2: "Hắn dùng kiếm pháp rất nhanh, đối thủ không kịp phản ứng."
    ✅_tốt_2: |
      "Kiếm quang lóe lên — một tia, chỉ một tia. 
       Khi đối phương nhận ra vết máu trên cổ, 
       thanh kiếm đã trở về vỏ."
       
  tránh_tuyệt_đối:
    - Liệt kê khô khan tên chiêu thức không có miêu tả
    - Miêu tả quá dài một chiêu (mất nhịp — tối đa 3-4 câu/chiêu)
    - Dùng số liệu cụ thể (không phải game, không nói "sát thương 1000")
    - Lặp cấu trúc: "Hắn [verb]. Hắn [verb]. Hắn [verb]." ← CẤM
```

#### 8.1.2 Miêu Tả Tu Luyện & Đột Phá

> **Phạm vi:** mục này chỉ quy định *văn phong/imagery* khi viết đột phá. Cấu trúc narrative (5 TYPE, mỗi type 5 nhịp), foreshadow 3-1-1, bottleneck — xem `Cultivation_Progression_System.md` §5/§4/§6 (source of truth).

```yaml
MIÊU TẢ ĐỘT PHÁ:
  tông_chỉ: Đột phá = đau đớn + nguy hiểm + transformation — KHÔNG BAO GIỜ dễ dàng
  
  nguyên_tắc:
    - Dùng IMAGERY CƠ THỂ: kinh mạch, đan điền, xương cốt, máu, mao khổng
    - Đột phá phải có CÁI GIÁ rõ ràng (đau đớn, rủi ro, tiêu hao)
    - Cảm giác biến đổi từ bên trong ra — không chỉ mô tả bên ngoài
    - Xen kẽ tâm lý: nhân vật nghĩ gì giữa cơn đau? Sợ hãi? Kiên định? Ngộ ra?
    
  ví_dụ_đối_chiếu:
    ❌_xấu: "Hắn ngồi xuống tu luyện và đột phá thành công."
    ✅_tốt: |
      "Linh khí cuồn cuộn đổ vào kinh mạch như thác lũ. 
       Mỗi mao khổng trên cơ thể đều rỉ máu — cái giá 
       của việc ép nén cả trăm năm đạo uẩn vào một đêm."
    
    ❌_xấu_2: "Hắn cảm nhận tu vi tăng lên, Kim Đan hình thành."
    ✅_tốt_2: |
      "Trong đan điền, chân nguyên xoay tròn — chậm, rồi nhanh, rồi điên cuồng. 
       Hắn nghe thấy tiếng xương cốt rạn nứt, nghe thấy tiếng gió gào 
       trong kinh mạch. Rồi — tĩnh lặng. Một hạt kim quang lặng lẽ ngưng tụ, 
       nhỏ như hạt gạo, nặng như sơn nhạc."

  kỹ_thuật_nâng_cao:
    - Đột phá ở cảnh giới cao → dùng ngôn ngữ SIÊU THỰC, huyền diệu
    - Đột phá kèm kiếp nạn → xen kẽ miêu tả bên trong + sấm sét bên ngoài
    - Đột phá thất bại → miêu tả sự sụp đổ, tuyệt vọng, đau đớn gấp bội
```

#### 8.1.3 Miêu Tả Cảnh Vật

```yaml
MIÊU TẢ CẢNH VẬT:
  tông_chỉ: Thủy mặc họa — ít nhưng sắc, một hình ảnh đúng hơn mười hình ảnh thừa
  
  nguyên_tắc:
    - NHÂN CÁCH HÓA thiên nhiên — trong xianxia, trời đất có linh
    - Cảnh vật PHẢN ÁNH tâm trạng nhân vật (pathetic fallacy)
    - Dùng ngũ giác: Không chỉ nhìn, mà nghe, ngửi, cảm nhận
    - "Sơn bất tại cao, hữu tiên tắc danh" — ý cảnh quan trọng hơn chi tiết
    
  ví_dụ_đối_chiếu:
    ❌_xấu: "Ngọn núi rất cao và đẹp."
    ✅_tốt: |
      "Mây trắng vắt ngang lưng chừng Thanh Vân Phong 
       như dải lụa trên thân thể người khổng lồ đang ngủ."
    
    ❌_xấu_2: "Ngọn núi cao 3000 mét, trên đỉnh có một cái đài bằng đá."
    ✅_tốt_2: |
      "Gió thổi qua đỉnh núi, cuốn theo tàn hương từ đỉnh thắp trên đài tế, 
       phảng phất như tiếng thở dài của người tu hành đã chìm vào thời gian."

  cảnh_theo_tâm_trạng:
    bi_thương: "Mưa rơi trên phế tích, mỗi giọt đập vào đá vỡ như tiếng thì thầm của vong hồn."
    phấn_khích: "Linh khí trong không khí sôi sục, cỏ cây hai bên đường rung rinh như đón chào."
    tĩnh_lặng: "Hồ nước phẳng lặng như gương đồng, phản chiếu một mảnh trăng khuyết và bóng người ngồi bất động."
    sát_khí: "Gió ngừng. Lá rụng đông cứng giữa chừng. Cả khu rừng nín thở."
```

#### 8.1.4 Miêu Tả Nội Tâm

```yaml
MIÊU TẢ NỘI TÂM:
  tông_chỉ: Nhân vật xianxia KHÔNG MÍT ƯỚT — ngay cả đau đớn cũng nén
  
  nguyên_tắc:
    - Không nói thẳng "hắn buồn" → SHOW the emotion, don't TELL
    - Nội tâm = LỰA CHỌN (ta phải chọn giữa X và Y) — không phải nhật ký cảm xúc
    - Đạo tâm = NIỀM TIN — nhân vật bám vào gì khi mọi thứ sụp đổ?
    - Nội tâm main phải nhất quán với tính cách đã thiết lập
    - Ở cảnh giới cao → nội tâm trở nên triết lý, trầm mặc hơn
    - Khoảnh khắc đột phá ngộ đạo → dùng ngôn ngữ huyền diệu, siêu thực
    
  ví_dụ_đối_chiếu:
    ❌_xấu: "Hắn cảm thấy vô cùng kinh ngạc khi nhìn thấy cảnh này."
    ✅_tốt: "Đồng tử co lại. Tay nắm kiếm siết chặt đến trắng bệch. 
             Cảnh trước mắt — không thể. Tuyệt đối không thể."
    
    ❌_xấu_2: "Hắn rất buồn vì sư phụ chết."
    ✅_tốt_2: |
      "Hắn không khóc. Chỉ đứng đó, nhìn chiếc áo bào dính máu 
       bay trong gió, rồi nhặt lên, gấp lại thật gọn — 
       như cách sư phụ từng dạy hắn gấp áo ngày đầu nhập môn."

  nội_tâm_theo_lựa_chọn:
    mẫu: |
      "Cứu nàng, nghĩa là quay lưng lại với sư môn. 
       Không cứu, nghĩa là mất đi thứ duy nhất khiến 
       con đường tu luyện này còn có ý nghĩa.
       Hắn nhắm mắt. Mở mắt. Bước đi."
    nguyên_tắc: "Không giải thích quyết định — chỉ cho thấy hành động. 
                  Độc giả tự hiểu."
```

### 8.2 Hệ Thống Thuật Ngữ Chuẩn

#### 8.2.1 Bảng Thuật Ngữ Cơ Bản

> **Source of truth (thuật ngữ cốt lõi cơ thể/năng lượng/vật phẩm):** `Tu_Tien_Texture_Floor.md` §11.1. Bảng dưới là bản tra nhanh nhóm theo tu_luyện/xã_hội/vật_phẩm cho Prose Writer; khi lệch, Texture §11.1 thắng.

```yaml
THUẬT NGỮ CƠ BẢN (phải nhất quán xuyên suốt):
  tu_luyen:
    - Linh khí / Chân nguyên / Tiên lực (theo cảnh giới tăng dần)
    - Đan điền (nơi tích trữ tu vi)
    - Thần thức / Nguyên Thần (sức mạnh tinh thần)
    - Nhục thân (thể xác vật lý)
    - Thiên kiếp / Lôi kiếp (thiên phạt khi đột phá)
    
  xa_hoi:
    - Phàm nhân / Phàm tục (người không tu luyện)
    - Tu sĩ / Tu chân giả (người tu luyện)
    - Tản tu / Tản nhân (tu sĩ không thuộc tông phái)
    - Tông môn / Môn phái (tổ chức tu luyện)
    
  vat_pham:
    - Linh thạch (tiền tệ + tài nguyên tu luyện)
    - Đan dược (thuốc tu luyện)
    - Pháp khí → Pháp bảo → Linh bảo → Tiên khí (cấp bậc vũ khí)
    - Truyền âm phù (thông tin liên lạc)
    - Trữ vật đại / Trữ vật giới chỉ (túi không gian)
    - Phi kiếm / Phi hành pháp khí (phương tiện bay)
```

#### 8.2.2 Từ Vựng & Cổng Chống Hiện Đại Hóa

> **Source of truth:** `Tu_Tien_Texture_Floor.md` §11 (Bảng từ vựng cốt lõi, Bảng thay thế từ vựng, Cổng chống lệch văn phong hiện đại, Idiom).

Tóm tắt:
- Bảng thay thế Dùng/Cấm: Texture §11.3
- Lexical Gate (từ cấm trong prose): Texture §11.4
- Thuật ngữ cốt lõi: Texture §11.1
- Từ thường dùng sai: Texture §11.2
- Thành ngữ: Texture §11.5

#### 8.2.4 Positive Tu Tiên Texture Gate

> **Source of truth:** `Xianxia_Depth_Contract.md` §Texture Tier System.

Chương Xianxia phải có cảm giác thế giới tu luyện đang vận hành. Cổ phong sạch nhưng rỗng tu luyện = lệch genre.

Tóm tắt: Tier 1 (`bắt buộc`: hệ tu luyện vận hành trong scene), Tier 2 (`bắt buộc`: áp lực thân xác/nội tâm hoặc hệ thống), Tier 3 (`hỗ trợ`: vật phẩm/tài nguyên — không thay thế Tier 1/2). Chi tiết từng tier xem tại Depth_Contract.

`CANON_GAP` = không tự bịa tầng/cảnh; KHÔNG có nghĩa là né tu vi, thần thức, chân nguyên, kinh mạch, linh khí, pháp khí, đạo tâm, nhân quả.

Reviewer phải fail hoặc soft-fail nếu chương giống trinh thám/kiếm hiệp/phường thị mà thiếu Tier 1 hoặc Tier 2.

#### 8.2.5 Cultivation Progression Gate

> **Source of truth:** `Cultivation_Progression_System.md` (cadence §2.1 + §7.3, bottleneck §6, breakthrough types §5, foreshadow §4.1)

Texture đủ nhưng tiến độ tu luyện bị bỏ quên vẫn là lỗi Xianxia. Yêu cầu tóm tắt:

- Duy trì Cultivation Clock: current_realm, fuel, bottleneck, next_breakthrough, recent_progressions.
- Cadence tham chiếu: xem Progression §2.1 + §7.3 (số cụ thể + priority giữ ở nguồn, không lặp ở đây).
- Đột phá lớn: ≥2 loại fuel, foreshadow 3-1-1, bottleneck rõ, quá trình trên trang, aftermath.
- Không viết "tu luyện rồi đột phá" — phải show quá trình qua thân thể, kinh mạch, đan điền, thần thức, chướng ngại, kết quả.

#### 8.2.6 Xianxia World Operating Gate

> **Source of truth:** `Xianxia_World_Operating_System.md`

Khi chương dùng bí cảnh, thiên kiếp, đấu giá, đại pháp hội/tỷ võ, chiến tranh liên giới, tông môn, di tích, truyền thừa, dị bảo cổ đại, yêu thú, ma tu/quỷ tu, phi thăng, thiên đạo, nhân quả hoặc khí vận — hệ thống đó phải có luật, nguồn gốc, người kiểm soát, rủi ro và hậu quả trên trang. Không viết world systems như background rỗng. Bí cảnh/di tích/tiểu thế giới phải khóa cơ chế mở và tỷ lệ thời gian trong/ngoài; thiên kiếp phải khớp cảnh giới và có hậu quả thất bại; cơ duyên/dị bảo không được "ăn không" mà phải kèm cái giá.

#### 8.2.7 Quy Tắc Thuật Ngữ

```
QUY TẮC:
  - Một khi đã chọn thuật ngữ → KHÔNG ĐƯỢC thay đổi giữa chừng
  - Mỗi thuật ngữ phải được giải thích lần đầu xuất hiện (tự nhiên, trong ngữ cảnh)
  - Infodump về hệ thống tu luyện: TỐI ĐA 100 CHỮ liên tục — sau đó phải trả về narrative
  - Nếu cần giải thích nhiều hơn → rải qua đối thoại, hành động, suy nghĩ nhân vật
```

### 8.3 Đối Thoại

```yaml
NGUYÊN TẮC ĐỐI THOẠI:
  tông_chỉ: "Ngắn. Sắc. Có subtext."
  
  theo_canh_gioi:
    - Luyện Khí/Trúc Cơ: Nói năng thường, có thể hơi ngây thơ/nóng nảy
    - Kim Đan/Nguyên Anh: Trầm ổn hơn, suy nghĩ trước khi nói
    - Hóa Thần+: Ít nói, mỗi câu đều có trọng lượng
    - Cổ tu/Lão quái: Cách nói cổ kính, hàm súc, đôi khi nói nửa câu

  theo_tinh_cach:
    - Main lạnh lùng (kiểu Vương Lâm): Ít đối thoại, hành động nhiều hơn lời
    - Main hài hước (kiểu Bạch Tiểu Thuần): Nói nhiều, chém gió, nhưng thâm sâu
    - Main trầm mặc (kiểu Tô Minh): Độc thoại nội tâm nhiều hơn đối thoại

  theo_than_phan:
    - Lão niên nói KHÁC thiếu niên
    - Ma tu nói KHÁC chính đạo
    - Tông chủ nói KHÁC ngoại môn đệ tử
    - Xưng hô phải đúng thân phận: ta/ngươi, bản tọa, tiểu tử, lão phu, nàng...
    
  quy_tắc_implied_power:
    - Người MẠNH ít nói — một câu đủ khiến người khác im lặng
    - Người YẾU nhiều lời — nói để che giấu sợ hãi
    - Đối thoại giữa cường giả: ý tại ngôn ngoại, mỗi chữ là sát chiêu

  ví_dụ_đối_chiếu:
    ❌_xấu: "Ngươi không thể đánh bại ta vì ta mạnh hơn ngươi rất nhiều."
    ✅_tốt: "Ngươi... cũng xứng cầm kiếm trước mặt ta?"
    
    ❌_xấu_2: "Ta sẽ giết ngươi vì ngươi đã hại gia tộc của ta và giết cha ta."
    ✅_tốt_2: "Món nợ năm đó — hôm nay ta đến thu."
    
    ❌_xấu_3: "Cảm ơn tiền bối đã cứu mạng vãn bối, vãn bối vô cùng biết ơn."
    ✅_tốt_3: "[Cúi đầu sâu, không nói gì. Khi ngẩng lên, mắt đã đỏ.]"

  ky_thuat:
    - Mỗi nhân vật có "cách nói" riêng (khẩu đầu thiền)
    - Đối thoại chiến trường: Nhanh, sắc, đôi khi chỉ 1-2 chữ
    - Tránh đối thoại giải thích cốt truyện (exposition through dialogue) ← CẤM
    - Tránh mọi villain đều cười "ha ha ha" ← CẤM
```

### 8.4 Cấu Trúc Chương

> **Source of truth:** `Xianxia_style.md` → `Tu_Tien_Texture_Floor.md` §9.2.

Cấu trúc chương xianxia tuân theo 6 phần % tại Texture §9.2.

Bổ sung:

```
NHỊP ĐỘ CHƯƠNG (4 rule):
  - KHÔNG mở bằng miêu tả cảnh dài dòng
  - KHÔNG mở bằng "buổi sáng hôm đó, hắn tỉnh dậy..."
  - Câu cuối chương PHẢI khiến độc giả muốn lật trang tiếp
  - Infodump > 100 chữ liên tục = CẤM
```

### 8.5 Danh Sách "Tránh Tuyệt Đối" (Style Blacklist)

Đây là danh sách lỗi văn phong mà Agent PHẢI quét trước khi xuất bản:

```yaml
STYLE_BLACKLIST:

  # === LỖI CÂU VĂN ===
  
  BL_01_LẶP_CẤU_TRÚC:
    ❌: "Hắn rút kiếm. Hắn chém xuống. Hắn nhảy lui. Hắn lại tấn công."
    ✅: "Kiếm rút. Một đường chém thẳng xuống — đối phương né, 
         hắn đã ở sau lưng, kiếm quang chéo ngược."
    quy_tắc: Không quá 2 câu liên tiếp bắt đầu bằng cùng chủ ngữ

  BL_02_TRẠNG_TỪ_THỪA:
    ❌: "Hắn cực kỳ nhanh chóng phi lên trời, vô cùng mạnh mẽ."
    ✅: "Thân hình hóa thành tia sáng, xuyên phá tầng mây."
    quy_tắc: Bỏ "cực kỳ", "vô cùng", "rất", "vô cùng" — thay bằng hình ảnh

  BL_03_TELL_NOT_SHOW:
    ❌: "Hắn cảm thấy vô cùng kinh ngạc."
    ❌: "Nàng cảm thấy rất đau lòng."
    ❌: "Mọi người đều cảm thấy sợ hãi."
    ✅: SHOW the emotion qua hành động, biểu cảm, cơ thể
    quy_tắc: Cấm "cảm thấy [tính từ cảm xúc]" — phải miêu tả biểu hiện

  # === LỖI ĐỐI THOẠI ===
  
  BL_04_EXPOSITION_DIALOGUE:
    ❌: "Ngươi biết không, tu sĩ Kim Đan có thể sống 800 năm, 
         và Kim Đan được hình thành từ chân nguyên ngưng tụ trong đan điền..."
    ✅: Rải thông tin qua hành động, suy nghĩ, hoặc tối đa 1-2 câu trong đối thoại
    quy_tắc: Đối thoại giải thích hệ thống > 50 chữ liên tục = CẤM

  BL_05_VILLAIN_CƯỜI:
    ❌: "Ha ha ha! Ngươi tưởng có thể chạy thoát sao?"
    ✅: "[Hắn không cười. Chỉ nghiêng đầu nhìn, như nhìn con kiến.]"
    quy_tắc: Villain cười "ha ha" tối đa 1 lần trong toàn truyện — và phải có lý do

  # === LỖI CỐT TRUYỆN ===
  
  BL_06_NHÂN_VẬT_CHÍNH_LUÔN_ĐÚNG:
    ❌: Main không bao giờ sai, mọi quyết định đều đúng
    ✅: Main đưa ra quyết định SAI → phải gánh hậu quả → học bài học
    quy_tắc: Mỗi arc phải có ít nhất 1 sai lầm có hậu quả của main

  BL_07_INFODUMP:
    ❌: Giải thích hệ thống tu luyện 500 chữ liên tục
    ✅: Tối đa 100 chữ giải thích liên tục, sau đó phải quay về narrative
    quy_tắc: Infodump > 100 chữ = PHẢI chia nhỏ và rải vào câu chuyện

  # === LỖI NHỊP ĐỘ ===
  
  BL_08_MỞ_BÀI_CHẬM:
    ❌: "Buổi sáng, mặt trời mọc, Vương Lâm thức dậy, ăn sáng, rồi đi tu luyện."
    ✅: Mở giữa hành động, giữa khoảnh khắc quyết định, hoặc giữa bí ẩn
    quy_tắc: 3 câu đầu tiên phải có HOOK — nếu không có, viết lại

  BL_09_KẾT_CHƯƠNG_PHẲNG:
    ❌: "Mọi chuyện đã xong, hắn đi nghỉ ngơi."
    ✅: Kết bằng câu hỏi mới, mối đe dọa mới, hoặc khoảnh khắc ám gợi
    quy_tắc: Câu cuối chương phải khiến độc giả MUỐN lật trang tiếp
```

### 8.6 Style Quality Scoring — Cho Agent Tự Đánh Giá

```yaml
STYLE_SCORE_RUBRIC:
  
  chiến_đấu: (0-10)
    10: "Đọc mà thấy kiếm khí phả vào mặt. Nhịp hoàn hảo, stakes rõ, cảm xúc đan xen."
    7:  "Hay, có hình ảnh, có nhịp, nhưng một vài chỗ hơi kéo dài."
    4:  "Tạm được nhưng thiếu imagery, dùng trạng từ thừa, nhịp phẳng."
    1:  "Liệt kê chiêu thức, không có cảm xúc, đọc như báo cáo chiến trường."
    
  cảnh_vật: (0-10)
    10: "Một câu mà thấy cả bức tranh thủy mặc, cảnh vật có linh hồn."
    7:  "Đẹp, có nhân cách hóa, nhưng hơi dài hoặc thiếu kết nối tâm trạng."
    4:  "Mô tả được nhưng như sách địa lý — thiếu cảm xúc, thiếu linh hồn."
    1:  "Liệt kê sự vật: núi cao, sông dài, trời xanh — không có ý cảnh."
    
  đối_thoại: (0-10)
    10: "Mỗi câu đều có subtext, xưng hô đúng, implied power rõ, personality riêng biệt."
    7:  "Tốt, ngắn gọn, nhưng đôi khi các nhân vật nói giống nhau."
    4:  "Tạm, nhưng có exposition dump hoặc quá dài hoặc thiếu personality."
    1:  "Đối thoại giải thích, villain cười ha ha, mọi người nói như nhau."
    
  nội_tâm: (0-10)
    10: "Đau mà không mít ướt. Lựa chọn rõ ràng. Đạo tâm kiên cố. Chạm đến độc giả."
    7:  "Tốt, có chiều sâu, nhưng đôi khi hơi trực tiếp (tell thay vì show)."
    4:  "Nhạt, thiếu lựa chọn đạo đức, hoặc quá mít ướt."
    1:  "Flat. 'Hắn buồn. Hắn giận. Hắn vui.' — không có chiều sâu."
    
  nhịp_độ_chương: (0-10)
    10: "Hook mạnh, leo thang hoàn hảo, turn bất ngờ, consequence rõ, cliffhanger đỉnh."
    7:  "Tốt nhưng một giai đoạn hơi kéo hoặc turn hơi dễ đoán."
    4:  "Mở chậm, giữa phẳng, hoặc kết không có cliffhanger."
    1:  "Không có cấu trúc rõ ràng, đọc mệt, không biết đâu là đỉnh."

  NGƯỠNG:
    - Dưới 5.0 trung bình: REJECT — viết lại toàn bộ phần đó
    - 5.0-7.0: REVISION — sửa các điểm yếu cụ thể
    - 7.0-9.0: GOOD — chất lượng xuất bản
    - 9.0+: ĐỈNH — cấp Nhĩ Căn
```

---
