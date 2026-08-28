# Time Travel / Xuyên Không Style Guide
# Dành cho: Prose Writer (Sử Quan) — viết chương

## Tông Chỉ Hành Văn

Xuyên không hay nhất khi độc giả VỪA thấy MC thông minh, VỪA lo lắng MC sẽ bị lộ. Tension đến từ: biết trước lịch sử nhưng KHÔNG kiểm soát được mọi thứ.

---

## Kỹ Thuật

### 1. Hai Giọng Văn Song Song — DNA Xuyên Không

```yaml
HAI_GIỌNG_VĂN:
  tông_chỉ: MC có 2 lớp ngôn ngữ — bên trong (hiện đại) vs bên ngoài (cổ đại)
  
  nguyên_tắc:
    - NỘI TÂM MC: Dùng ngôn ngữ hiện đại, đôi khi lẫn tiếng lóng, meme, suy nghĩ đời thường
    - ĐỐI THOẠI MC: Phải "diễn" — nói cổ phong, xưng hô đúng, lễ nghi đúng
    - KHOẢNH KHẮC LỠ MIỆNG: MC vô tình dùng từ hiện đại → tension cực đỉnh
    
  ví_dụ_đối_chiếu:
    ❌_xấu: |
      "Hắn nói: 'Ồ, cái này OK mà, không sao đâu.'"
    ✅_tốt: |
      "'Điều này... không thành vấn đề.' Hắn đáp, nhưng trong đầu 
       đang nghĩ: 'Mẹ ơi, suýt nói OK, may mà kịp dừng.'"
       
  ví_dụ_lỡ_miệng:
    ✅: |
      "'Tình hình này cần... cần một cuộc cải cách tổng thể.'
       Mọi ánh mắt đổ dồn về phía y. Vị lão thần nheo mắt: 
       'Tổng thể? Vị đại nhân giải thích rõ hơn được không?'
       Y nuốt nước bọt. Hai chữ đó — không thuộc về thời đại này."
```

### 2. Miêu Tả Thời Đại — Show, Don't Lecture

```yaml
MIÊU_TẢ_THỜI_ĐẠI:
  tông_chỉ: Thời đại phải SỐNG qua ngũ giác của MC, KHÔNG phải bài giảng lịch sử
  
  nguyên_tắc:
    - Miêu tả qua CẢM GIÁC CỦA MC — người hiện đại nhìn thế giới cổ đại
    - Culture shock = cơ hội miêu tả tuyệt vời
    - Infodump lịch sử: TỐI ĐA 80 CHỮ liên tục → sau đó phải quay về narrative
    - Thông tin lịch sử rải qua hành động, đối thoại, quan sát MC
    
  ví_dụ_đối_chiếu:
    ❌_xấu: |
      "Thời Tống, hệ thống khoa cử được chia thành ba cấp: hương thí, 
       hội thí, và điện thí. Mỗi năm có hàng vạn sĩ tử tham gia..."
    ✅_tốt: |
      "Hắn đứng giữa dòng người áo vải chen chúc trước cổng trường thi. 
       Mồ hôi, mùi mực, mùi lo âu — ba thứ trộn lẫn thành thứ mùi 
       mà hắn chưa từng ngửi ở thế kỷ 21. Ở đây, một bài văn 
       quyết định cả đời người."

    ❌_xấu_2: "Đường phố thời Đường rất sầm uất."
    ✅_tốt_2: |
      "Mùi hương liệu Tây Vực trộn với mùi dầu mỡ chiên bánh — 
       hắn hít một hơi sâu, và lần đầu tiên hiểu tại sao người ta gọi 
       nơi này là 'Trường An vạn lý'. Mỗi bước chân là một thế giới."
```

### 3. Miêu Tả Quyền Mưu & Triều Đình

