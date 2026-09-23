# Evently — Event Management System

Ứng dụng web quản lý sự kiện, đăng ký tham dự, cấp vé và check-in. Dự án phục vụ việc học và áp dụng FastAPI để xây dựng REST API, kết hợp frontend React và PostgreSQL.

## Công nghệ và cấu trúc

- **Frontend:** React 19, TypeScript, Vite, React Router, Tailwind CSS.
- **Backend:** Python, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic.
- **Database:** PostgreSQL, driver psycopg.
- **Xác thực:** JWT, refresh token qua cookie HttpOnly, hash mật khẩu bằng Argon2.
- **Kiểm thử:** pytest, TestClient/httpx, pytest-cov.

```text
Project/
├── Backend/
│   ├── app/                 # API, models, schemas, xác thực, seed
│   ├── alembic/             # Migration cơ sở dữ liệu
│   ├── tests/               # Kiểm thử backend
│   ├── .env.example
│   └── requirements.txt
├── Frontend/
│   ├── src/app/             # Giao diện và routes
│   ├── src/api/             # HTTP client và refresh token
│   ├── src/services/        # Gọi backend API
│   ├── src/mock/            # Dữ liệu mock cũ
│   ├── .env.example
│   └── package.json
└── docs/                    # Tài liệu báo cáo
```

## Cài đặt và chạy local

### 1. Chuẩn bị

- Python 3.10 trở lên (mã nguồn dùng cú pháp kiểu `str | None`).
- Node.js 22.12 trở lên và npm, phù hợp với dependency frontend hiện tại.
- PostgreSQL đang chạy; có tài khoản được phép tạo database.

Các lệnh dưới đây dùng **PowerShell trên Windows**, bắt đầu tại thư mục gốc project.

### 2. Tạo database

Mở psql hoặc Query Tool của pgAdmin bằng tài khoản quản trị PostgreSQL, chạy từng câu lệnh nếu user/database chưa tồn tại:

```sql
CREATE USER evently WITH PASSWORD 'evently';
CREATE DATABASE evently OWNER evently;
```

Đây là thông tin kết nối mẫu cho local. Nếu dùng thông tin khác, cập nhật `DATABASE_URL` tương ứng.

### 3. Cấu hình và chạy backend

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Nếu đã có `.env`, giữ cấu hình hiện tại thay vì sao chép đè. Kiểm tra `Backend/.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://evently:evently@localhost:5432/evently
JWT_SECRET=replace-with-a-long-random-secret
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=7
FRONTEND_ORIGIN=http://localhost:5173
```

Đặt `JWT_SECRET` thành chuỗi bí mật ngẫu nhiên riêng. Vẫn trong thư mục `Backend`, tạo schema, nạp dữ liệu demo và chạy API:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Seed tạo 6 tài khoản, 6 sự kiện, phân công nhân viên và một vé mẫu. **Nếu database đã có bất kỳ user nào, seed bỏ qua toàn bộ việc nạp dữ liệu** và in `Database already seeded`. Script không tạo PostgreSQL database; cần hoàn tất bước 2 trước.

- API: [http://localhost:8000](http://localhost:8000).
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs).
- Kiểm tra API: [http://localhost:8000/health](http://localhost:8000/health), trả `{"status":"ok"}`. Endpoint này không kiểm tra kết nối database.

### 4. Cấu hình và chạy frontend

Mở **terminal thứ hai** tại thư mục gốc project:

```powershell
cd Frontend
npm ci
Copy-Item .env.example .env
```

Nếu đã có `.env`, chỉ kiểm tra và cập nhật khi cần. Nội dung `Frontend/.env`:

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
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term
```

Kiểm tra và build frontend từ thư mục `Frontend`:

```powershell
npm run lint
npm run build
npm run preview
```

Preview phục vụ bản build ở URL được in trong terminal; vẫn cần backend để đăng nhập và thao tác dữ liệu.

## Lỗi thường gặp

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
