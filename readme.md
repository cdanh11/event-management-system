# Evently - FastAPI Event Management System

Evently la he thong quan ly su kien phuc vu muc tieu hoc FastAPI. Du an tap trung vao REST API co kieu du lieu ro rang, phan quyen theo vai tro, vong doi nghiep vu, PostgreSQL va kiem thu tu dong. React chi dong vai tro client de demo API end-to-end.

## Pham vi

- Quan ly Event: tao, doi lich, chuyen trang thai va gui thong bao.
- Attendee dang ky, huy dang ky va xem ve.
- Staff check-in ve duoc phan cong.
- Organizer quan ly Event va staff assignment qua API.
- Co 7 bang: `users`, `events`, `registrations`, `tickets`, `checkins`, `staff_event_assignments`, `refresh_tokens`.

Ngoai pham vi hien tai: thanh toan, quet QR bang camera that, email production, queue phan tan va microservice.

## Cong nghe

- Backend: Python, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, psycopg 3.
- Auth: JWT access token, refresh token HttpOnly cookie, Argon2 password hash.
- Database: PostgreSQL 16 qua Docker Compose.
- Frontend: React, TypeScript, Vite.
- Test: pytest, TestClient/httpx, dependency override, pytest-cov.
- CI: GitHub Actions chay backend test/coverage va frontend lint/build.

Tai lieu chi tiet:

- [Backend/congnghe.md](Backend/congnghe.md): cach FastAPI duoc ap dung trong code.
- [docs/roadmap.md](docs/roadmap.md): hien trang, khoang trong va lo trinh 2 tuan.
- [Backend/README.md](Backend/README.md): cau truc va minh chung backend.

## Chay local

Yeu cau: Docker Desktop, Python 3.10+, Node.js 22+ va npm. Cac lenh duoi day dung PowerShell, bat dau tai thu muc goc project.

### 1. Chay PostgreSQL

```powershell
docker compose up -d db
docker compose ps
```

Compose tu tao database/user local `evently`. PostgreSQL duoc map tai `localhost:5433` de tranh xung dot cong 5432 cua may.

pgAdmin la tuy chon:

```powershell
docker compose --profile tools up -d
```

Mo `http://localhost:5050`, dang nhap `admin@evently.local` / `admin`. Khi them server trong pgAdmin, dung host `db`, port `5432`, user/password `evently` / `evently`.

Dung database bang `docker compose down`. Chi dung `docker compose down -v` khi muon xoa toan bo du lieu local.

### 2. Chay backend

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

`Backend/.env` local can dung cau hinh sau:

```dotenv
DATABASE_URL=postgresql+psycopg://evently:evently@localhost:5433/evently
JWT_SECRET=replace-with-a-long-random-secret
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=7
FRONTEND_ORIGIN=http://localhost:5173
NOTIFY_WEBHOOK_URL=
```

- API: `http://localhost:8000`
- Swagger/OpenAPI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### 3. Chay frontend

Mo terminal thu hai tai thu muc goc project:

```powershell
cd Frontend
npm ci
Copy-Item .env.example .env
npm run dev -- --port 5173
```

`Frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

Khởi động giao diện:

```powershell
npm run dev -- --port 5173
```

Mở [http://localhost:5173](http://localhost:5173). Giữ hai terminal chạy trong quá trình sử dụng; nhấn `Ctrl+C` tại từng terminal để dừng. Dùng nhất quán hostname `localhost` cho cả frontend và backend để cookie đăng nhập hoạt động đúng. Sau khi đổi `.env`, khởi động lại server tương ứng.

## Hướng dẫn sử dụng

### 1. Đăng nhập bằng tài khoản demo

Các tài khoản sau chỉ có sau khi seed thành công; tất cả dùng mật khẩu **`123456`**:

| Vai trò | Email | Mục đích |
| --- | --- | --- |
| ATTENDEE | `attendee@demo.com` | Đăng ký sự kiện; có sẵn vé AI Product Meetup |
| ATTENDEE | `linh@demo.com`, `huy@demo.com` | Thử với người tham dự khác |
| STAFF | `staff@demo.com` | Check-in cho AI Product Meetup |
| STAFF | `khanh.staff@demo.com` | Được phân công Vietnam Tech Conference 2026 |
| ORGANIZER | `organizer@demo.com` | Quản lý sự kiện mẫu và tạo sự kiện mới |

Vào `/login`, nhập email và mật khẩu rồi chọn **Sign in**. Dùng biểu tượng đăng xuất ở góc phải để đổi vai trò. Hiện chưa có chức năng tự đăng ký tài khoản mới.

### 2. Người tham dự — ATTENDEE

1. Đăng nhập bằng `attendee@demo.com`, mở **Explore** (`/events`).
2. Nhập từ khóa trong **Search events** hoặc lọc trạng thái. Chọn **View event** để xem chi tiết.
3. Chọn sự kiện **PUBLISHED** còn chỗ, chẳng hạn **Vietnam Tech Conference 2026**, rồi bấm **Register now**. Backend tạo đăng ký và vé, giao diện chuyển tới trang vé.
4. Mở **My registrations** (`/registrations`); chọn **View ticket** để xem vé hoặc **Cancel** để hủy đăng ký. Hủy đăng ký vô hiệu hóa vé và trả lại một chỗ.

Backend chỉ cho đăng ký khi sự kiện ở trạng thái `PUBLISHED`. Sự kiện đầy chỗ hiển thị **Sold out**; một tài khoản không thể đăng ký cùng sự kiện lần nữa, kể cả sau khi đã hủy. **Career Fair: Future Makers** được seed ở trạng thái đầy chỗ để thử trường hợp này.

**Hạn chế hiện tại:** thông tin vé và tên sự kiện trong danh sách đăng ký có thể bị thiếu do frontend chưa chuyển các trường API `snake_case` sang `camelCase`. Nếu không thấy mã vé, dùng Swagger theo mục bên dưới để lấy `ticket_code`.

### 3. Nhân viên — STAFF

1. Đăng nhập bằng `staff@demo.com`; giao diện mở **Check-in** (`/staff/check-in`).
2. Nhập **`AI-MEET-2026`** vào **Ticket code**, hoặc chọn **Use demo valid code**.
3. Bấm **Validate & check in**. Đây là vé của `attendee@demo.com` cho **AI Product Meetup**, sự kiện được seed ở trạng thái `ONGOING` và đã phân công cho nhân viên này.
4. Thử lại cùng mã để kiểm tra lỗi vé đã sử dụng (`TICKET_ALREADY_USED`).

Chỉ nhân viên được phân công mới được check-in, và sự kiện phải ở trạng thái `ONGOING`. Vé bị hủy hoặc đã sử dụng không được chấp nhận. Mã demo chỉ dùng thành công một lần và phải chưa bị người tham dự hủy.

**Hạn chế hiện tại:** backend trả `checked_in_at`, trong khi giao diện đọc `checkedInAt`, nên có thể báo lỗi hiển thị thời gian dù check-in đã được lưu. Kiểm tra kết quả bằng Swagger; lỗi hiển thị không đồng nghĩa với thao tác chưa thực hiện. Khung camera và hình QR trên vé chỉ là minh họa, chưa hỗ trợ quét QR thật. Các mục **Dashboard** và **Attendees** của STAFF hiện cũng dẫn tới màn hình check-in.

### 4. Người tổ chức — ORGANIZER

1. Đăng nhập bằng `organizer@demo.com`; mở **Dashboard** (`/organizer`) để xem sự kiện, tổng đăng ký và tổng check-in.
2. Chọn **Create event**. Điền tên, mô tả, địa điểm, thời gian bắt đầu/kết thúc, số chỗ, danh mục và URL ảnh.
3. Chọn thời gian bắt đầu **ở tương lai**, kết thúc sau bắt đầu, số chỗ lớn hơn 0; kiểm tra lại ngày mặc định trong form. Bấm **Create draft event** để tạo sự kiện `DRAFT`.
4. Tại trang **Manage**, chọn **Publish event** để mở đăng ký, **Start event** để bắt đầu check-in, rồi **Mark completed** khi kết thúc.
5. Có thể chọn **Cancel event** khi sự kiện đang `DRAFT` hoặc `PUBLISHED`.

Vòng đời chính: `DRAFT → PUBLISHED → ONGOING → COMPLETED`. Từ `DRAFT` hoặc `PUBLISHED` có thể chuyển sang `CANCELLED`.

Trạng thái không tự chuyển theo thời gian. `COMPLETED` và `CANCELLED` không chuyển tiếp được. Sự kiện mới chưa có nhân viên; cần phân công qua API trước khi thử check-in. Chỉnh sửa/dời lịch và phân công nhân viên hiện chưa có màn hình riêng.

Số lượng đăng ký trên sự kiện seed là dữ liệu minh họa, không tương ứng đầy đủ với số bản ghi đăng ký thực tế; thống kê dashboard có thể khác số chỗ đã đăng ký trên thẻ sự kiện.

### 5. Thử API bằng Swagger

1. Mở [Swagger UI](http://localhost:8000/docs), chọn `POST /auth/login` → **Try it out**.
2. Nhập body với tài khoản đúng vai trò, rồi chọn **Execute**:

   ```json
   {"email": "organizer@demo.com", "password": "123456"}
   ```

3. Sao chép `access_token` trong response, bấm **Authorize**, dán token vào ô HTTPBearer (không thêm tiền tố `Bearer`). Khi đổi vai trò, đăng nhập lại và thay token trong **Authorize**.
4. Dùng các API sau; lấy ID từ response thay vì dùng tên sự kiện hoặc email thay ID:

| Thao tác | Endpoint | Vai trò / dữ liệu |
| --- | --- | --- |
| Danh sách sự kiện và ID | `GET /events` | Không cần đăng nhập |
| Đăng ký sự kiện | `POST /events/{event_id}/register` | ATTENDEE; response có vé và `ticket_code` |
| Đăng ký cá nhân | `GET /registrations/me` | ATTENDEE; lấy ID đăng ký |
| Lấy vé đã đăng ký | `GET /registrations/{registration_id}/ticket` | Người sở hữu vé; đọc `ticket_code` |
| Dời lịch/chỉnh sửa | `PATCH /events/{event_id}` | ORGANIZER sở hữu sự kiện; gửi trường cần đổi như `start_time`, `end_time` |
| ID người dùng hiện tại | `GET /auth/me` | Đăng nhập STAFF để lấy ID nhân viên |
| Phân công nhân viên | `POST /events/{event_id}/staff` | ORGANIZER sở hữu sự kiện; body `{"staff_id":"ID nhân viên"}` |
| Sự kiện được phân công | `GET /staff/events` | STAFF |
| Check-in | `POST /checkins` | STAFF được phân công; body `{"ticket_code":"AI-MEET-2026"}` |
| Gửi thông báo | `POST /events/{event_id}/notify` | ORGANIZER sở hữu sự kiện |

Thông báo mặc định chạy mô phỏng (`mode: simulated`). Để gửi HTTP webhook thật, đặt thêm `NOTIFY_WEBHOOK_URL` trong `Backend/.env` và khởi động lại backend. Chuyển sang `COMPLETED` cũng lên lịch thông báo cho người còn đăng ký; hiện chưa có cấu hình gửi email trực tiếp.

## Kiểm thử và build

Chạy kiểm thử backend từ thư mục `Backend` (test sử dụng SQLite trong bộ nhớ qua dependency override):

```powershell
cd Backend
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term
```

Frontend:

```powershell
cd Frontend
npm run lint
npm run build
```

Kiem tra demo E2E:

1. Organizer tao Event, Publish, Reschedule, Start, Complete va Notify.
2. Attendee dang ky Event `PUBLISHED`, mo ve va huy dang ky.
3. Staff dung ma ve duoc phan cong de check-in mot lan.
4. Mo Swagger, login, Authorize bang access token va thu response 401/403/409/422.

## OpenAPI va bao mat

- OpenAPI duoc sinh tu Pydantic response/request model tai `/docs`.
- Endpoint public nhu `POST /auth/login`, `POST /auth/refresh`, `GET /events`, `GET /health` khong yeu cau Bearer token trong Swagger.
- Endpoint can xac thuc nhu `GET /auth/me`, tao Event, dang ky, check-in va Notify hien HTTP Bearer security.
- Loi nghiep vu su dung dang `{status, code, message}`; loi Pydantic 422 bo sung `details`.
- Secret trong Compose va `.env.example` chi danh cho local development. Khong dung chung secret/password nay khi deploy.

## Cau truc

```text
Project/
|- Backend/                 # FastAPI app, Alembic, seed, pytest
|- Frontend/                # React client goi REST API that
|- docs/                    # roadmap va tai lieu bao cao se bo sung
|- compose.yaml             # PostgreSQL va pgAdmin profile
`- .github/workflows/ci.yml # CI backend + frontend
```

