# Xianxia Depth Contract
> **Phiên bản:** v3.00

Mục đích: Contract index cho Quality Auditor và Verifier. Định nghĩa verdict rules và trỏ sang source of truth cho từng lớp depth.

## Thứ Tự Đọc Cho Agent (Reading Order)

Agent mới vào bộ canon Xianxia đọc theo thứ tự:

1. **File này (`Xianxia_Depth_Contract.md`)** — điểm vào: index, precedence, verdict, manifest.
2. **Load theo nhu cầu scene** (không cần đọc hết mọi lúc):
   - Chất văn / ngôn ngữ / nhịp → `Texture/Tu_Tien_Texture_Floor.md`
   - Tu vi / đột phá / bottleneck → `Progression/Cultivation_Progression_System.md`
   - Bí cảnh / thiên kiếp / tông môn / di tích → `World/Xianxia_World_Operating_System.md`
   - Cảnh giới / logic nội tại / nhân vật → `Xianxia_consistency_rules.md`
   - Văn phong khi viết prose → `Xianxia_style.md`
3. **Nếu `PROJECT_DNA.md` có `style_model`** → load `Author Style/[MÃ] …` + `Worldbuilding guide/[MÃ] …` tương ứng. Đây là canon riêng, thắng ví dụ/default ở core (xem §Không Conflict Rule).

## Canon Version Manifest

Toàn bộ bộ canon hệ-thống Xianxia hiện ở **v3.00**. Mọi file phải đồng bộ mốc này:

| File | Version |
|------|---------|
| `Xianxia_Depth_Contract.md` | v3.00 |
| `Texture/Tu_Tien_Texture_Floor.md` | v3.00 |
| `Progression/Cultivation_Progression_System.md` | v3.00 |
| `World/Xianxia_World_Operating_System.md` | v3.00 |
| `Xianxia_consistency_rules.md` | v3.00 |
| `Xianxia_style.md` | v3.00 |
| `Author Style/*` (10 file per-master) | 3.0 |
| `Worldbuilding guide/*` (8 file per-master) | (canon riêng, theo mốc bộ) |

## Source of Truth

| Lớp | Source File | Vai trò |
|-----|------------|---------|
| Texture Floor | `system/Xianxia/Texture/Tu_Tien_Texture_Floor.md` | Ngôn ngữ, nhịp, cảm giác, cấm kỵ |
| Cultivation Progression | `system/Xianxia/Progression/Cultivation_Progression_System.md` | Cultivation Clock, foreshadow, bottleneck, spacing |
| World Operating | `system/Xianxia/World/Xianxia_World_Operating_System.md` | Bí cảnh, thiên kiếp, kinh tế, tông môn, di tích |
| Consistency Rules | `system/Xianxia/Xianxia_consistency_rules.md` | Cảnh giới, nhân vật, chiến đấu, logic nội tại |
| Style Guide | `system/Xianxia/Xianxia_style.md` | Văn phong, đối thoại, cấu trúc chương, blacklist |

## Xianxia Positive Standard

Mỗi chương Xianxia phải thể hiện ít nhất một cơ chế tu luyện thực sự tác động đến một lựa chọn, xung đột, nhận thức, cái giá phải trả, hoặc hậu quả.

Các cơ chế được chấp nhận:
- spiritual sense quét nguy hiểm, ý đồ, điểm yếu formation, khí thuốc, áp lực ẩn
- true essence, meridians, dantian, qi sea, primordial spirit thay đổi khả năng chịu đựng
- realm pressure, bottleneck, Dao heart, heart demon, karma, heavenly secret, lifespan cost buộc đánh đổi
- pill, talisman, formation, treasure, spirit stone, cultivation method, spirit herb dùng với chức năng và hậu quả rõ ràng

## Texture Tier System (Unified)

| Tier | Yêu cầu | Ý nghĩa |
|------|----------|---------|
| **Tier 1** (bắt buộc) | Hệ tu luyện vận hành trong scene | thần thức, chân nguyên, kinh mạch, linh khí, đạo tâm, nhân quả tác động lên lựa chọn/hành động |
| **Tier 2** (bắt buộc) | Áp lực thân xác/nội tâm hoặc áp lực hệ thống | kinh mạch đau, đan điền trầm, đạo tâm dao động, tâm ma, áp lực cảnh giới, thương thế pháp lực |
| **Tier 3** (hỗ trợ) | Vật phẩm/tài nguyên | linh thạch, đan dược, pháp khí, phù lục, linh thảo, trận pháp — KHÔNG thay thế Tier 1/2 |

## Scene Types

Outline phải gắn tag cho mỗi cảnh chính:
- `tu_luyen`: đột phá, lĩnh ngộ, luyện đan, formation, kỹ thuật, Dao heart, bottleneck
- `worldbuilding`: chợ búa, môn phái, luật lệ, kinh tế tài nguyên, hành trình
- `investigation`: truy tìm, nhân chứng, tàn khí, manh mối nhân quả
- `conflict`: quyết đấu, truy đuổi, phục kích, đàm phán dưới chênh lệch quyền lực
- `transition`: hồi phục, di chuyển, dàn dựng, nhịp cảm xúc nhẹ

Ngay cả `transition` cũng cần nhận thức Xianxia nhẹ, trừ khi outline giải thích rõ vì sao tu luyện vắng mặt.

## Cultivation Progression Contract

