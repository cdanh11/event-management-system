# Hiệu năng và giao dịch

## Pagination

GET /events hỗ trợ status, q (tìm title), limit 1–100, offset hoặc cursor. Cursor là ID cuối trang trước, keyset theo (start_time, id). Không dùng cursor kèm offset khác 0. X-Next-Cursor được expose qua CORS; trang đủ limit có thể cần thêm một lần tải để xác nhận hết dữ liệu.

Index ix_events_status_start_time(status, start_time) hỗ trợ lọc status và sắp theo giờ. Migration 0001 là snapshot schema cố định; 0002 tạo index nếu chưa có. Không sửa metadata runtime để thay đổi lịch sử migration.

## Benchmark

Chạy trên PostgreSQL test riêng đã migration, từ Backend:

```powershell
$env:DATABASE_URL='postgresql+psycopg://evently:evently@localhost:5433/evently_test?connect_timeout=5'
.\.venv\Scripts\python.exe scripts/bench_events.py --rows 3000 --iters 20
Remove-Item Env:DATABASE_URL
```

Script tạo dataset, ANALYZE, so EXPLAIN ANALYZE trước/sau index và đo offset deep-page/cursor. Mọi thay đổi nằm trong một transaction và rollback cuối cùng, gồm cả index và dữ liệu tạm. Chỉ dùng DB test riêng vì DROP/CREATE index có thể khóa bảng trong lúc đo.

Các số liệu từng ghi trong phase cũ là phép đo local lịch sử, không phải cam kết hiệu năng bản hiện tại. Ghi lại dataset, máy, query plan và trung bình khi tái hiện; không kết luận từ một hệ số chung cho mọi workload.

## Giao dịch

Register khóa Event, kiểm tra capacity rồi commit registration/ticket/counter cùng giao dịch. Cancel và check-in theo thứ tự Event trước Registration/Ticket. UNIQUE bảo vệ trùng attendee/event và check-in/ticket. Refresh khóa dòng token trước khi rotate. Xem [test PostgreSQL](testing.md) để kiểm chứng tính đồng thời.

Dashboard dùng SQL COUNT cho tổng registrations/checkins, tránh nạp mọi bản ghi chi tiết vào RAM; danh sách event vẫn được trả đầy đủ nên tổng truy vấn không có độ phức tạp O(1). Chưa có load test xác nhận thông lượng nhiều người dùng hay hạ tầng production.

## Danh sách organizer và phép đo cuối

GET /organizer/events giới hạn theo owner, lọc status/q, sort soonest/popular, limit/offset; trả items/total/has_more. SQL COUNT và LIMIT/OFFSET chạy trước serialization. Dashboard dùng subquery event IDs để tổng hợp, không tạo danh sách toàn bộ ID trong Python.

Ngày 07/10/2026: PostgreSQL 16 local, 3000 rows bổ sung (3003 Published tổng), limit 20, 20 lần đo. EXPLAIN execution: 1.113 ms trước index, 0.154 ms sau index; deep offset trung bình 1.922 ms, cursor 0.961 ms. Dữ liệu/index benchmark được rollback. Đây là phép đo query local, không phải load test hoặc cam kết throughput.
