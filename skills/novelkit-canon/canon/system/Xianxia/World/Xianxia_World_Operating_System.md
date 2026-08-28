# XIANXIA WORLD OPERATING SYSTEM
## Module Cấu Hình Vận Hành Giới Tu Chân — Agentic AI Tiên Hiệp
> **Phiên bản:** v3.00

> Module này bổ sung cho `Tu_Tien_Texture_Floor.md` và `Cultivation_Progression_System.md`. Texture trả lời "cảnh đọc có chất tu tiên không"; Progression trả lời "tu vi có tiến triển hợp lý không"; World Operating trả lời "thế giới tu chân có đang vận hành như một hệ sống thật không".

## Nguyên Tắc Không Conflict

> **Source of truth:** `Xianxia_Depth_Contract.md` §Không Conflict Rule.

Canon riêng (`PROJECT_DNA.md`, database, author style) luôn thắng guide chung. Guide chung không bắt buộc dùng tất cả hệ; chỉ bắt buộc hệ đã xuất hiện phải có luật, giá, nguồn gốc và hậu quả.

## 1. Secret Realm System — Bí Cảnh / Tiểu Giới / Cấm Địa

Bí cảnh không phải "dungeon loot". Mỗi bí cảnh phải có:

```yaml
secret_realm:
  name:
  type: [tien_phu_di_tich/tong_mon_cam_dia/tieu_gioi_tu_nhien/thuong_co_chien_truong/nhan_tao_tieu_gioi]
  origin: [ai tạo/tự nhiên hình thành/chiến trường nào để lại]
  opening_rule: [chu_ky/thien_tuong/chia_khoa/huyet_te/tong_mon_cho_phep]
  entry_limit: [canh_gioi/tuoi/thoi_gian/so_nguoi/huyet_mach]
  internal_law: [ap_che_canh_gioi/cam_than_thuc/thoi_gian_lech/linh_khi_doc/khong_gian_bat_on]
  rewards: [linh_thao/truyen_thua/phap_bao/cong_phap/tien_phu/dao_van]
  risks: [yeu_thu/co_quan/cam_che/ma_khi/quy_hon/tu_si_giet_nguoi_doat_bao/sup_do]
  aftermath: [tai_nguyen_doi_chu/truy_sat/thi_truong_bien_dong/tong_mon_mat_mat/nhan_qua_moi]
```

Scene bí cảnh phải cho thấy ít nhất 2 lớp: luật nội tại + tranh đoạt/hậu quả. Không viết "bí cảnh mở ra, mọi người vào lấy truyền thừa" nếu không có cấm chế, giới hạn, rủi ro, nguồn gốc hoặc cái giá.

### 1.1 Phân Loại: Di Tích Cổ / Bí Cảnh / Tiểu Giới

Ba loại địa điểm đặc biệt có luật vận hành khác nhau; agent phải chọn đúng loại và giữ nhất quán.

| Đặc điểm | Di Tích Cổ | Bí Cảnh | Tiểu Giới |
|---|---|---|---|
| Vị trí | Cố định trên đại lục | Ẩn giấu, không cố định hiển hiện | Độc lập, trong vật phẩm/kẽ hở không gian |
| Cách vào | Khám phá trực tiếp, vào lại được | Cần điều kiện mở (thời gian/tín vật/thực lực) | Cần được "công nhận" (huyết mạch, khế ước, phá cấm chế) |
| Độ ổn định | Tương đối ổn định, suy yếu theo thời gian | Đóng/mở theo chu kỳ | Có quy luật vận hành riêng, tự thành "trời đất" nhỏ |
| Quy luật thời gian | Giống bên ngoài | Thường giống bên ngoài | Có thể lệch (X năm trong = Y ngày ngoài) |
| Mức nguy hiểm | Trung bình, giảm dần qua khai thác | Cao, có trận pháp/thủ hộ tự động | Biến thiên lớn — thiên đường tu luyện hoặc tử địa |
| Loại thu hoạch | Di vật rải rác, manh mối lịch sử | Tài nguyên tập trung | Truyền thừa hệ thống, không gian tu luyện riêng |

### 1.2 Cơ Chế Kích Hoạt / Mở

