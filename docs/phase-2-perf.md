# Phase 2 — Background & Tầng 3 perf (đã xong, chờ review)

## 2a. BackgroundTask gửi vé/QR khi register
- `app/services/notifier.py` — `send_ticket_email(to, title, code, qr)`: webhook thật nếu có
  `NOTIFY_WEBHOOK_URL`, ngược lại simulate (KHÔNG cần SMTP/email thật — ghi rõ giới hạn báo cáo).
- `routers/registrations.py` — sau commit, đọc kiểu nguyên thủy ra biến local rồi mới
  `add_task` (task nền chạy sau khi Session đóng nên cấm chạm ORM — tránh DetachedInstanceError).
- Client nhận `201` ngay; vé/QR gửi sau response. Test `test_register_sends_ticket_in_background`
  monkeypatch task nền và assert đúng email/code.

## 2b. Cursor pagination + composite index (số liệu PostgreSQL thật)
- `GET /events` thêm `cursor=<id>`: keyset `(start_time, id)`, header `X-Next-Cursor`
  (rỗng khi hết); cursor và offset không dùng chung (`400 CURSOR_OFFSET_CONFLICT`,
  cursor lạ `404 CURSOR_NOT_FOUND`). Offset giữ nguyên để FE Phase 1 tương thích.
- Migration `0002_event_status_start_index` + `Index("ix_events_status_start_time")`
  trong `models.py`. Lưu ý drift đã gặp: 0001 dùng `create_all` nên DB mới đã có index —
  0002 dùng `if_not_exists=True` để chạy được cho cả DB mới lẫn DB cũ (ca Chương 13).
- Benchmark `Backend/scripts/bench_events.py` (`--rows 3000 --iters 20`, PG compose,
  `ANALYZE` trước khi đo, đo đúng shape query của endpoint):

| Đo | Kết quả |
| --- | --- |
| EXPLAIN ANALYZE, chưa index | Seq Scan + Sort, Execution **1.403 ms** |
| EXPLAIN ANALYZE, có `ix_events_status_start_time` | Index Scan, Execution **0.112 ms (~12.5x)** |
| Offset deep-page (`OFFSET 2980`) trung bình 20 lần | **3.43 ms** |
| Cursor keyset trung bình 20 lần | **1.60 ms (~2.1x)** |

Kết luận: OFFSET phải quét+bỏ qua N dòng nên chậm dần theo trang; cursor đi thẳng từ anchor.
Index composite phục vụ đúng truy vấn lọc `status` + sắp xếp `start_time`.

## 2c. Concurrency test PostgreSQL thật
- `tests/test_concurrency_pg.py` — bỏ qua mặc định, chạy tay bằng
  `TEST_POSTGRES_URL=... pytest tests/test_concurrency_pg.py -q`.
- Kịch bản: event capacity=1, 5 thread đăng ký đồng thời → `[201, 409, 409, 409, 409]`,
  `registered_count == 1` (đã chạy pass trên PG compose, 2 lần liên tiếp).
- Email duy nhất mỗi lần chạy (idempotent) + cleanup raw SQL theo thứ tự FK.

## Cách review
1. `cd Backend; .\.venv\Scripts\python.exe -m pytest -q` → pass + 1 skipped.
2. `TEST_POSTGRES_URL=postgresql+psycopg://evently:evently@localhost:5433/evently python -m pytest tests/test_concurrency_pg.py -q` (cần `docker compose up -d db` trước).
3. `python scripts/bench_events.py --rows 3000 --iters 20` để tái hiện số liệu.
4. `cd Frontend; npm run lint; npm run build`.

## Giới hạn (Chương 13)
- SMTP/email thật chưa có — webhook/simulate.
- Broadcast WS vẫn in-memory single-process; đa instance cần Redis pub/sub.
- Benchmark trên 3000 rows local; dataset lớn hơn sẽ chênh lệch rõ hơn.