```yaml
MIÊU_TẢ_QUYỀN_MƯU:
  tông_chỉ: Triều đình = chiến trường không tiếng súng. Mỗi câu nói là vũ khí.
  
  nguyên_tắc:
    - Đối thoại triều đình: NGẮN, SẮC, NHIỀU SUBTEXT
    - Mỗi nhân vật có agenda riêng — không ai nói thật 100%
    - MC phải "đọc" ý nghĩa ẩn sau lời nói → dùng nội tâm để giải mã
    - Chiến thắng triều đường = chiến thắng bằng LỜI NÓI, BƯU KIỆN, LIÊN MINH
    
  ví_dụ_đối_chiếu:
    ❌_xấu: |
      "Vị quan kia nói: 'Ta sẽ hại ngươi vì ngươi đe dọa vị trí của ta.'"
    ✅_tốt: |
      "'Hạ quan nghe nói Hứa đại nhân gần đây thăng tiến rất nhanh. 
        Thật đáng mừng.' Nụ cười trên môi Vương lão đại — nhưng 
        mắt y không cười. Hứa Thanh hiểu: đó không phải lời chúc mừng. 
        Đó là lời cảnh cáo."

  lời_nói_triều_đình:
    nguyên_tắc:
      - Khen = có thể là đe dọa
      - Im lặng = có thể là đồng ý hoặc từ chối
      - Hỏi thăm gia đình = nhắc nhở "ta biết người thân ngươi ở đâu"
      - "Bệ hạ thánh minh" = "Tôi không đồng ý nhưng không dám nói"
```

### 4. Miêu Tả Chiến Trận (Lịch Sử)

```yaml
MIÊU_TẢ_CHIẾN_TRẬN:
  tông_chỉ: Chiến tranh cổ đại = MÁU, BÙN, SỢ HÃI — không phải game chiến thuật
  
  nguyên_tắc:
    - MC hiện đại nhìn chiến trường → SHOCK lần đầu 
    - Chiến thuật phải hợp lý với vũ khí/hậu cần thời đại đó
    - Binh lính là CON NGƯỜI — không phải số liệu
    - Chiến tranh có hậu quả: thương vong, đói kém, tị nạn

  ví_dụ_đối_chiếu:
    ❌_xấu: "Quân ta tấn công và giành chiến thắng."
    ✅_tốt: |
      "Tên lửa cắm vào bùn ướt cách hắn ba bước chân. Xung quanh, 
       tiếng rên rỉ thay thế tiếng hô xung trận. Chiến thắng — 
       nếu cảnh này gọi là chiến thắng. Hắn nhìn xuống tay mình: 
       máu ai đó. Không phải của hắn. Hắn nôn."

    ❌_xấu_2: "Hắn dùng chiến thuật hiện đại để thắng dễ dàng."
    ✅_tốt_2: |
      "Kế hoạch hoàn hảo trên giấy. Nhưng giấy không biết gió đổi chiều. 
       Giấy không biết lương thảo bị chuột gặm. Giấy không biết 
       kẻ đưa tin bị phục kích ở dặm thứ ba. Hắn ngồi trong trướng, 
       nhìn bản đồ, và lần đầu hiểu: chiến tranh thật không có nút Restart."
```

### 5. Nội Tâm MC Xuyên Không