Điều kiện mở nên chọn từ (hoặc kết hợp) các nhóm sau, ghi rõ ngay lần đầu xuất hiện:

- Thiên văn/thiên thời: sao chiếu mệnh, nhật/nguyệt thực, linh khí dâng cao theo mùa — tạo tính chu kỳ để cài "đếm ngược" hợp lý.
- Tín vật/manh mối: ngọc giản cổ, bản đồ tàn khuyết — tạo động lực nhân vật phải tìm kiếm trước khi vào.
- Huyết thống/tư cách: chỉ hậu nhân hoặc người cùng thuộc tính đặc biệt mới vào được — hợp cốt truyện thân thế bí ẩn.
- Thực lực tối thiểu/tối đa: cấm chế chặn tu vi quá thấp để tránh chết oan, hoặc quá cao để ép thế hệ trẻ tự lực — giữ công bằng tương đối giữa các phe.

Cơ chế thời gian (đặc biệt quan trọng với Tiểu Giới): phải quy định rõ tỷ lệ thời gian trong/ngoài ngay khi thiết lập và giữ nhất quán xuyên suốt. Đây là chi tiết rất dễ viết sai logic nếu không ghi chú lại từ đầu. Nếu dùng làm nơi ẩn cư tu luyện dài hạn, cần cân nhắc tỷ lệ này để tránh nhân vật mạnh lên phi lý so với dòng thời gian bên ngoài.

### 1.3 Phân Cấp Nguy Hiểm Theo Cảnh Giới (khung gợi ý)

| Cấp bậc | Cảnh giới phù hợp | Loại thủ hộ thường gặp | Phần thưởng tương ứng |
|---|---|---|---|
| Hạ Phẩm | Luyện Khí – Trúc Cơ | Trận pháp đơn giản, dã thú biến dị yếu | Linh thạch, dược liệu phổ thông |
| Trung Phẩm | Kim Đan – Nguyên Anh | Cấm chú, hộ vệ thú cấp Nguyên Anh | Công pháp trung cấp, đan dược quý |
| Thượng Phẩm | Hóa Thần – Luyện Hư | Ý chí tàn lưu chủ nhân cũ, trận pháp phức hợp | Truyền thừa thượng thừa, pháp bảo |
| Cực Phẩm/Cấm Địa | Hợp Thể trở lên | Tồn dư sức mạnh cấp Thần/Tiên, dị biến thời-không | Cơ duyên phá giới hạn cảnh giới, manh mối Phi Thăng |

### 1.4 Nguyên Tắc "Thưởng Đi Kèm Rủi Ro"

Giá trị phần thưởng phải tỷ lệ thuận với mức nguy hiểm và số thế lực tranh đoạt; không thiết kế bí cảnh "toàn lợi không hại". Chọn kết hợp (không dùng hết cùng lúc để tránh rối):

- Trận pháp công kích tự động hoặc cấm chú trói buộc thần thức.
- Hồn ma/tàn niệm kiểm tra tư cách người vào (đạo tâm, thân phận, thử thách triết lý).
- Sinh vật biến dị do hấp thụ linh khí dị thường lâu năm.
- Không gian lồng không gian (bí cảnh giả trong bí cảnh thật — tạo twist).
- Thời gian đảo loạn/vòng lặp (nhân vật phải tìm quy luật để thoát — hợp chương giải đố).

### 1.5 Checklist Trước Khi Hoàn Thành Scene Bí Cảnh / Di Tích

- Đã có ít nhất một thế lực/đối thủ khác cùng xuất hiện tranh đoạt chưa (tránh độc chiếm quá dễ)?
- Phần thưởng nhân vật nhận được có đi kèm cái giá hoặc giới hạn sử dụng rõ ràng không?
- Quy luật không gian/thời gian của địa điểm đã nêu rõ và sẽ giữ nhất quán nếu xuất hiện lại chưa?
- Mức nguy hiểm có phù hợp cảnh giới hiện tại của MC (không quá dễ, không vô lý khó) không?
- Có để lại ít nhất một "hạt giống" cho cốt truyện sau (manh mối, kẻ thù mới, món nợ ân tình) không?

## 2. Heavenly Tribulation System — Thiên Kiếp / Lôi Kiếp / Kiếp Nạn