## Loi thuong gap

| Hiện tượng | Cách kiểm tra |
| --- | --- |
| Không kết nối được PostgreSQL | Kiểm tra dịch vụ PostgreSQL, database đã tạo, user/mật khẩu/cổng trong `DATABASE_URL`. |
| Báo thiếu bảng dữ liệu | Chạy Alembic từ thư mục `Backend`, kiểm tra đang trỏ đúng database. |
| Tài khoản demo đăng nhập thất bại | Kiểm tra đã seed thành công; seed bỏ qua nếu database đã có user. |
| `Failed to fetch` hoặc lỗi CORS | Kiểm tra backend đang chạy, `VITE_API_BASE_URL`, `FRONTEND_ORIGIN` và hostname; khởi động lại sau khi sửa `.env`. |
| `REGISTRATION_CLOSED` | Chọn sự kiện `PUBLISHED`; backend không cho đăng ký khi `ONGOING`. |
| `FORBIDDEN` / `CHECKIN_CLOSED` khi check-in | Dùng STAFF đã được phân công và chuyển sự kiện sang `ONGOING`. |
| Vé thiếu mã hoặc check-in lỗi hiển thị ngày | Xem ghi chú về tên trường API ở phần hướng dẫn; dùng Swagger để đọc kết quả. |

Xem thêm cấu trúc backend và nội dung thực hành FastAPI trong [Backend/README.md](Backend/README.md).
