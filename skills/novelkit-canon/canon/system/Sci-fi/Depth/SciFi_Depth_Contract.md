# Sci-Fi Depth Contract

Mục đích: Contract index cho Quality Auditor và Verifier. Định nghĩa verdict rules và trỏ sang source of truth cho từng lớp depth của thể loại Khoa Huyễn.

## Source of Truth

| Lớp | Source File | Vai trò |
|-----|------------|---------|
| Consistency Rules | `system/Sci-fi/Sci-fi_consistency_rules.md` | Vật lý, công nghệ, văn minh, quy luật vũ trụ |
| Style Guide | `system/Sci-fi/Sci-fi_style.md` | Văn phong, đối thoại kỹ thuật, cấu trúc chương |
| Genre Operating | `system/Sci-fi/Genre Operating/SciFi_Operating_Guide.md` | Hard SF rules, văn minh vận hành |

## Sci-Fi Positive Standard

Mỗi chương Sci-Fi phải thể hiện ít nhất một cơ chế công nghệ/vật lý/văn minh thực sự tác động đến một lựa chọn, xung đột, nhận thức, cái giá phải trả, hoặc hậu quả.

Các cơ chế được chấp nhận:
- Công nghệ vận hành có giới hạn rõ (năng lượng, tài nguyên, thời gian)
- Quy luật vật lý (entropy, tương đối, lượng tử) ảnh hưởng hành động
- Văn minh ngoại lai / AI / hậu nhân loại tạo xung đột
- Môi trường vũ trụ (chân không, bức xạ, trọng lực) đe dọa sinh mệnh
- Chính trị liên bang / tập đoàn / phe phái ép lựa chọn

## Texture Tier System

| Tier | Yêu cầu | Ý nghĩa |
|------|----------|---------|
| **Tier 1** (bắt buộc) | Cơ chế khoa học/công nghệ vận hành trong scene | năng lượng có hạn, thiết bị hỏng có lý do, physics ép lựa chọn, AI có logic riêng |
| **Tier 2** (bắt buộc) | Áp lực sinh tồn/tâm lý/văn minh | thiếu oxy, cô lập, hoài nghi thực tại, xung đột đạo đức về công nghệ |
| **Tier 3** (hỗ trợ) | Vật phẩm / thiết bị / phương tiện | vũ khí, tàu, mecha — KHÔNG thay thế Tier 1/2 |

## Scene Types

Outline phải gắn tag cho mỗi cảnh chính:
- `tech_deployment`: sử dụng/sửa chữa/phát minh công nghệ
- `survival`: môi trường khắc nghiệt, resources ngặt, rủi ro vật lý
- `first_contact`: tương tác với văn minh khác, AI, hậu nhân loại
- `investigation`: phân tích dữ liệu, truy tìm manh mối khoa học
- `combat`: chiến đấu vũ trụ, mecha, điệp viên công nghệ
- `politics`: liên bang, tập đoàn, phe phái nội bộ
- `transition`: di chuyển không gian, nghỉ ngơi, kiểm tra hệ thống

## Tech / Civilization Progression Contract

- Macro progression: leo Kardashev scale, thăng cấp công nghệ, mở rộng ảnh hưởng
- Meso progression: phát minh đột phá, chinh phục văn minh, giải mã bí ẩn
- Micro progression: thu thập dữ liệu, sửa chữa, nâng cấp nhỏ

Cadence tham chiếu: ~10 chương có ~6 micro, ~3 meso, ~1 notable breakthrough/reveal.

Breakthrough lớn yêu cầu:
- Ít nhất 2 loại fuel: dữ liệu đã thu thập, tài nguyên, nhân lực, thời gian nghiên cứu
- Obstacle / constraint rõ trước khi giải quyết (physics limit, budget, opposing force)
- Foreshadow 3-1-1 cho breakthrough lớn: 3 dấu xa (dữ liệu + giả thuyết + chuẩn bị), 1 dấu gần (thử nghiệm), 1 dấu trực tiếp (breakthrough)
- Quá trình trên trang: phân tích, thử nghiệm, thất bại, điều chỉnh, thành công
- Aftermath: công nghệ mới tạo hệ quả (kẻ thù theo dõi, cân bằng quyền lực đổi, đạo đức xung đột)

## Hard SF Rule

Mỗi công nghệ/hiện tượng phải có:
- Lý thuyết nền tảng (dù là giả tưởng, phải nhất quán)
- Giới hạn vật lý / kinh tế / xã hội
- Side effects / bias / rủi ro
- Ai kiểm soát / ai bị loại trừ

Không viết: "AI vạn năng giải quyết mọi thứ." Phải viết: AI giới hạn trong dữ liệu đã học, năng lượng đang có, thời gian tính toán; ai sở hữu AI có quyền gì, mất gì.

## Operating Systems

Sci-Fi worldbuilding không phải phông. Khi chương dùng:
- **Công nghệ**: nguyên lý, nhiên liệu, vận hành, bảo trì, fail mode
- **Văn minh / chính trị**: liên bang, tập đoàn, tôn giáo, phân tầng sinh học
- **Vũ trụ / vật lý**: lỗ đen, neutron star, radiation belt, quantum effect
- **Văn minh ngoại lai**: sinh học, văn hóa, mục tiêu, cách giao tiếp
- **AI / hậu nhân loại**: self-awareness, goal drift, ethical alignment
- **Kinh tế**: năng lượng làm tiền, tài nguyên hiếm, thương mại liên hành tinh

Hệ thống nào xuất hiện phải có luật vận hành rõ, KHÔNG phải magic với vỏ bọc công nghệ.

## Review Verdict Rules

| Verdict | Điều kiện |
|---------|-----------|
| `PASS` | Đủ Tier 1 + Tier 2, tech/civ progression hợp lý, hard rules rõ |
| `PASS_WITH_FLAGS` | 1 lớp depth yếu nhưng phục hồi được |
| `SOFT_FAIL_STYLE` | 2 lớp texture/depth yếu |
| `HARD_FAIL_DEPTH` | Cảnh không có cơ chế khoa học/công nghệ vận hành, HOẶC công nghệ "magic" không giải thích, HOẶC AI/văn minh ngoại lai hành động vô logic, HOẶC breakthrough đột ngột không foreshadow |

## Anti-Magic Rule

Phép thuật / siêu nhiên KHÔNG được dùng trừ khi:
- Truyện là hybrid (sci-fi + xianxia, sci-fi + meta genre)
- `PROJECT_DNA.md` khai báo rõ phép thuật được phép
- Có lý thuyết giả tưởng bao quanh (pseudo-science explanation)

Reviewer phải hard-fail nếu chương dùng phép thuật không có giải thích và không phải hybrid.

## Không Conflict Rule

- Canon riêng truyện luôn thắng guide chung.
- Hard SF mức độ do `PROJECT_DNA.md` quyết định (hard sci / soft sci / space opera).