> **Nguyên tắc cốt lõi:** `Xianxia_consistency_rules.md` §2.2.3 — kiếp nạn tương xứng cảnh giới, là cơ hội narrative, không chỉ power-up.
> **Phân loại + phân cấp + hậu quả thất bại + quy tắc AI:** các mục dưới đây bổ sung chi tiết.

Thiên kiếp là cơ chế kiểm tra, không chỉ là sét đánh cho đẹp cảnh.

```yaml
tribulation:
  trigger: [dai_canh_gioi/nghich_thien_cong_phap/luyen_bao/yeu_thu_hoa_hinh/loi_the_dao_tam]
  type: [loi_kiep/tam_ma_kiep/nhan_qua_kiep/nghiep_hoa_kiep/thien_dao_van_tam]
  foreshadow: [linh_ap_bat_thuong/may_kiep/thien_co_roi_loan/dao_tam_bat_an]
  preparation: [dia_diem/tran_phap/phap_bao_chong_loi/dan_duoc/ho_phap/duong_lui]
  test_axis: [than_the/dao_tam/nhan_qua/cong_phap/can_co]
  failure_cost: [thuong_can_co/mat_tho_nguyen/tam_ma_luu_lai/tan_cong_than_thuc/tau_hoa]
  aftermath: [on_co_canh_gioi/loi_ngan/co_duyen_moi/ke_thu_biet_vi_tri/luat_troi_danh_dau]
```

Theo Vọng Ngữ, thiên kiếp cần kế hoạch chi tiết: địa điểm, trận pháp, linh thạch, đan dược, pháp bảo, hộ pháp. Theo Nhĩ Căn, thiên kiếp nên chất vấn đạo tâm, số mệnh, nhân quả và lựa chọn của nhân vật.

### 2.1 Phân Loại Các Dạng Kiếp Nạn

- Lôi Kiếp: sét trời đánh xuống, phổ biến nhất, dùng để tịnh hóa thân thể và linh hồn.
- Hỏa Kiếp / Băng Kiếp: thiêu đốt hoặc đóng băng đạo thể, thường gắn với thuộc tính tu luyện của nhân vật.
- Tâm Kiếp: ảo cảnh tấn công tâm trí, gợi lại sợ hãi/dục vọng/quá khứ đau thương; không gây tổn thương vật lý nhưng đạo tâm không vững sẽ tự sụp đổ.
- Nghiệp Kiếp: oan hồn/nghiệp lực của sinh linh nhân vật từng sát hại quay về đòi nợ; mức độ nặng nhẹ tỷ lệ thuận với "nghiệp" đã gây — hữu dụng để cài cắm hậu quả nhân-quả từ các chương trước.
- Kiếm Kiếp / Thú Kiếp: dành cho tu sĩ luyện kiếm hoặc yêu thú, kiếp nạn hiện thân dưới dạng tương ứng với đạo của họ.
- Đại Kiếp Phi Thăng: kiếp cuối cùng, thường là Tam Tai (Phong/Hỏa/Lôi) hoặc Thiên Binh Thiên Tướng hợp lực; đóng vai trò "boss cuối" mỗi khi rời một tầng thế giới để lên cao hơn.

### 2.2 Phân Cấp Theo Cảnh Giới (khung gợi ý)

| Cảnh giới đột phá | Loại kiếp tương ứng | Mức nguy hiểm | Tỷ lệ thành công gợi ý |
|---|---|---|---|
| Trúc Cơ -> Kim Đan | Lôi Kiếp nhỏ | Thấp | ~70-80% |
| Kim Đan -> Nguyên Anh | Lôi Kiếp + Tâm Kiếp | Trung bình | ~50-60% |
| Nguyên Anh -> Hóa Thần | Hỏa/Băng Kiếp + Nghiệp Kiếp | Cao | ~30-40% |
| Hóa Thần -> Luyện Hư | Tam Tai nhỏ (luân phiên) | Rất cao | ~15-20% |
| Đại Thừa -> Độ Kiếp | Đại Kiếp toàn diện | Cực hạn | ~5-10% |
| Độ Kiếp -> Phi Thăng | Phi Thăng Kiếp (đứt liên kết hạ giới) | Một đi không trở lại | Biến thiên theo cốt truyện |

