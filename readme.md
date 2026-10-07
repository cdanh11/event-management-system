# Evently — Đồ án FastAPI

Đồ án môn **Công nghệ Lập trình Hiện đại**, tìm hiểu và xây dựng dịch vụ backend với FastAPI. Evently minh họa quản lý sự kiện, đăng ký vé và check-in qua ba vai trò. Frontend là web MVP phục vụ sử dụng và demo API.

## Công nghệ và kiến trúc

```text
React / TypeScript / Vite
    ├── REST + JWT Bearer / refresh cookie
    └── WebSocket occupancy
            ↓
FastAPI → SQLAlchemy 2 → PostgreSQL 16
    ├── Pydantic v2: request/response và validation
    ├── Depends: DB session, xác thực và phân quyền
    ├── BackgroundTasks: thông báo sau commit
    └── lifespan: lifecycle sự kiện và giải phóng tài nguyên
```

Bảy bảng: users, events, registrations, tickets, checkins, staff_event_assignments và refresh_tokens. Xem [minh chứng FastAPI](Backend/README.md) và [kết quả rà soát](docs/final-review.md).

## Cài đặt và chạy

Yêu cầu: Python 3.12+ (đã kiểm chứng local với 3.14), Node.js 22.12+ và Docker Desktop đang chạy Linux containers. Các lệnh dưới đây dùng PowerShell, bắt đầu tại thư mục gốc project.

**Chuẩn bị máy mới và clone**

| Công cụ | Vai trò |
| --- | --- |
| Git | Clone/pull source; có thể thay bằng tải ZIP nếu không cần thao tác Git |
| Python 3.12+ | Chạy FastAPI, Alembic và seed trên máy host |
| Node.js 22.12+ và npm | Cài/build/chạy frontend Vite |
| Docker Desktop (Linux containers) | Chạy PostgreSQL; pgAdmin/Mailpit tùy chọn |
| VS Code | Editor/terminal thuận tiện; không bắt buộc và không thay cho Python/Node |
| Trình duyệt và Internet lần cài đầu | Dùng web/Swagger và tải dependency/Docker image |

