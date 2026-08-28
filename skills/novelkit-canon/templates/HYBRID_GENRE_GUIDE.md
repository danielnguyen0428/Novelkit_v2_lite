# Hybrid Genre Guide — Quy Tắc Pha Trộn Thể Loại

> Reference doc cho `PROJECT_DNA_TEMPLATE.md` Section II.
> Chỉ đọc khi tác phẩm là Hybrid (kết hợp 2+ thể loại).

## Khi Nào Dùng Hybrid?

Khi tác phẩm kết hợp đặc trưng của 2 thể loại trở lên.
Ví dụ: Đô Thị + Tu Chân, Xuyên Không + Hệ Thống, Romance + Sci-Fi, Tiên Hiệp + Khoa Huyễn.

## Quy Tắc Routing

```
PRIMARY GENRE quyết định:
  ✅ Squad chính (agents nào viết)
  ✅ Consistency rules chính
  ✅ Style guide chính
  ✅ Đại Thần chọn từ pool genre chính

SECONDARY GENRE bổ sung:
  ✅ Canon pack phụ (đọc thêm consistency_rules + style)
  ✅ Worldbuilding elements từ genre phụ
  ✅ Từ vựng genre phụ ĐƯỢC PHÉP sử dụng (override blacklist)
  ❌ KHÔNG đổi squad — vẫn dùng squad genre chính
  ❌ KHÔNG pha trộn Đại Thần cross-genre (chọn 1 genre)
```

## Bảng Combo Phổ Biến

| Combo | Ví Dụ | Primary Squad | Canon Đọc Thêm | Lưu Ý |
|---|---|---|---|---|
| **Đô Thị + Tu Chân** | Tu chân giả trang trong thế giới hiện đại | `sub_agents_do_thi/` | `system/Xianxia/` | Từ vựng tu chân ĐƯỢC phép, ràng buộc xã hội hiện đại VẪN áp dụng |
| **Xuyên Không + Hệ Thống** | MC xuyên không có system hỗ trợ | `sub_agents_xuyen_khong/` | `system/Meta Genre/` | System là công cụ, bối cảnh lịch sử là nền |
| **Tiên Hiệp + Khoa Huyễn** | Tu chân trong vũ trụ có công nghệ (Star-Xianxia) | `sub_agents/` | `system/Sci-fi/` | Linh khí + Công nghệ cùng tồn tại, cần quy tắc tương tác rõ |
| **Ngôn Tình + Xuyên Không** | Tình yêu xuyên thời gian | `sub_agents_ngon_tinh/` | `system/Time Travel/` | Tình cảm là trục chính, bối cảnh lịch sử là gia vị |
| **Đô Thị + Hệ Thống** | Hệ thống trong thế giới hiện đại | `sub_agents_do_thi/` | `system/Meta Genre/` | System rules + Ràng buộc đô thị |
| **Khoa Huyễn + Hệ Thống** | System trong vũ trụ tương lai | `sub_agents_khoa_huyen/` | `system/Meta Genre/` | Hard SF rules vẫn áp dụng cho nền tảng |
| **Custom** | _(combo khác)_ | _chọn genre chiếm >50%_ | _genre còn lại_ | _ghi rõ quy tắc tương tác 2 hệ thống_ |

## Quy Tắc Từ Vựng Hybrid

```
Khi genre = hybrid:
  → Blacklist từ vựng của genre CHÍNH được NỚI LỎNG cho từ vựng genre PHỤ
  → Ví dụ: Đô Thị + Tu Chân → "đan điền", "linh khí" ĐƯỢC PHÉP dùng
  → Nhưng: vẫn CẤM từ vựng genre KHÔNG liên quan
    (vd: Đô Thị + Tu Chân → CẤM "mecha", "FTL", "gen biến dị")

Quy tắc xung đột:
  → Nếu consistency_rules chính ↔ phụ mâu thuẫn → CHÍNH THẮNG
  → Nếu style guide chính ↔ phụ mâu thuẫn → CHÍNH THẮNG
  → Quality Auditor kiểm tra CẢ HAI bộ rules
```