> **Source of truth (full):** `Cultivation_Progression_System.md`
> - Cadence: §2.1 (density tham chiếu) + §7.3 (Luật Hành Trình)
> - Bottleneck: §6 (5 loại + template thất bại)
> - Breakthrough types: §5 (TYPE A-E templates)
> - Foreshadow: §4.1 (3-1-1 rule)

Yêu cầu tóm tắt:
- Macro/Meso/Micro progression.
- Cadence tham chiếu: xem Progression §2.1 (density) + §7.3 (Luật Hành Trình) — không lặp số ở đây để tránh lệch.
- Breakthrough: ≥2 loại fuel, bottleneck rõ, foreshadow 3-1-1, quá trình trên trang, aftermath.
- Mọi cột mốc tu luyện: áp dụng Luật Hành Trình (§7.3), Spacing Rules (§7.2), không ép breakthrough bằng density tham chiếu.

## World Operating Contract

> Chi tiết đầy đủ: `Xianxia_World_Operating_System.md`

Khi chương dùng bí cảnh, thiên kiếp, tông môn, đấu giá, đại pháp hội/tỷ võ, chiến tranh liên giới, di tích, truyền thừa, dị bảo cổ đại, yêu thú, ma tu/quỷ tu, phi thăng, thiên đạo, nhân quả hoặc khí vận — hệ thống đó phải có luật, nguồn gốc, người kiểm soát, rủi ro và hậu quả trên trang.

Yêu cầu bổ sung theo `Xianxia_World_Operating_System.md`:
- Bí cảnh/di tích/tiểu thế giới: phân loại đúng (§1.1), khóa cơ chế mở và tỷ lệ thời gian trong/ngoài (§1.2), mức nguy hiểm khớp cảnh giới (§1.3), thưởng đi kèm rủi ro (§1.4).
- Thiên kiếp: loại kiếp khớp cảnh giới (§2.1-2.2), hậu quả thất bại phân tầng (§2.3), không hóa giải bằng ngoại lực rẻ tiền (§2.4).
- Đại pháp hội/tỷ võ (§5.2) và chiến tranh liên giới (§5.3): có mục đích, quy củ, hậu quả chính trị; không có "ông trời" dọn sạch xung đột.
- Dị bảo/truyền thừa cổ (§6.1): không "ăn không" — kèm cái giá và giới hạn sử dụng.

## Review Verdict Rules

| Verdict | Điều kiện |
|---------|-----------|
| `PASS` | Đủ Tier 1 + Tier 2, progression hợp lý, world operating có luật |
| `PASS_WITH_FLAGS` | 1 lớp depth yếu nhưng phục hồi được |
| `SOFT_FAIL_STYLE` | 2 lớp texture/depth yếu |
| `HARD_FAIL_DEPTH` | Cảnh không có cơ chế tu luyện vận hành, HOẶC lặp texture nông 3 chương, HOẶC breakthrough đột ngột thiếu Clock/fuel/bottleneck/foreshadow/process/aftermath, HOẶC world systems (bí cảnh, thiên kiếp, pháp hội, chiến tranh, di tích, dị bảo) xuất hiện như nhãn dán không có luật/rủi ro/hậu quả, HOẶC cơ duyên/dị bảo/vượt kiếp "ăn không" không kèm cái giá, HOẶC tỷ lệ thời gian bí cảnh/tiểu thế giới mâu thuẫn với lần thiết lập trước |

## Không Conflict Rule

- Canon riêng truyện (`PROJECT_DNA.md`, database, author style) luôn thắng guide chung.
- Các guide chung không bắt buộc mọi truyện dùng tất cả hệ; chỉ bắt buộc hệ đã xuất hiện phải có luật, giá, nguồn gốc và hậu quả.
- Nếu chưa khóa cảnh giới/luật riêng, agent dùng `CANON_GAP` nhưng không viết bí cảnh, thiên kiếp, đấu giá, tông môn như background rỗng.
- Leo thang có kiểm soát, cái giá tương xứng, nhất quán dài hạn và gài hạt giống là nguyên tắc xuyên suốt — chi tiết tại `Xianxia_World_Operating_System.md` §11.

### Thang Precedence (khi nhiều nguồn mâu thuẫn)

Áp dụng theo thứ tự; nguồn trên thắng nguồn dưới:

1. `PROJECT_DNA.md` + database canon của truyện.
2. Author Style / Worldbuilding guide của master đã chọn (`style_model`).
3. `Xianxia_consistency_rules.md` §2.1 (khung cảnh giới) — chỉ khi truyện chưa khóa hệ riêng.
4. Các guide chung còn lại (Texture, Progression, World Operating).

### Quy Tắc Chuyên-Biệt Thắng Tổng-Quát

Khi hai guide chung cùng cấp mâu thuẫn, quy tắc chuyên biệt (floor) là nền; quy tắc kia là **modifier cộng thêm**, không thay thế floor. Ví dụ đã chốt — thiên kiếp:

- `consistency_rules.md` §2.2.3 "kiếp nạn tương xứng cảnh giới" = **floor** xác định mức nền của kiếp.
- `Xianxia_World_Operating_System.md` §2.4 "cường độ tỷ lệ mức nghịch-thiên" = **modifier** cộng thêm trên floor.
- Kết quả: nhân vật cảnh giới cao (floor kiếp nặng) + thiên tư thấp (modifier nhẹ) → vẫn tính từ floor theo cảnh giới, modifier chỉ điều chỉnh trong biên, không kéo kiếp xuống dưới mức nền của cảnh giới đó.
