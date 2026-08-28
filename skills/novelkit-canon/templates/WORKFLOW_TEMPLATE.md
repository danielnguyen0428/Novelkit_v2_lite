# WORKFLOW_TEMPLATE.md — Master Multiverse Pipeline

> **Ghi chú:** Đây là khung luồng xử lý tự động của hệ thống từ lúc setup cho đến khi hoàn thành vòng lặp của một chương. Workflow này áp dụng cho TẤT CẢ các thể loại (Tiên hiệp, Khoa huyễn, Đô thị, v.v.).

## 1. Pipeline Automation (Phases 1-4)
- **Phase 1 (Khai Thiên - Khởi tạo):** 
    - Lãng Khách nhận `PROJECT_DNA.md`.
    - `sessions_spawn` (`[Character Architect]` + `[World Builder]` của Vũ trụ tương ứng chạy SONG SONG).
    - Khởi tạo Data gốc: Cảnh giới, Nhân vật, Lưới quan hệ.
- **Phase 2 (Bố Cục - Outline):**
    - Lãng Khách chạy lệnh RAG lấy ngữ cảnh.
    - `sessions_spawn` (`[Plot Weaver]` - Dệt Outline 3-5 Chương).
- **Phase 3 (Chấp Bút - Drafting):**
    - Lãng Khách thu thập: `Outline` + `RAG Context` + `Style Vault Context` (Văn mẫu Đại Thần).
    - `sessions_spawn` (`[Prose Writer]` - Chấp bút).
- **Phase 4 (Đạo Kiếp - Quality Audit):**
    - `sessions_spawn` (`[Quality Auditor]` - Chấm điểm, kiểm tra OOC, check Logic).
    - Pass (>=85): Chuyển sang `sync` để cập nhật `memory/Memory.md`, `.rag.sqlite3`, `.vector_db/` và Phase B memory.
    - Sau mỗi `sync`, control plane tự giữ rolling window 3-5 chương bằng cách seed tiếp batch kế nếu backlog phía trước xuống dưới ngưỡng.
    - Fail (<85): Trả về Phase 3. Thất bại 3 lần: Kích hoạt Circuit Breaker, gọi Human.

## 2. System Variables (Cấu hình)
- **LLM Writer/Reviewer:** `gemini-3.1-pro-preview` / `claude-sonnet-4-6`
- **LLM Embeddings:** `nomic-embed-text` qua `ollama` (mặc định hiện tại)
- **Vector DB Path:** Phase A lưu tại `.vector_db/`; Phase B lưu riêng tại `.mem0/qdrant/` bên trong mỗi folder truyện.

## 3. Style Integration Protocol (15 Gods)
- Văn phong được quyết định hoàn toàn bởi trường `style_model` (Mã Đại Thần) trong `PROJECT_DNA.md`.
- `system/[genre]/*` là shared canon cho rule, consistency, mood và giới hạn của thể loại.
- `SOUL.md` nội bộ của tổ đội chỉ là prompt specialization để thực thi nhiệm vụ tốt hơn.
- Nếu `SOUL.md` mâu thuẫn với `system/[genre]/*`, shared canon trong `system/` thắng.
