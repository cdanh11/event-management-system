# Tài liệu đồ án Evently

Thư mục này chứa toàn bộ tài liệu tiến trình, minh chứng kỹ thuật và báo cáo
của đồ án (tính đến lúc hoàn thành code).

## Đọc theo thứ tự

| File | Nội dung |
| --- | --- |
| [`roadmap.md`](roadmap.md) | Mục tiêu, phạm vi Tầng 1/2/3, lộ trình phase và tiêu chí review từng phase |
| [`phase-0-websocket.md`](phase-0-websocket.md) | Review Phase 0: WebSocket realtime + dashboard `/organizer/live` |
| [`phase-1-contract.md`](phase-1-contract.md) | Review Phase 1: Pydantic 422, pagination, DELETE, Swagger errors |
| [`phase-2-perf.md`](phase-2-perf.md) | Review Phase 2: background task, cursor/index/benchmark, concurrency test |
| [`gioi-han-ky-thuat.md`](gioi-han-ky-thuat.md) | Giới hạn đã biết + quyết định thiết kế (nguyên liệu Chương 13 báo cáo) |
| [`Bao_cao_Evently_DRAFT.docx`](Bao_cao_Evently_DRAFT.docx) | Báo cáo toàn văn (bản nháp chờ duyệt nội dung) |
| [`Bien_ban_bao_cao.docx`](Bien_ban_bao_cao.docx) | Khung/biên bản mẫu của môn (giữ nguyên, không sửa) |
| [`assets/`](assets/) | Minh chứng hình ảnh: ERD (`erd.png`), Swagger và giao diện (`*.png`) |

## Quy ước

- Mỗi phase có đúng một file review; chỉ sang phase sau khi review xong (ghi trong `roadmap.md`).
- Số liệu trong tài liệu (test, coverage, benchmark) phải tái hiện được bằng lệnh
  ghi trong chính file đó; số liệu lỗi thời thì cập nhật, không xóa lịch sử phase.