### 2.3 Ba Mức Hậu Quả Khi Thất Bại

Nên có ít nhất 3 mức để tạo độ căng:

- Tổn thương đạo cơ: tụt cảnh giới, cần thời gian phục hồi.
- Tàn phế: hư hại kinh mạch/đan điền, mất khả năng tu luyện — hạt giống cho tuyến "báo thù" hoặc "y đạo".
- Hồn tiêu phách tán: tử vong thật — chủ yếu dùng cho NPC, hiếm khi áp lên MC trừ khi mở đầu là trùng sinh/chuyển sinh.

### 2.4 Quy Tắc Cho AI

- Không dùng trợ giúp ngoại lực để hóa giải Thiên Kiếp một cách rẻ tiền; nếu có hỗ trợ, phải kèm giá: tiêu hao bảo vật cực hiếm, người hỗ trợ bị tổn thương nặng, hoặc chỉ giảm nhẹ chứ không miễn trừ.
- Cường độ kiếp nạn tỷ lệ thuận với mức "nghịch thiên" của nhân vật — thiên tư cao, nhiều bí bảo hộ thể, hoặc tu luyện tà đạo thì kiếp nạn nặng hơn người bình thường. Đây là cơ chế bù trừ giúp MC không trở nên quá dễ.
  > **Quan hệ với `Xianxia_consistency_rules.md` §2.2.3:** loại/mức kiếp tương xứng cảnh giới (§2.2.3) là **floor** (nền); mức "nghịch thiên" ở đây là **modifier CỘNG THÊM** lên floor đó, không thay thế. Vậy nhân vật cảnh giới cao (floor nặng) + thiên tư thấp (modifier nhẹ) vẫn chịu kiếp theo floor cảnh giới, chỉ giảm phần modifier. Thứ tự phân xử đầy đủ: `Xianxia_Depth_Contract.md` §Không Conflict Rule.
- Mỗi lần độ kiếp là một điểm neo thời gian/cao trào — không lặp công thức giống nhau liên tiếp; nên đa dạng hóa: lúc cận kề cái chết, lúc là cơ hội giác ngộ đạo tâm, lúc bị kẻ địch lợi dụng thời điểm yếu nhất để tập kích.
- Có thể dùng Nghiệp Kiếp như công cụ hé lộ lore/quá khứ nhân vật mà không cần lộ liễu qua đối thoại.

## 3. Heavenly Dao / Karma / Luck Law

Mỗi thế giới Xianxia cần câu trả lời riêng:

- Thiên Đạo vô tình, có ý chí, hay là cơ chế tự nhiên?
- Lời thề đạo tâm có phản phệ không?
- Giết người đoạt bảo tạo nhân quả gì?
- Khí vận có thể tích lũy, cướp, chuyển, đốt hay không?
- Người nghịch thiên bị đánh dấu bằng dấu hiệu nào?
- Có thể phá thiên mệnh không, và giá phải trả là gì?

```yaml
heavenly_law:
  dao_stance: [vo_tinh/co_y_chi/bi_thuong_ton/bi_thao_tung]
  karma_rule:
  oath_backlash:
  luck_mechanics:
  fate_breaking_cost:
  visible_omens:
```

## 4. Resource Economy & Cultivation Ecology

Tài nguyên phải có nguồn gốc, chủ sở hữu, giá trị và vòng đời.

- Linh mạch: cấp bậc, trữ lượng, ai kiểm soát, suy kiệt ra sao.
- Linh thạch: đơn vị, giá trị theo cảnh giới, cách khai thác.
- Đan dược: đan phương, nguyên liệu, tỉ lệ thành đan, độc tính/tạp chất.
- Pháp bảo: cấp bậc, vật liệu, người luyện, giới hạn, hao mòn.
- Linh thảo/yêu đan: môi trường sinh trưởng, chu kỳ, tranh đoạt.

Vọng Ngữ standard: tài nguyên là kinh tế học. Ai kiểm soát đan dược, linh mạch, đấu giá và thông tin bí cảnh thì có quyền lực.

## 5. Sect / Faction Operation