```yaml
MIÊU_TẢ_NỘI_TÂM:
  tông_chỉ: MC mang NỖI CÔ ĐƠN của người biết quá nhiều nhưng không thể nói

  nguyên_tắc:
    - MC KHÔNG PHẢI siêu nhân — đôi khi nhớ nhà, sợ hãi, mệt mỏi
    - Nội tâm = LỰA CHỌN đạo đức (cứu hay không cứu? can thiệp hay để yên?)
    - Nostalgia: nhớ điện thoại, nhớ cà phê, nhớ mẹ — chi tiết nhỏ = cảm xúc lớn
    - Ở cảnh giới cao (quyền lực lớn) → nội tâm cô đơn hơn, trầm mặc hơn

  ví_dụ_đối_chiếu:
    ❌_xấu: "Hắn nhớ nhà."
    ✅_tốt: |
      "Đêm trăng sáng. Hắn ngồi trên bậc đá, mí mắt nặng trĩu. 
       Trong đầu bỗng vang lên nhạc chuông điện thoại — 
       ringtone cũ, bài hát mà mẹ hắn hay nghe. 
       Hắn giật mình. Nhìn xuống tay: không có điện thoại. 
       Chỉ có bóng trăng rơi trên lòng bàn tay trống rỗng."
       
    ❌_xấu_2: "Hắn phân vân không biết có nên cứu người đó."
    ✅_tốt_2: |
      "Người đó sẽ chết trong ba ngày. Hắn biết — lịch sử ghi rõ.
       Nhưng cứu y nghĩa là trận Xích Bích sẽ không xảy ra.
       Không có Xích Bích nghĩa là Tào Tháo thống nhất thiên hạ.
       Tào Tháo thống nhất nghĩa là... hắn không biết nữa. 
       Sách giáo khoa không viết kịch bản thay thế.
       Hắn khép mắt. Mở mắt. Bước đi — theo hướng ngược lại."
```

---

## Đối Thoại

### 6. Đối Thoại Đa Tầng

```yaml
NGUYÊN_TẮC_ĐỐI_THOẠI:
  tông_chỉ: "Mỗi nhân vật nói KHÁC NHAU — thời đại, thân phận, tính cách."
  
  theo_thân_phận:
    hoàng_đế: Ít lời, mỗi câu là mệnh lệnh hoặc kiểm tra. "Khanh nghĩ sao?"
    tể_tướng: Hàm súc, nói nửa câu, để đối phương tự hiểu. Thận trọng cực độ.
    tướng_quân: Thẳng thắn, ngắn gọn, ít chơi chữ. "Đánh hay rút?"
    thương_nhân: Khách sáo, hay cười, mỗi câu đều tính toán.
    nông_dân: Mộc mạc, chất phác, đôi khi thô nhưng thật.
    MC_xuyên_không: Bên ngoài cổ phong, bên trong hiện đại. Gap đó tạo hài/tension.

  theo_tình_huống:
    triều_đường: |
      Chuẩn mực, lễ nghi, xưng hô phức tạp.
      "Vi thần trộm nghĩ..." = "Tôi phản đối nhưng nói nhẹ nhàng."
    chiến_trường: |
      Ngắn, sắc, khẩn cấp. 
      "Rút!" / "Xung!" / "Giữ trận!" — không có diễn thuyết dài.
    mật_nghị: |
      Nói ít, ám chỉ nhiều. 
      "Lão phu nghe nói phương Bắc gần đây gió lớn." = "Quân địch sắp tấn công."
    đời_thường: |
      Tự nhiên hơn, MC có thể thả lỏng một chút.
      Nhưng KHÔNG BAO GIỜ quên mình đang ở thời cổ đại.

  ví_dụ_đối_chiếu:
    ❌_xấu: "'Bệ hạ, vi thần thấy kế hoạch này rất tốt, chúng ta nên thực hiện ngay.'"
    ✅_tốt: |
      "'Thánh thượng minh giám.' 
       Chỉ bốn chữ. Nhưng cái gật đầu nhẹ kèm theo — 
       đủ để hoàng đế hiểu: lão tể tướng cuối cùng đã gật."
       
    ❌_xấu_2: "'Ta sẽ giết ngươi vì ngươi phản bội.'"
    ✅_tốt_2: |
      "'Ngô huynh à, chén rượu hôm đó — ngon lắm.' 
       Ngô Đạt run lên. Chén rượu hôm đó — hắn đã bỏ thuốc.
       'Nhưng ta vẫn sống.' Cười. 'Thật phiền ha.'"
```

---

## Cấu Trúc Chương

### 7. Chapter Structure — Xuyên Không

