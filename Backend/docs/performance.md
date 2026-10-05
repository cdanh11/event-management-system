# Hiệu năng truy vấn (Tầng 3)

## Phân trang `GET /events`

| Kiểu | Cách dùng | Khi nào dùng |
| --- | --- | --- |
| Offset (mặc định, tương thích FE) | `?limit=20&offset=0` | Trang đầu, danh sách ngắn |
| Cursor keyset | `?cursor=<id cuối trang trước>` | Lướt sâu; server trả header `X-Next-Cursor` (rỗng khi hết) |

Cursor và offset không dùng chung (`400 CURSOR_OFFSET_CONFLICT`); cursor lạ
(`404 CURSOR_NOT_FOUND`). Keyset theo `(start_time, id)` nên đi thẳng từ anchor,
không quét-bỏ N dòng như `OFFSET`.

## Composite index

Migration `0002_event_status_start_index` tạo `ix_events_status_start_time(status, start_time)`,
phục vụ đúng truy vấn lọc `status` + sắp xếp `start_time` của `GET /events`.
Lưu ý drift đã xử lý: `0001` dùng `create_all` nên DB mới đã có index từ metadata —
`0002` dùng `if_not_exists=True` để chạy được cho cả DB mới lẫn DB cũ.

## Số liệu benchmark (PostgreSQL compose, 3000 rows, `scripts/bench_events.py`)

| Đo | Kết quả |
| --- | --- |
| `EXPLAIN ANALYZE`, chưa index | Seq Scan + Sort, **1.403 ms** |
| `EXPLAIN ANALYZE`, có index | Index Scan, **0.112 ms (~12.5x)** |
| Offset deep-page (`OFFSET 2980`, trung bình 20 lần) | **3.43 ms** |
| Cursor keyset (trung bình 20 lần) | **1.60 ms (~2.1x)** |

Tái hiện: `docker compose up -d db`, rồi `python scripts/bench_events.py --rows 3000 --iters 20`
(chạy `ANALYZE` trước khi đo, đo đúng shape query của endpoint, tự dọn dữ liệu benchmark).

## Chống over-booking

`register` khóa dòng event bằng `with_for_update()` và unique `(event_id, attendee_id)`,
minh chứng bằng `tests/test_concurrency_pg.py` trên PostgreSQL thật:
5 thread × event capacity 1 → `[201, 409, 409, 409, 409]`, `registered_count == 1`.
Test này skip khi thiếu `TEST_POSTGRES_URL` vì SQLite không có row lock:

```powershell
$env:TEST_POSTGRES_URL="postgresql+psycopg://evently:evently@localhost:5433/evently"
.\.venv\Scripts\python.exe -m pytest tests/test_concurrency_pg.py -q
```

## Dashboard O(1)

`/organizer/dashboard` đếm bằng SQL `func.count()`, không kéo toàn bộ ORM về RAM.
