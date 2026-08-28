# STYLE_GUIDE.md — La Bàn Văn Phong (v1.5 Multiverse)

**Author:** Dũng Nguyễn  
**Project:** NovelKit  
**Version:** 2.1.06

> **Mục tiêu:** Đảm bảo tính nhất quán (Consistency) và độ sâu cảm xúc (Depth) từ chương 1 đến chương 1000 cho ĐA THỂ LOẠI. Mọi tác tử (Agents) phải tuân thủ nghiêm ngặt.

## 1. Mô Hình Thập Ngũ Đại Thần (15 Gods Paradigm)
Trong bản v1.5, văn phong không bị đóng cứng vào một quy chuẩn duy nhất. Nó được nội suy hoàn toàn dựa vào **Mã Đại Thần** mà bạn đã chọn trong `PROJECT_DNA.md`.

*Ví dụ về độ "Flex" của văn phong:*
- Nếu mã là **LC (Lưu Từ Hân - Khoa Huyễn):** Văn phong lạnh lẽo, hùng tráng, mô tả khoa học chính xác, nhịp điệu chậm dãi, tập trung vào sự vĩ mô của vũ trụ.
- Nếu mã là **TT (Hội Thuyết Thoại - Hệ Thống):** Văn phong tấu hài, bựa, nhịp điệu nhanh, sử dụng tiếng lóng, phá vỡ bức tường thứ tư.
- Nếu mã là **PN (Phỉ Ngã Tư Tồn - Ngôn Tình):** Văn phong xoáy sâu vào nội tâm, mô tả nỗi đau tinh tế, nhịp điệu trầm buồn.

=> **Quy tắc Tối Cao:** *Novel Agents — Prose Writer* PHẢI truy vấn file `SOUL.md` của mình để nạp tệp từ vựng và nhịp điệu tương ứng với Đại Thần.

## 2. Quy Tắc Hành Văn Tiêu Chuẩn (Áp dụng cho mọi Vũ trụ)
Dù là Đại Thần nào, *Prose Writer* cũng không được phép vi phạm 3 thiết luật sau:
1. **Show, Don't Tell:** Cấm tuyệt đối việc kể lể trạng thái tâm lý nhân vật nếu không có hành động, biểu cảm, hoặc hoàn cảnh đi kèm (VD: Thay vì viết "Hắn rất tức giận", hãy viết "Gân xanh nổi hằn trên mu bàn tay đang siết chặt của hắn").
2. **Cliffhanger Rule (Quy tắc Móc Câu):** Trừ khi là chương kết Arc, mọi chương phải kết thúc bằng một "Hook" (câu hỏi, mâu thuẫn mở, hoặc sự xuất hiện bất ngờ).
3. **No Infodump:** Không nhồi nhét quá 150 từ giải thích về Worldbuilding/Hệ thống/Công nghệ trong 1 phân đoạn liên tiếp. Phải chẻ nhỏ thông tin ra và rải vào hội thoại hoặc hành động.

## 3. Style Vault Integration (Kho Văn Phong Lai)
- Hệ thống Hybrid Memory sẽ thu thập các đoạn văn xuất thần (>= 9 điểm) và dán nhãn (Tagging).
- Khi Novel Agents Orchestrator gọi RAG Context:
    - *Combat / Action:* Tìm style dựa trên tag `[action, high-velocity]`.
    - *Emotional / Drama:* Tìm style dựa trên tag `[introspective, tear-jerker]`.
- *Prose Writer* **bắt buộc** phải mô phỏng Rhythm (nhịp điệu) của các đoạn được trích xuất từ Style Vault, không chỉ copy từ ngữ.

## 4. Quality Auditor Review Rubric (Tiêu chuẩn Chấm Điểm)
*Novel Agents — Quality Auditor* (Chân Nhân, Thẩm Phán, Thiên Đạo...) sẽ chấm điểm văn phong dựa trên:
- **Tone Consistency (0-10):** Văn phong có khớp với Đại Thần được chọn không? Có bị lọt từ vựng Tiên hiệp vào truyện Đô thị không?
- **Pacing (0-10):** Nhịp độ chương có phù hợp với mục đích của Outline không (Chương đánh nhau thì nhịp nhanh câu ngắn, chương giải đố thì nhịp chậm mô tả kỹ)?
- **Show, Don't Tell Ratio (0-10):** Có bị mắc lỗi kể lể (infodump) quá mức không?

*Bất kỳ lỗi rò rỉ từ vựng sai thể loại (VD: "Đan điền" xuất hiện trong truyện Khoa Huyễn) sẽ bị đánh rớt (Hard-fail) lập tức.*