> **Cấu trúc chức vụ, quy mô, luật tông môn:** `Xianxia_consistency_rules.md` §3.3.
> **Faction Relationship Matrix & enforcement rules:** `Xianxia_consistency_rules.md` §3.3.1.

Bổ sung: Tông môn không chỉ là tên riêng. Mỗi thế lực quan trọng cần có:

```yaml
faction:
  hierarchy: [ngoai_mon/noi_mon/chan_truyen/chhap_su/truong_lao/chuong_mon]
  resources_controlled:
  laws: [dau_phap/giet_nguoi/phan_bo_tai_nguyen/phan_mon]
  daily_operations: [nhiem_vu_duong/dan_phong/tang_kinh_cac/linh_dien/hinh_duong]
  rivalries:
  structural_weakness:
  public_face_vs_hidden_truth:
```

Cảnh tông môn phải có cấp bậc, lợi ích, quy củ hoặc áp lực. Không viết tông môn như trường học/hoàng cung có phong cách hiện đại.

## 5.1 Map Registry & Travel Consistency

> **Source of truth:** `Xianxia_consistency_rules.md` §5.1.1 — MAP_REGISTRY (9 fields + quy_tắc).

Mỗi địa danh/tuyến đường quan trọng phải có bản ghi Map Registry trước khi nhân vật đi qua, đặc biệt là bí cảnh, di tích, cấm địa, truyền tống trận, thượng giới và tiểu giới.

Các field:

```
location / region_or_realm_layer / location_controller
travel_route / travel_time / entry_rule
route_cost / resource_or_danger / last_seen_or_changed
```

Không cho phép nhân vật "rời nơi A đến nơi B" mà không biết đường đi, thời gian, ai kiểm soát cổng vào, điều kiện vào, và cái giá. Nếu cần dùng route chưa có canon, agent phải ghi `CANON_GAP` và nêu rõ thông tin thiếu thay vì tự thêm địa danh/tuyến đường.

Quy tắc chi tiết: xem `Xianxia_consistency_rules.md` §5.1.1.

## 5.2 Grand Tournament — Đại Pháp Hội / Đại Tỷ Võ

Pháp hội/tỷ võ là cơ chế chọn lọc và xếp hạng thiên tài, phân chia tài nguyên và vị thế giữa các thế lực. Không viết như một trận đấu thể thao thuần túy; mỗi pháp hội cần mục đích, quy củ, phần thưởng và hậu quả chính trị.

```yaml
grand_tournament:
  host: [tong_mon/the_gia/lien_minh/hoang_trieu/bi_canh_cho_phep]
  purpose: [chon de tu chan truyen/phan tai nguyen/xep hang thien kieu/suat vao bi canh/lien minh chinh tri]
  qualification: [canh_gioi/tuoi/than_phan/thanh_tich_truoc]
  rules: [cam_sat/gioi_han_phap_bao/vong_loai/cam_che_trong_truong]
  reward: [tu_cach_de_tu_chan_truyen/cong_phap_that_truyen/danh_hieu_thien_kieu_bang/suat_bi_canh/hon_uoc_lien_minh]
  aftermath: [an_oan_moi/thay_doi_vi_the/the_luc_de_y/no_an_tinh]
```

Quy tắc cho AI:

- Tránh để MC thắng áp đảo phẳng lặng từ đầu đến cuối — cần ít nhất một đối thủ "không thể đánh giá thấp" và một biến cố bất ngờ phá vỡ trật tự thi đấu dự kiến.
- Pháp hội cấp cao nên thấp thoáng một thế lực/cường giả vượt xa tầm MC ở thời điểm đó, để gieo động lực vươn lên và làm nền cho cao trào sau.
- Không dùng quá 2-3 đại pháp hội theo cùng công thức mở-đấu-kết liên tiếp; nên thay đổi nhịp (có hội bị phá giữa chừng, có hội MC chỉ quan sát/ảnh hưởng từ xa).

## 5.3 Inter-World War — Chiến Tranh Giữa Các Thế Giới / Đại Lục

