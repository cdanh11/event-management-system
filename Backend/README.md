# Evently — FastAPI Backend

Hệ thống quản lý sự kiện: tạo sự kiện, đăng ký tham dự, cấp vé, check-in,
phân quyền theo role (ORGANIZER / STAFF / ATTENDEE).

## 1. Chạy dự án

1. Tạo PostgreSQL database `evently` và copy `.env.example` thành `.env`.
2. `python -m venv .venv`, kích hoạt, rồi `pip install -r requirements.txt`.
3. Tạo schema: `alembic upgrade head` (hoặc `python -m app.seed` để nạp dữ liệu demo).
4. Chạy: `uvicorn app.main:app --reload --port 8000`.

- Swagger/OpenAPI: `http://localhost:8000/docs`
- Tài khoản demo (pass `123456`): `attendee@demo.com`, `staff@demo.com`, `organizer@demo.com`
- Chạy test + đo coverage: `pytest --cov=app --cov-report=term`

## 2. Cấu trúc code

```
app/
├── main.py            # điểm vào: lifespan, exception handler, middleware, OpenAPI
├── config.py          # settings tập trung (đọc từ .env)
├── db.py              # engine + session + dependency get_db
├── models.py          # 7 bảng ORM (SQLAlchemy 2.0)
├── schemas.py         # Pydantic v2: model request/response
├── deps.py            # dependency: current_user (auth) + require(*roles)
├── serializers.py     # chuyển ORM -> dict theo schema API
├── errors.py          # helper ném lỗi HTTP chuẩn {code, message}
├── middleware.py      # middleware tự viết (log + đo thời gian)
├── security.py        # Argon2 hash, JWT access, refresh token (hash SHA-256)
├── services/notifier.py  # async I/O thật (gửi thông báo qua webhook)
├── routers/           # tách theo tài nguyên: auth, events, registrations,
│                      #   tickets, checkins, staff
└── seed.py            # dữ liệu demo
```

## 3. Minh chứng theo yêu cầu "Backend FastAPI"

### 3.1 Lõi bắt buộc (Tầng 1A)

| Yêu cầu | Nơi trong code |
|---|---|
| Pydantic model request/response + validation tự động | `schemas.py` — `Field(min_length=…)`, `EmailStr`; lỗi sai kiểu do Pydantic sinh ở tầng binding → 422 |
| Dependency system (Depends) | `get_db` (`db.py`), `current_user`; `config` là dependency/instance dùng chung |
| auth + phân quyền | `deps.py: current_user` (401) + `require("ORGANIZER")...` (403) |
| async đúng chỗ | xem mục 3.3 bên dưới |
| HTTP status/error rõ ràng | `errors.api_error` + exception handler tập trung (`main.py`) |

### 3.2 Lõi tự chọn (Tầng 1B)

| Yêu cầu | Nơi trong code |
|---|---|
| Response model + OpenAPI có chủ đích | `response_model=...` ở mọi endpoint; `custom_openapi()` gắn security scheme Bearer để Swagger hiện nút Authorize (`main.py`) |
| Exception handler tập trung | `@app.exception_handler(HTTPException)` + `@app.exception_handler(RequestValidationError)` (`main.py`) |
| Background task (công việc ngắn sau response) | `transition_event(...)` lên schedule `notify_attendees` khi chuyển COMPLETED; **không** dùng cho tác vụ nặng (đã chú thích rõ giới hạn) |
| Middleware | `CORSMiddleware` (main) + `TimingLoggingMiddleware` tự viết (`middleware.py`) |
| Lifespan/startup-shutdown | `lifespan()` trong `main.py` — log startup, `engine.dispose()` khi shutdown |
| TestClient/httpx + dependency override | `tests/` — `conftest.py` override `get_db` bằng SQLite |

### 3.3 Async "đúng chỗ" và dependency graph

**Nguyên tắc đang áp dụng:**
- Endpoint dùng SQLAlchemy **sync** → khai báo `def` (FastAPI chạy trong
  threadpool, không chặn event loop). Ví dụ: `login`, `register`, `checkin`.
- Endpoint **chỉ có** network I/O → `async def` và `await` một tác vụ awaitable thật.
  Ví dụ: `POST /events/{id}/notify` (`routers/events.py`) await
  `notify_attendees(...)` (`services/notifier.py`) — chờ phản hồi HTTP webhook
  (hoặc `asyncio.sleep` mô phỏng khi chưa cấu hình `NOTIFY_WEBHOOK_URL`).
- `GET /health` là `def` vì không có I/O gì để await.

**Dependency graph của endpoint ví dụ `POST /events` (create_event):**
```
create_event
 ├── require("ORGANIZER")  (factory dependency - phân quyền)
 │    └── current_user     (xác thực)
 │         ├── HTTPBearer  (đọc header Authorization: Bearer <token>)
 │         └── get_db      (mở Session, đóng sau request)
 └── get_db                (Session của DB)
```

**Câu hỏi tự kiểm — đáp án rút gọn:**
1. *Endpoint nào nên async, endpoint nào không?* → async khi có covert I/O awaitable
   (`/notify`); các endpoint còn lại sync vì DB là SQLAlchemy sync.
2. *Dependency được tạo ở đâu và dùng lại thế nào?* → `db.py` (get_db),
   `deps.py` (current_user, require). Ro dùng lại nhờ khai báo `Depends(...)`
   trong tham số hàm ở bất kỳ router nào.
3. *Model input sai kiểu thì lỗi sinh ở tầng nào?* → Pydantic validate ngay khi
   bind request body, ném `RequestValidationError` TRƯỚC khi endpoint chạy;
   handler tập trung (`main.py`) đóng gói thành `{status:422, code:VALIDATION_ERROR, details}`.

## 4. Vòng đời sự kiện (Create–Cancel–Reschedule–Complete–Notify)

| Bước | Endpoint | Ghi chú |
|---|---|---|
| Create | `POST /events` | organizer, status khởi tạo DRAFT |
| Cancel | `POST /registrations/{id}/cancel` | hủy đăng ký + hủy vé + trả slot |
| Reschedule | `PATCH /events/{id}` | đổi start/end time, validate thời gian |
| Complete | `POST /events/{id}/transition` → COMPLETED | kích hoạt background task Notify |
| Notify | `POST /events/{id}/notify` (async) | gửi email/webhook; transition cũng tự gửi qua background task |

## 5. Test

- 29 test qua `TestClient` trên SQLite trong bộ nhớ (`dependency_overrides[get_db]`).
- Coverage ~84% (`pytest --cov=app --cov-report=term`).
- Gồm: auth, phân quyền 401/403, CRUD/validation 422, vòng đời event,
  đăng ký/hủy, over-booking (409 EVENT_FULL, ALREADY_REGISTERED), check-in
  một lần duy nhất (409 TICKET_ALREADY_USED), async notify.