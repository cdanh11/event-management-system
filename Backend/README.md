# Evently — FastAPI Backend

Hệ thống quản lý sự kiện: tạo sự kiện, đăng ký tham dự, cấp vé, check-in,
phân quyền theo role (`ORGANIZER` / `STAFF` / `ATTENDEE`), dashboard realtime
qua WebSocket.

## 1. Chạy nhanh (chi tiết đầy đủ ở [`../readme.md`](../readme.md))

```powershell
# 1. PostgreSQL local (tại thư mục gốc project)
docker compose up -d db

# 2. Tại thư mục Backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- Swagger/OpenAPI: `http://localhost:8000/docs` — tài liệu tham khảo thêm ở [`docs/`](docs/).
- Tài khoản demo (mật khẩu `123456`): `attendee@demo.com`, `staff@demo.com`, `organizer@demo.com`.
- Kiểm thử: `.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term` (**52 passed + 1 skipped**, coverage **~88%**).

## 2. Cấu trúc code

```text
app/
├── main.py            # FastAPI app: lifespan, exception handler, middleware, OpenAPI
├── config.py          # settings tập trung (đọc từ .env)
├── db.py              # engine + session + dependency get_db
├── models.py          # 7 bảng ORM (SQLAlchemy 2.0) + helper utcnow()
├── schemas.py         # Pydantic v2: request/response, Enum, model_validator, error contract
├── deps.py            # current_user (401) + require(*roles) (403)
├── serializers.py     # ORM -> dict theo schema API
├── errors.py          # api_error(status, code, message)
├── middleware.py      # TimingLoggingMiddleware (log + đo thời gian)
├── security.py        # Argon2, JWT access, refresh token (lưu hash SHA-256)
├── realtime.py        # ConnectionManager WS + ticket handshake một lần
├── services/
│   └── notifier.py    # async I/O gửi notify/vé (shared httpx client)
├── routers/           # auth, events, registrations, tickets, checkins, staff, realtime
└── seed.py            # dữ liệu demo
```

## 3. Minh chứng FastAPI (Tầng 1)

| Yêu cầu | Nơi trong code |
| --- | --- |
| Pydantic request/response + validation 422 | `schemas.py`: `Field`, `EmailStr`, `model_validator` start/end; chi tiết xem [`docs/validation-errors.md`](docs/validation-errors.md) |
| Dependency system | `get_db` (`db.py`), `current_user` + `require(*roles)` (`deps.py`) |
| Auth + phân quyền + ownership | JWT Bearer + refresh xoay vòng; organizer chỉ thao tác event của mình; chi tiết xem [`docs/authentication.md`](docs/authentication.md) |
| Async đúng chỗ | Endpoint DB sync giữ `def`; chỉ notify/WS/notifier dùng `async` cho network I/O; chi tiết xem [`docs/realtime.md`](docs/realtime.md) |
| Response model + OpenAPI có chủ đích | `response_model` mọi endpoint; Bearer chỉ gắn operation cần auth; `responses={401,403,404,409}` cho endpoint quan trọng |
| Exception handler tập trung | `main.py`: HTTP → `{status, code, message}`; Pydantic → `422 + details` |
| Background task | Gửi vé/QR sau `201` register, notify khi `COMPLETED` (task ngắn, không retry) |
| Middleware + lifespan | `CORSMiddleware` + `TimingLoggingMiddleware`; shutdown dispose engine + close httpx client |
| TestClient + dependency override | `tests/conftest.py` override `get_db` bằng SQLite; xem [`docs/testing.md`](docs/testing.md) |

**Dependency graph ví dụ** (`POST /events`): `require("ORGANIZER") → current_user → {HTTPBearer, get_db}`.

## 4. Vòng đời sự kiện

`DRAFT → PUBLISHED → ONGOING → COMPLETED` (từ `DRAFT`/`PUBLISHED` có thể `CANCELLED`).
Chỉ xóa cứng khi còn `DRAFT`. Luồng đầy đủ: Create → Reschedule (`PATCH`) →
Register → Cancel → Complete → Notify (async) + realtime occupancy.

## 5. Tầng 3 & hiệu năng

Cursor pagination + composite index + benchmark + concurrency test đầy đủ trong
[`docs/performance.md`](docs/performance.md). Giới hạn đã biết và quyết định thiết kế
(trả lời trước câu hỏi phản biện) trong [`../docs/gioi-han-ky-thuat.md`](../docs/gioi-han-ky-thuat.md).