Nguyên nhân điển hình (chọn một hoặc kết hợp để tránh chiến tranh vô cớ): linh khí/tài nguyên một thế giới cạn kiệt buộc xâm chiếm để sinh tồn; một thông đạo/khe nứt không gian đột ngột mở ra do dư chấn đại kiếp hoặc cấm chế cổ bị phá; mối thù từ thời đại trước (chiến tranh Thần-Ma cổ xưa) tái phát theo chu kỳ định mệnh; chủng tộc khác (Yêu/Ma/Cổ tộc) chủ động mở rộng lãnh địa sinh tồn.

| Quy mô | Bên tham chiến | Giai đoạn truyện phù hợp |
|---|---|---|
| Tông môn chiến | 2 tông môn nhỏ | Đầu truyện, rèn luyện nhân vật |
| Quốc chiến | Vài quốc gia/thế gia trong 1 đại lục | Giữa truyện, nhân vật bắt đầu có ảnh hưởng |
| Chủng tộc chiến | Nhân tộc vs Yêu/Ma tộc | Cao trào, nhân vật trở thành nhân tố trọng yếu |
| Giới chiến | Liên minh đa thế giới vs đại kiếp diệt thế | Cao trào cuối/đại kết |

Quy tắc cho AI:

- Giới hạn sự can thiệp của cường giả tối cao (do đạo quy cổ, cấm chế thiên đạo, hoặc họ đang bận đối phó hiểm họa ở tầng cao hơn) — tránh để "ông trời" giải quyết hết xung đột trong một chương, làm nỗ lực của MC trở nên vô nghĩa.
- Chiến tranh lớn cần có "tiền chấn" — tin tức rò rỉ, trinh sát, chuẩn bị lực lượng — kéo dài qua nhiều chương trước khi nổ ra, để quy mô có cảm giác hợp lý.
- Cần hậu quả thực sự: mất mát nhân vật phụ quan trọng, thay đổi bản đồ chính trị, tài nguyên tổn hại — không kết thúc "sạch sẽ" như chưa từng xảy ra.

## 6. Ancient Era / Ruins / Inheritance

Di tích và truyền thừa phải gắn với lịch sử:

- Kỷ nguyên nào để lại?
- Ai tạo ra, vì sao mất?
- Cấm chế bảo vệ hoạt động theo logic nào?
- Truyền thừa chọn người theo tiêu chí gì?
- Chủ nhân cũ để lại chấp niệm, di nguyện, bẫy hay nhân quả nào?
- Nếu MC lấy truyền thừa, ai mất lợi ích?

Nhĩ Căn/Thần Đông standard: lịch sử là tầng tầng lớp lớp; mỗi di tích là vết nứt của một kỷ nguyên cũ, không phải kho đồ ngẫu nhiên.

### 6.1 Dị Bảo Cổ Đại & Tiên Cơ Thất Truyền

Di vật, công pháp hoặc cơ duyên còn sót lại từ một thời đại đã lụi tàn (Thượng Cổ, Viễn Cổ, hoặc thời Thần-Ma đại chiến), thường vượt xa trình độ hiện tại — đóng vai trò "wildcard" giúp nhân vật hoặc thế lực đột phá giới hạn thông thường.

Phân loại:

- Pháp bảo/vũ khí cổ: sức mạnh vượt cấp, có thể có ý thức riêng, cần thệ ước máu hoặc thử thách tư cách để nhận chủ.
- Truyền thừa: công pháp/ký ức của cường giả đã mất, phong ấn trong không gian đặc biệt, có bài kiểm tra tư cách trước khi truyền lại.
- Sinh thể cổ đại: yêu thú/thần thú bị phong ấn, khi tỉnh có thể là đồng minh hoặc kẻ thù tùy cách đối xử.
- Không gian dị biệt: tiểu thế giới phong ấn (xem §1.1 và các mục Secret Realm).

Quy tắc cho AI:

- Bảo vật/truyền thừa cổ đại không nên rơi vào tay MC miễn phí và dễ dàng; luôn kèm máu thệ/khế ước, mạo hiểm tính mạng, hoặc đánh đổi tương đương (ký ức, tuổi thọ, một phần tu vi).
- Sức mạnh từ ngoại lai cần có giới hạn sử dụng (số lần dùng, điều kiện kích hoạt, thời gian hồi, hoặc phản tác dụng khi dùng quá mức) để nhân vật vẫn cần tự thân tu luyện thay vì chỉ dựa "hack".
- Dùng để hé lộ lore thời đại trước và làm động lực tranh đoạt giữa nhiều thế lực — tăng xung đột khi nhiều phe cùng nhắm một bảo vật.