Trên Windows, Docker Desktop cần backend WSL 2 hoặc Hyper-V theo [hướng dẫn Docker](https://docs.docker.com/desktop/setup/install/windows-install/). Với cấu hình hiện tại, Docker chỉ đóng gói database và công cụ hỗ trợ; backend/frontend chạy trên host, vì vậy chỉ cài VS Code và Docker là chưa đủ.

```powershell
git clone https://github.com/cdanh11/event-management-system.git
cd event-management-system
# Tùy chọn: code .
python --version
node --version
npm --version
docker compose version
```

Cần clone phiên bản chứa source mới: backend PR #9 đã merge; source frontend hoàn chỉnh nằm trong PR #10 (foundation, gồm cả attendee/operations), sau đó merge documentation. Main chỉ có đầy đủ sau khi merge. Trước khi merge, dùng `git switch --track origin/feature/uiux-v2-documentation` để chạy toàn bộ source cuối. Repo private cần quyền truy cập. Sau clone thực hiện lần lượt các bước dưới đây; không sao chép .venv/node_modules/database từ máy khác.

**1. PostgreSQL**

```powershell
docker compose up -d db
docker compose ps
```

Database `evently`, user/password `evently`, cổng host `5433`. pgAdmin là tùy chọn: `docker compose --profile tools up -d`; mở `http://localhost:5050`, tài khoản `admin@evently.local` / `admin`. Kết nối server trong pgAdmin bằng host `db`, port `5432`.

**2. Backend**

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
Copy-Item .env.example .env
# Tạo secret riêng cho máy này và cập nhật đúng một biến, không cần activate venv.
.\.venv\Scripts\python.exe -c "from pathlib import Path; import re,secrets; p=Path('.env'); p.write_text(re.sub(r'^JWT_SECRET=.*$', 'JWT_SECRET='+secrets.token_urlsafe(48), p.read_text(encoding='utf-8-sig'), flags=re.M), encoding='utf-8')"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

API: `http://localhost:8000` · Swagger: `http://localhost:8000/docs` · OpenAPI: `/openapi.json` · Liveness: `/health`.

Seed bổ sung dataset đánh số ngay cả khi DB đã có dữ liệu; chạy lại không nhân bản hoặc đặt lại dữ liệu của các lần demo trước. Thời gian sự kiện mẫu được tính từ lúc seed. Nếu vé mẫu đã dùng hoặc sự kiện đã kết thúc, hãy tạo sự kiện mới theo kịch bản bên dưới.

**3. Frontend** — terminal thứ hai, từ thư mục gốc:

```powershell
cd Frontend
npm ci
Copy-Item .env.example .env
npm run dev -- --port 5173
```

Mở `http://localhost:5173`. Dùng nhất quán `localhost` cho frontend và API để refresh cookie hoạt động. Dừng server bằng Ctrl+C; `docker compose down` dừng DB và giữ volume.

## Email vé và QR khi demo

Mailpit là hộp thư SMTP local, giữ thư ngay trên máy và không chuyển tới email ngoài. Khởi chạy từ thư mục gốc:

```powershell
docker compose --profile mail up -d mailpit
```

Đặt trong `Backend/.env`, rồi khởi động lại backend:

```dotenv
SMTP_HOST=127.0.0.1
SMTP_PORT=1025
SMTP_STARTTLS=false
SMTP_SSL=false
SMTP_FROM=evently@localhost
```

Mở `http://localhost:8025`. Đăng ký một sự kiện Published bằng attendee chưa đăng ký trước đó: email xác nhận chứa mã vé và file `ticket-qr.png`. Backend cấp vé trước, gửi thư bằng BackgroundTasks sau commit. Notify attendees cũng gửi qua SMTP. Hộp thư local không yêu cầu tài khoản email; không dùng cấu hình không TLS này cho SMTP bên ngoài.

SMTP thật có thể cấu hình thêm username/password và STARTTLS/SSL theo nhà cung cấp. Thứ tự ưu tiên: SMTP → webhook → simulated. Lỗi gửi nền không làm mất vé; thông báo thủ công lỗi transport trả 502. Xem [tài liệu Mailpit](https://mailpit.axllent.org/docs/install/docker/).

## Tài khoản demo

Mật khẩu chung: **123456**.

| Vai trò | Email | Chức năng |
| --- | --- | --- |
| ORGANIZER (2) | organizer1, organizer2 (hoặc organizer1@demo.com…) | Tạo, dời lịch, công bố, gán staff, vận hành, thông báo và Dashboard |
| STAFF (5) | staff1…staff5 (hoặc staff1@demo.com…) | Check-in sự kiện được phân công |
| ATTENDEE (100) | user1…user100 (hoặc user1@demo.com…) | Đăng ký, xem vé và hủy đăng ký |

Dataset mới có 10 Published còn chỗ đăng ký, 5 Completed; 278 đăng ký/vé và 75 check-in thật (15 mỗi sự kiện đã hoàn thành), 30 assignment. Hai organizer chia nhau sở hữu sự kiện; năm staff được phân công theo vòng. user100 chưa đăng ký các event mở, tiện thử Register. Vé mở có mã `DEMO-OPEN-01-U001`; vé đã check-in có trạng thái USED. Muốn thử scan mới, organizer chuyển một event mở sang STARTED trước. Dữ liệu cũ được giữ nên tổng DB hiện có thể lớn hơn dataset này.

Username ngắn chỉ là alias demo trỏ tới email đánh số, không xác thực theo tên hiển thị và không đổi quyền. Đăng ký tài khoản mới từ trang login luôn tạo ATTENDEE. Organizer có thể tạo STAFF trong tab Staff.

## Hướng dẫn sử dụng

1. **Organizer:** Create event → điền tên, mô tả, địa điểm, thời gian tương lai và số chỗ → Create draft → Publish. Trong Manage, tab Staff dùng để gán nhân viên; Schedule để sửa lịch; Check-in để trực tiếp soát vé.
2. **Attendee:** Explore → tìm sự kiện → Register và xác nhận → xem vé QR/mã vé. My tickets lưu các vé Upcoming, Past và Cancelled. Cancel registration chỉ được phép khi sự kiện còn Published; hủy trả lại một chỗ.
3. **Staff:** Check-in → chọn sự kiện được phân công → nhập mã hoặc dùng máy quét có đầu ra bàn phím → Enter. Banner kết quả tự ẩn sau 5 giây; Last scan giữ kết quả cuối, Recent check-ins lấy lượt thành công từ API.
4. **Realtime:** organizer mở Dashboard; attendee đăng ký/hủy ở browser profile khác. Registered và Left cập nhật qua WebSocket; REST dự phòng khi mất kết nối. Registered là số đăng ký, không phải số người đã check-in.
5. **Kết thúc:** organizer chọn Complete event; Notify attendees gửi thông báo theo chế độ cấu hình. SMTP gửi email thật kèm QR; webhook là transport thay thế. Không cấu hình cả hai thì chỉ mô phỏng.

Vòng đời: `DRAFT → PUBLISHED → ONGOING → STARTED → COMPLETED`. Có thể chuyển trực tiếp PUBLISHED → STARTED; hủy sự kiện ở DRAFT/PUBLISHED/ONGOING. ONGOING đóng đăng ký để chuẩn bị, STARTED mới mở check-in. Backend tự mở trước giờ bắt đầu 15 phút và kết thúc khi hết giờ, quét mỗi 60 giây.

Chỉ sửa sự kiện khi DRAFT/PUBLISHED; capacity không được thấp hơn số đăng ký. Chỉ xóa nháp DRAFT. Một attendee không thể đăng ký lại cùng sự kiện sau khi hủy; dùng attendee khác để tiếp tục thử. Vé đã check-in chỉ dùng một lần.

Kịch bản bảo vệ 5–7 phút: [demo end-to-end](Frontend/docs/demo-scenarios.md).

## Thử bằng Swagger

1. Chọn **Authorize** trong Swagger; username là email hoặc alias demo, password là `123456`; giữ client_id/client_secret trống.
2. Swagger gọi OAuth2 password flow `POST /auth/token` và tự gắn Bearer JWT. Web frontend tiếp tục dùng `POST /auth/login` JSON. Đổi vai trò bằng Logout trong Authorize rồi đăng nhập lại.
3. Tạo event và lấy ID từ response; Publish bằng `POST /events/{id}/transition`.
4. Đổi token attendee để gọi register; đổi token organizer/staff để check-in.
5. Thử capacity âm hoặc end trước start → 422; thiếu token → 401; sai quyền → 403; đăng ký trùng/đầy → 409.

WebSocket được hướng dẫn riêng trong [tài liệu realtime](Backend/docs/realtime.md); OpenAPI chỉ mô tả các route HTTP.

## Kiểm thử

```powershell
# Tại Backend: tests mặc định dùng SQLite riêng, không cần DB phát triển.
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term

# Tại Frontend
npm run lint
npm test
npm run audit:copy
npm run build
```

SQLite kiểm tra luồng API; PostgreSQL kiểm chứng khóa dòng và chống overbooking. Xem [hướng dẫn kiểm thử](Backend/docs/testing.md), [hiệu năng](Backend/docs/performance.md) và [kết quả rà soát](docs/final-review.md). CI cấu hình PostgreSQL service để chạy cả hai test concurrency, cùng backend coverage và frontend checks. Chưa có run remote cho source chưa commit.

## Tài liệu và giới hạn

- [Backend](Backend/README.md): cấu trúc code, minh chứng FastAPI, API và quy tắc phát triển.
- [Frontend](Frontend/README.md): màn hình và cách sử dụng client demo.
- [Danh mục tài liệu](docs/README.md): báo cáo, ERD và tài liệu kỹ thuật.
- [Giới hạn kỹ thuật](docs/gioi-han-ky-thuat.md): một worker, thông báo không có retry/queue, thời gian địa phương và phạm vi triển khai.

Source hoàn thành trong phạm vi web MVP một worker. Báo cáo Word do nhóm thực hiện riêng; tài liệu kỹ thuật chỉ ghi hành vi source và cách tái hiện kiểm chứng.

## Xử lý sự cố

| Hiện tượng | Kiểm tra |
| --- | --- |
| Không kết nối DB | Docker Desktop, `docker compose ps`, `docker compose port db 5432`, DATABASE_URL đúng cổng |
| Thiếu bảng | Chạy alembic upgrade head trên đúng database |
| Login demo không được | DB đã seed chưa; seed bỏ qua nếu đã có user |
| Failed to fetch / CORS | Backend đang chạy, VITE_API_BASE_URL và FRONTEND_ORIGIN đúng, cùng hostname |
| Không đăng ký được | Event PUBLISHED, còn chỗ, chưa qua giờ, attendee chưa đăng ký lần nào |
| Không check-in được | Event STARTED, vé VALID, đúng event đang chọn, organizer sở hữu hoặc staff được gán |
| Dashboard không tăng khi check-in | Occupancy đếm đăng ký; check-in cập nhật lịch sử và dashboard, không tăng registered_count |