```
CẤU TRÚC CHƯƠNG XUYÊN KHÔNG — 5 NHỊP:

  1. HOOK — Bắt đầu giữa tình huống hoặc quyết định
     ├── KHÔNG mở bằng "buổi sáng, MC thức dậy trong triều đại X"
     ├── Tốt: Mở giữa triều đường tranh luận, giữa mưu kế bị phá
     └── Tốt: Mở bằng chi tiết thời đại gây impact (MC nhìn/nghe/ngửi)

  2. RISING TENSION — Stakes leo thang
     ├── MC dùng kiến thức tương lai → thành công nhưng tạo nghi ngờ
     ├── Hoặc: MC KHÔNG NHỚ chi tiết quan trọng → phải improvise
     └── Xen kẽ: nội tâm hiện đại + hành động cổ đại

  3. TURN — Biến cố / twist
     ├── Lịch sử KHÔNG diễn ra như MC nhớ (butterfly effect)
     ├── Hoặc: AI ĐÓ nghi ngờ MC
     └── Hoặc: MC phát hiện thông tin mới thay đổi mọi tính toán

  4. CONSEQUENCE — Nhân quả rõ ràng
     ├── Chiến thắng cũng có cái giá
     ├── Butterfly effect lan rộng — hành động ở chương 10 ảnh hưởng chương 50
     └── MC phải đối mặt kết quả — không có "undo"

  5. CLIFFHANGER — Kết bằng mối đe dọa hoặc câu hỏi
     ├── "Nếu y biết trước điều này... y là AI?"
     ├── Hoặc: Sự kiện lịch sử lớn sắp xảy ra — MC chưa sẵn sàng
     └── Hoặc: Khoảnh khắc tĩnh lặng — MC nhớ nhà, đơn độc giữa thời đại

NHỊP ĐỘ TỔNG THỂ:
  - Chương "sảng" (MC thắng): 30% — quá nhiều = nhạt
  - Chương "tension" (MC bị dồn ép): 40% — backbone
  - Chương "cảm xúc" (nội tâm, quan hệ): 20% — chiều sâu
  - Chương "twist" (lật kèo): 10% — đỉnh cao
```

---

## Style Blacklist — Tránh Tuyệt Đối

```yaml
STYLE_BLACKLIST_XUYÊN_KHÔNG:

  BL_01_GIỌNG_VĂN_HIỆN_ĐẠI_TRÀN_LAN:
    ❌: Toàn truyện viết giọng hiện đại, không có hơi thở cổ đại
    ✅: Hai lớp rõ ràng — nội tâm MC hiện đại, thế giới cổ đại
    quy_tắc: Miêu tả/đối thoại cổ phong ≥ 60%, nội tâm hiện đại ≤ 40%

  BL_02_MC_NHƯ_WIKIPEDIA:
    ❌: MC giải thích lịch sử cho độc giả qua nội tâm dài dòng
    ✅: Thông tin lịch sử rải qua hành động, quan sát, đối thoại tự nhiên
    quy_tắc: Infodump lịch sử > 80 chữ liên tục = CẤM

  BL_03_CẢI_CÁCH_MONTAGE:
    ❌: "Hắn giới thiệu giấy, rồi in ấn, rồi thuốc súng..." — skip qua khó khăn
    ✅: Mỗi cải cách là một ARC — có thử nghiệm, thất bại, kháng cự, rồi mới thành
    quy_tắc: Mỗi phát minh/cải cách lớn cần ≥ 3 chương phát triển

  BL_04_NHÂN_VẬT_CỔ_ĐẠI_NGU:
    ❌: Mọi người cổ đại đều ngây ngô, chỉ MC thông minh
    ✅: Người cổ đại thông minh THEO CÁCH CỦA HỌ — MC chỉ có lợi thế kiến thức
    quy_tắc: Mỗi arc phải có ≥1 nhân vật cổ đại khiến MC phải thực sự nể phục

  BL_05_LẶP_PATTERN_SẢNG:
    ❌: MC dự đoán → đúng → mọi người sốc → MC cool → lặp lại
    ✅: MC dự đoán → đúng lần 1,2 → lần 3 SAI (butterfly effect) → crisis
    quy_tắc: Pattern "dự đoán đúng" không lặp quá 3 lần liên tiếp

  BL_06_VILLAIN_1_CHIỀU:
    ❌: Phản diện chỉ vì "ác", "ghen", "ngu"
    ✅: Phản diện có lý do: bảo vệ quyền lợi, giá trị quan khác, hoặc bị MC đe dọa
    quy_tắc: Mọi antagonist phải có ≥ 1 scene từ POV của họ

  BL_07_TÌNH_CẢM_NỮ_NPC:
    ❌: Nữ chính/phụ chỉ tồn tại để yêu MC và được MC cứu
    ✅: Nhân vật nữ có mục tiêu riêng, agency riêng, có thể KHÔNG YÊU MC
    quy_tắc: Mỗi nhân vật nữ quan trọng phải có arc độc lập
```