## 7. Daily Cultivator Life & Professions

Đời thường của tu sĩ phải khác phàm nhân:

- Động phủ, nhập định, dưỡng thương, ổn cố cảnh giới.
- Phường thị, đấu giá, nhiệm vụ đường, truyền tin bằng ngọc giản/phù lục.
- Luyện đan, luyện khí, phù lục, trận pháp, ngự thú, linh thực.
- Quan hệ thuê mướn: hộ pháp, khách khanh, tản tu, dân sự.

Mỗi scene đời thường nên có ít nhất một hệ vận hành: tài nguyên, quy củ, thần thức, pháp bảo, linh khí, nhân quả, cấp bậc tông môn.

## 8. Non-Human Cultivation

Nếu xuất hiện yêu thú/linh thú/quỷ tu/ma tu, phải khóa luật:

- Yêu thú tu luyện bằng yêu đan, huyết mạch, lăn xác hay thiên kiếp hóa hình?
- Linh thú là bạn đồng hành, tài nguyên, hay chủng tộc có xã hội?
- Quỷ tu dùng âm khí/hồn phách và bị giới hạn bởi dương khí ra sao?
- Ma tu mạnh nhanh nhưng đối mặt với ma hóa, mất lý trí, nghiệp lực nào?

## 8.1 Owned Spirit Beast System

> **Registry schema (fields & format):** `Xianxia_consistency_rules.md` §5.1.1 — OWNED_SPIRIT_BEAST_REGISTRY.
> **Enforcement rules:** `Xianxia_consistency_rules.md` §5.1.1 — LUẬT_4 (track song song), LUẬT_5 (linh thú & pháp bảo Chí Tôn).

Linh Thú sở hữu không phải công cụ triệu hồi rồi biến mất. Nó là một mảnh ghép của Đạo nhân vật chính: có lai lịch, trí nhớ, lộ trình phát triển, lý do ký khế ước, và có thể giữ một phần đáp án cho câu hỏi lớn của truyện đến cuối truyện.

Khi MC có Linh Thú sở hữu, phải khóa:

- Nguồn gốc: loài, tuổi linh, huyết mạch, ký ức riêng, bí mật cuối truyện đang che.
- Lý do chấp nhận khế ước: ân tình, huyết luyện, cộng hưởng Đạo, bị ép bởi sinh tử, hoặc mục tiêu riêng; không thuần phục vô lý.
- Năng lực lõi: bẩm sinh, phát triển theo cảnh giới MC, năng lực cấm, điều kiện kích hoạt và giá phải trả.
- Linh trí và tính cách: mức linh trí, thói quen riêng, điều tuyệt đối không làm, quan điểm khi MC sai hoặc liều lĩnh.
- Ràng buộc vật lý: hình thái thường trú, tiêu hao khi triệu hồi, cooldown sau năng lực cấm, hậu quả nếu bị thương.
- Quan hệ với MC: tầng khế ước hiện tại, lịch sử cảm xúc, điều kiện nâng tầng tiếp theo.

Không cho phép: linh thú xuất hiện -> dùng -> biến mất không hậu quả; linh thú mạnh hơn MC nhiều bậc mà chịu phục dễ dàng; linh thú không có quan điểm riêng. Linh thú được phép không đồng ý, bỏ đi tạm thời, trợ giúp trễ, hoặc gây xung đột với pháp bảo vì lý do nội tại.

## 8.2 Supreme Dao Artifact System

> **Registry schema (fields & format):** `Xianxia_consistency_rules.md` §5.1.1 — SUPREME_DAO_ARTIFACT_REGISTRY.
> **Enforcement rules:** `Xianxia_consistency_rules.md` §5.1.1 — LUẬT_5 (linh thú & pháp bảo Chí Tôn).

Pháp bảo Chí Tôn không bị sở hữu; chúng chọn người. MC không "lấy" được, chỉ được công nhận. Một món pháp bảo Chí Tôn thường có tính duy nhất trong vũ trụ, nguồn gốc từ thực thể hoặc Đạo ngoài quy tắc thông thường, có khả năng trưởng thành cùng tu vi và cuối cùng hóa thành một phần Đạo quả của MC.

