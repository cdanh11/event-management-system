# Evently — Hệ thống quản lý sự kiện & đăng ký vé (FastAPI)

> Đồ án môn **Công nghệ Lập trình Hiện đại** — đề tài:
> **Tìm hiểu và xây dựng dịch vụ Backend với FastAPI**.

Evently là hệ thống quản lý sự kiện hoàn chỉnh với ba vai trò
(`ORGANIZER` / `STAFF` / `ATTENDEE`): tạo và điều hành sự kiện, đăng ký vé,
check-in tại cửa, xem occupancy realtime. Trọng tâm đồ án là **backend FastAPI**
(Pydantic, dependency injection, async đúng chỗ, OpenAPI, WebSocket);
React chỉ là client demo API end-to-end.

## Mục lục

1. [Tính năng](#1-tính-năng)
2. [Kiến trúc](#2-kiến-trúc)
3. [Công nghệ](#3-công-nghệ)
4. [Chạy local](#4-chạy-local)
5. [Tài khoản demo & kịch bản E2E](#5-tài-khoản-demo--kịch-bản-e2e)
6. [Thử API bằng Swagger](#6-thử-api-bằng-swagger)
7. [Kiểm thử & chất lượng](#7-kiểm-thử--chất-lượng)
8. [Tài liệu](#8-tài-liệu)
9. [Giới hạn đã biết](#9-giới-hạn-đã-biết)
10. [Xử lý sự cố](#10-xử-lý-sự-cố)

## 1. Tính năng

| Vai trò | Tính năng |
| --- | --- |
| Khách | Tự đăng ký tài khoản `ATTENDEE` (`POST /auth/register`), xem danh sách/tìm kiếm/lọc sự kiện (phân trang offset + cursor) |
| Attendee | Đăng ký vé (chặn event đầy, trùng vé, chưa mở bán, đã qua giờ bắt đầu), xem vé, hủy vé (trả slot) |
| Staff | Check-in vé bằng ticket code (vé một lần duy nhất, đúng event được phân công và đang `ONGOING`) |
| Organizer | Tạo/sửa/dời lịch/xóa nháp event, chuyển trạng thái theo state machine, gán staff, gửi notify, xem dashboard và occupancy realtime (`/organizer/live`) |

Vòng đời sự kiện: `DRAFT → PUBLISHED → ONGOING → COMPLETED`
(từ `DRAFT`/`PUBLISHED` có thể `CANCELLED`; chỉ xóa cứng khi còn `DRAFT`).

## 2. Kiến trúc

```text
React (Vite) ──REST/JSON──▶ FastAPI ──SQLAlchemy──▶ PostgreSQL 16
     │                         ├── Depends: get_db → current_user → require(*roles)
     │                         ├── Pydantic: validate request / serialize response
     │                         ├── BackgroundTasks: gửi vé/QR, notify, broadcast WS
     │                         └── WebSocket: occupancy realtime theo room event_id
     └── apiClient (Bearer + refresh cookie) + services (chuẩn hóa snake_case)
```

7 bảng: `users`, `events`, `registrations`, `tickets`, `checkins`,
`staff_event_assignments`, `refresh_tokens` — xem ERD ở `docs/assets/erd.png`.

## 3. Công nghệ

| Lớp | Công nghệ |
| --- | --- |
| Backend | Python, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, psycopg 3 |
| Auth | JWT access (15 phút) + refresh xoay vòng (HttpOnly cookie), Argon2, ticket WS một lần |
| Database | PostgreSQL 16 (Docker Compose, cổng host `5433`) |
| Realtime | WebSocket occupancy + broadcast sau commit |
| Frontend | React 19, TypeScript, Vite, React Router |
| Test/CI | pytest + TestClient + coverage (~88%), oxlint + `tsc`, GitHub Actions |

Minh chứng chi tiết theo Tầng 1/2/3 của môn học: [`Backend/README.md`](Backend/README.md),
[`Backend/docs/`](Backend/docs/), [`docs/roadmap.md`](docs/roadmap.md).

## 4. Chạy local

Yêu cầu: Docker Desktop, Python 3.10+, Node.js 22+ và npm. Lệnh dùng **PowerShell**,
bắt đầu tại thư mục gốc project.

### Bước 1 — PostgreSQL

```powershell
docker compose up -d db
```

Compose tự tạo database/user `evently`; PostgreSQL mở ở `localhost:5433`
(tránh chiếm cổng `5432` của máy). pgAdmin là tùy chọn:

```powershell
docker compose --profile tools up -d
```

Mở `http://localhost:5050`, đăng nhập `admin@evently.local` / `admin`,
tạo server với host `db`, port `5432`, user/password `evently` / `evently`.

### Bước 2 — Backend

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- API: `http://localhost:8000` · Swagger: `http://localhost:8000/docs` · Health: `http://localhost:8000/health`
- `DATABASE_URL` mặc định trong `.env.example` đã trỏ đúng `localhost:5433`; chỉ cần
  đặt `JWT_SECRET` thành chuỗi bí mật riêng.

### Bước 3 — Frontend (terminal thứ hai, tại thư mục gốc)

```powershell
cd Frontend
npm ci
Copy-Item .env.example .env
npm run dev -- --port 5173
```

Mở `http://localhost:5173`. Dùng nhất quán hostname `localhost` cho cả hai phía để
cookie đăng nhập hoạt động; đổi `.env` thì khởi động lại server tương ứng.
Dừng database khi xong: `docker compose down` (thêm `-v` chỉ khi muốn xóa dữ liệu).

## 5. Tài khoản demo & kịch bản E2E

Tất cả dùng mật khẩu **`123456`** (có sau khi seed):

| Vai trò | Email | Dùng để thử |
| --- | --- | --- |
| ATTENDEE | `attendee@demo.com` | Đăng ký, xem vé, hủy vé (có sẵn vé `AI-MEET-2026`) |
| ATTENDEE | `linh@demo.com`, `huy@demo.com` | Đăng ký trùng, event đầy |
| STAFF | `staff@demo.com` | Check-in `AI-MEET-2026` (một lần duy nhất) |
| ORGANIZER | `organizer@demo.com` | Vòng đời event, gán staff, notify, live dashboard |

Kịch bản chi tiết từng bước (kể cả trường hợp biên 401/403/409/422 và demo hai trình
duyệt cho realtime): [`Frontend/docs/demo-scenarios.md`](Frontend/docs/demo-scenarios.md)
và [`Frontend/docs/realtime-dashboard.md`](Frontend/docs/realtime-dashboard.md).

## 6. Thử API bằng Swagger

1. Mở `http://localhost:8000/docs` → `POST /auth/login` → **Try it out** với
   `{"email": "organizer@demo.com", "password": "123456"}` → **Execute**.
2. Sao chép `access_token` → **Authorize** → dán vào ô HTTPBearer.
3. Gọi các endpoint theo vai trò (lấy ID từ response, xem bảng đầy đủ 27 endpoint
   trong báo cáo hoặc `GET /openapi.json`):
   `GET /events` (public) · `POST /events/{id}/register` (ATTENDEE) ·
   `POST /checkins` (STAFF) · `PATCH /events/{id}`, `POST /events/{id}/notify` (ORGANIZER).
4. Cố tình gửi sai để thấy chuẩn lỗi: body sai → `422`, thiếu token → `401`,
   sai role → `403`, đăng ký trùng → `409`.

## 7. Kiểm thử & chất lượng

```powershell
# Backend (SQLite in-memory qua dependency override; PG thật cho test concurrency)
cd Backend
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term
# → 52 passed + 1 skipped, coverage ~88%

# Concurrency PostgreSQL thật (cần docker compose up -d db)
$env:TEST_POSTGRES_URL="postgresql+psycopg://evently:evently@localhost:5433/evently"
.\.venv\Scripts\python.exe -m pytest tests/test_concurrency_pg.py -q
# → 5 thread × capacity 1 = [201, 409×4]

# Frontend
cd Frontend
npm run lint
npm run build
```

Số liệu Tầng 3 (tái hiện bằng `Backend/scripts/bench_events.py` trên 3000 rows):
index composite nhanh hơn Seq Scan **~12.5x** (1.403 ms → 0.112 ms),
cursor keyset nhanh hơn offset deep-page **~2.1x** (3.43 ms → 1.60 ms).

## 8. Tài liệu

| Tài liệu | Nội dung |
| --- | --- |
| [`Backend/README.md`](Backend/README.md) + [`Backend/docs/`](Backend/docs/) | Chạy backend, minh chứng FastAPI, auth/validation/realtime/perf/test |
| [`Frontend/README.md`](Frontend/README.md) + [`Frontend/docs/`](Frontend/docs/) | Chạy frontend, kiến trúc, auth, realtime, kịch bản demo |
| [`docs/`](docs/) | Roadmap, review từng phase, giới hạn kỹ thuật (nguyên liệu Chương 13), báo cáo DRAFT, ảnh minh chứng |
| [`docs/Bao_cao_Evently_DRAFT.docx`](docs/Bao_cao_Evently_DRAFT.docx) | Báo cáo toàn văn (bản nháp chờ duyệt) |

## 9. Giới hạn đã biết

- Notify/vé dùng webhook thật nếu cấu hình `NOTIFY_WEBHOOK_URL`, mặc định mô phỏng
  (chưa có SMTP production); `BackgroundTasks` chỉ cho task ngắn, không retry.
- WebSocket in-memory single-process (đa worker cần Redis Pub/Sub).
- Secret/password mặc định trong Compose chỉ cho local development.
- Chi tiết và phương án mở rộng: [`docs/gioi-han-ky-thuat.md`](docs/gioi-han-ky-thuat.md).

## 10. Xử lý sự cố

| Hiện tượng | Cách kiểm tra |
| --- | --- |
| Không kết nối PostgreSQL | `docker compose ps`; `DATABASE_URL` đúng port `5433` |
| Báo thiếu bảng | Chạy `alembic upgrade head` trong `Backend`, đúng database |
| Đăng nhập demo thất bại | Chạy lại `python -m app.seed` (seed bỏ qua nếu DB đã có user) |
| `Failed to fetch` / CORS | Backend đang chạy, `VITE_API_BASE_URL` + `FRONTEND_ORIGIN` đúng, cùng hostname `localhost` |
| `REGISTRATION_CLOSED` / `EVENT_STARTED` | Event phải `PUBLISHED` và chưa qua giờ bắt đầu |
| `FORBIDDEN` / `CHECKIN_CLOSED` | Đúng role, organizer sở hữu event, staff được phân công, event `ONGOING` |
