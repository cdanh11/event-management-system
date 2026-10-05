# Nguyên liệu Chương 13 — Giới hạn kỹ thuật & quyết định thiết kế

(Tài liệu này trả lời trước các câu hỏi phản biện của hội đồng.)

## 1. WebSocket in-memory: Single-node limitation
- `ConnectionManager` giữ `dict[event_id, set[WebSocket]]` trong RAM tiến trình.
- Chạy `uvicorn --workers 4`: 4 process độc lập, client ở worker khác không nhận
  broadcast từ worker xử lý register. Đây là giới hạn đã biết, chấp nhận ở quy mô đồ án.
- Phương án mở rộng (ghi trong Chương 14): Redis Pub/Sub — worker publish occupancy,
  mọi worker subscribe và đẩy tới room của mình. Minh chứng Tầng 3 C2.3.

## 2. WS auth: ticket handshake thay JWT trên query string
- Trước đây `?token=<JWT>` — sai vì token dính log proxy (Nginx/ALB), Referer, history.
- Hiện tại: `POST /ws/ticket` (header Authorization, ORGANIZER) cấp ticket 30s
  dùng 1 lần; WS chỉ nhận `?ticket=`. Ticket hết hạn/dùng lại -> 4401, sai role ->
  4403, sai event -> 4404. Test: `test_ws_ticket_one_time_use`.
- Còn lại: ticket chưa gắn event cụ thể (dùng được cho mọi event của organizer) —
  chấp nhận vì scope dashboard admin; ghi nhận để không bị hỏi bất ngờ.

## 3. BackgroundTasks không phải queue thật
- `register` (gửi vé/QR) và `transition COMPLETED` (notify) dùng BackgroundTasks:
  task ngắn, chạy sau response, không retry, mất khi restart process.
- Tác vụ nặng/dài phải dùng Celery/RabbitMQ + outbox + idempotency (Chương 14).

## 4. Email/SMTP thật chưa có
- `NOTIFY_WEBHOOK_URL` để cắm webhook thật; mặc định simulate bằng `asyncio.sleep`.
- Không xin credential SMTP vì ngoài phạm vi minh chứng FastAPI; client vẫn nhận
  201 trong vài ms và task nền vẫn chạy (có test monkeypatch).

## 5. Danh mục quyết định mã lỗi (nhất quán 400 vs 422)
- `422 VALIDATION_ERROR`: payload sai shape/kiểu hoặc quan hệ trong payload
  (end <= start qua `model_validator`, email sai, capacity âm).
- `400` nghiệp vụ cần trạng thái hiện tại/DB: `INVALID_EVENT_TIME` (start quá khứ),
  `REGISTRATION_CLOSED`, `EVENT_STARTED`, `INVALID_TRANSITION`, `EVENT_NOT_DELETABLE`,
  `CURSOR_OFFSET_CONFLICT`.
- PATCH gửi 1 mốc thời gian: Pydantic không thấy DB nên endpoint merge rồi check
  qua `_validate_event_time` -> `400`. Đây là thiết kế có chủ đích, không phải lọt lưới.

## 6. Thời gian: naive-UTC thống nhất
- Cột DB là `DateTime` không tz; toàn bộ so sánh dùng naive-UTC qua `models.utcnow()`
  (thay `datetime.utcnow()` deprecated từ Python 3.12).
- Datetime aware (ISO có 'Z') được chuẩn hóa qua `_as_naive` trước khi so sánh.

## 7. Test SQLite vs PostgreSQL thật
- Test mặc định dùng SQLite in-memory (nhanh, CI): không chứng minh được row lock.
- `FOR UPDATE` được chứng minh bằng `tests/test_concurrency_pg.py` trên PG compose
  (5 thread × capacity 1 -> `[201, 409×4]`), skip khi không có `TEST_POSTGRES_URL`.
- Benchmark index/cursor chạy trên PG compose 3000 rows (`scripts/bench_events.py`).

## 8. Secret local-only
- JWT secret, DB password, pgAdmin password trong Compose/`.env.example` chỉ cho
  local development; deploy phải qua biến môi trường/kho bí mật, bật `secure=True`
  cho cookie và HTTPS.