Khi dùng pháp bảo Chí Tôn, phải khóa:

- Bản chất Đạo: hiện thân cho Thời gian, Không gian, Hủy Diệt, Tạo Hóa, Nhân Quả, Luân Hồi, hoặc một Đại Đạo riêng; cộng hưởng hay xung đột với Đạo MC.
- Lịch sử và ký ức: từng có chủ trước không, kết cục chủ cũ, quan điểm của pháp bảo với chủ cũ, lý do công nhận MC hiện tại.
- Tầng lực: tầng thường dùng, tầng toàn lực, tầng cấm thuật/bản nguyên; mỗi tầng có điều kiện kích hoạt, tiêu hao và giới hạn.
- Giá phải trả: giá thường xuyên, giá tích lũy, giá catastrophic nếu vượt giới hạn.
- Phản ứng môi trường: người/địa điểm khiến pháp bảo thức tỉnh, kẻ thù thiên nhiên, vùng phong ấn hoặc nhiễu không gian/thời gian.
- Tăng trưởng: điều kiện khai mở tầng lực mới gắn với đột phá cảnh giới, hiểu thêm Đạo, vượt kiếp nạn, hoặc chấp nhận một mất mát.

Trước mỗi scene dùng linh thú/pháp bảo, tự kiểm: MC đang ở tầng khế ước nào, linh thú có lý do nội tại không, pháp bảo dùng tầng lực nào, giá đã tính chưa, hậu quả có carry sang scene sau không, hai hệ có mâu thuẫn không, và MC có thật sự hiểu hết năng lực đang dùng không.

## 9. Upper Realm / Ascension / World Layering

Truyện dài cần biết tầng giới:

- Nhân Giới/Linh Giới/Tiên Giới khác nhau về linh khí, pháp tắc, thời gian, thiên đạo.
- Điều kiện phi thăng là gì?
- Lên giới cao có bị trở thành kẻ yếu lại không?
- Người thượng giới có can thiệp hạ giới bằng cách nào?
- Mỗi giới có tiền tệ, tông môn, cảnh giới, thiên kiếp riêng không?

## 10. Agent Checklist

Trước khi viết cảnh có bí cảnh/thiên kiếp/đấu giá/tông môn/di tích/pháp hội/chiến tranh liên giới/dị bảo cổ:

- Hệ này đã có luật vận hành chưa?
- Ai kiểm soát tài nguyên?
- Nguồn gốc lịch sử là gì?
- Giá phải trả nếu thành công/thất bại là gì?
- Hậu quả sau scene có đổi memory/PLAN/GOAL_TRACKER không?
- Có đang lặp lại texture rỗng: "mở ra, lấy được, vượt qua" không?

Reviewer phải fail nếu thế giới chỉ có tên gọi tiên hiệp mà không có luật, tài nguyên, quy củ, nhân quả hoặc hậu quả.

## 11. Nguyên Tắc Xuyên Suốt

Áp dụng cho mọi cơ chế hệ thống (thiên kiếp, pháp hội, chiến tranh, bí cảnh, di tích, dị bảo):

- Leo thang có kiểm soát: mỗi thử thách mới nên khó hơn lần trước nhưng không nhảy cấp đột ngột — nhân vật thắng nhờ chuẩn bị/trưởng thành, không nhờ may mắn liên tục.
- Cái giá tương xứng: mọi sức mạnh/cơ duyên đột biến (vượt kiếp thành công, nhặt được dị bảo, thoát khỏi bí cảnh tử địa) phải đi kèm tổn thất hoặc ràng buộc — tránh cảm giác "ăn không".
- Tính nhất quán dài hạn: một khi cơ chế (tỷ lệ thời gian, loại kiếp, cấp bậc bí cảnh) đã nêu trong một chương, các chương sau phải tuân theo đúng quy tắc đó trừ khi có lý do lore rõ ràng để thay đổi.
- Gài hạt giống (foreshadowing): mỗi sự kiện hệ thống lớn nên để lại ít nhất một manh mối/mâu thuẫn chưa giải quyết để dẫn dắt sang cung truyện tiếp theo.