---

## Style Quality Scoring — Cho Agent Tự Đánh Giá

```yaml
STYLE_SCORE_RUBRIC:
  
  hai_giọng_văn: (0-10)
    10: "Nội tâm MC hiện đại sắc sảo, đối thoại cổ đại chuẩn mực. Gap tạo hài + tension."
    7:  "Tốt, nhưng đôi khi hai giọng bị trộn lẫn, ranh giới không rõ."
    4:  "Một giọng thống trị, giọng kia bị yếu — mất essence xuyên không."
    1:  "Không phân biệt được MC đang nghĩ hay đang nói. Giọng đều."

  miêu_tả_thời_đại: (0-10)
    10: "Đọc mà ngửi thấy mùi thời cổ đại. Ngũ giác đầy đủ, tự nhiên."
    7:  "Bối cảnh rõ, nhưng đôi khi hơi 'sách giáo khoa'."
    4:  "Thiếu chi tiết đặc trưng thời đại. Có thể xảy ra ở bất kỳ thời kỳ nào."
    1:  "Không có hơi thở cổ đại. Viết như tiểu thuyết hiện đại."

  quyền_mưu: (0-10)
    10: "Mỗi đối thoại triều đường đều có 2-3 lớp ý nghĩa. Tension ngấm ngầm."
    7:  "Tốt, nhưng đôi khi quá trực tiếp, mất sự hàm súc."
    4:  "Quyền mưu đơn giản, dễ đoán, thiếu lớp lang."
    1:  "'Ta sẽ hại ngươi' — nói thẳng, không có subtext. Không phải xuyên không."

  nội_tâm_MC: (0-10)
    10: "Cô đơn, lựa chọn đạo đức, nostalgia + humor — đầy đủ chiều sâu."
    7:  "Tốt nhưng đôi khi thiếu humor hoặc quá nặng nề."
    4:  "MC không có nội tâm đặc trưng xuyên không. Có thể là nhân vật bản địa."
    1:  "Flat. 'Hắn buồn. Hắn vui.' Không có chiều sâu."

  nhịp_độ_chương: (0-10)
    10: "Hook mạnh, tension leo thang, twist bất ngờ, consequence rõ, cliffhanger đỉnh."
    7:  "Tốt nhưng đôi khi mid-chapter hơi phẳng."
    4:  "Mở chậm, giữa kéo dài, kết không có cliffhanger."
    1:  "Không có cấu trúc. Đọc mệt."

  NGƯỠNG:
    - Dưới 5.0 trung bình: REJECT — viết lại
    - 5.0-7.0: REVISION — sửa điểm yếu
    - 7.0-9.0: GOOD — chất lượng xuất bản
    - 9.0+: ĐỈNH — cấp Đại Thần xuyên không
```

---

*Prose Writer (Sử Quan) PHẢI đọc file này + file Author Style tương ứng trước khi viết chương.*
