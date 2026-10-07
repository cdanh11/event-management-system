# Evently Backend

FastAPI là trọng tâm đồ án. Backend triển khai xác thực, phân quyền theo tài nguyên, quản lý vòng đời sự kiện, đăng ký/vé, check-in và WebSocket occupancy trên PostgreSQL.

## Chạy và sử dụng

Thực hiện [hướng dẫn cài đặt ở README gốc](../readme.md#cài-đặt-và-chạy). Chạy lệnh từ Backend:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Mở `/docs`, chọn Authorize, nhập email hoặc username đánh số vào username và mật khẩu tài khoản. OAuth2 password flow gọi `/auth/token`; `/auth/login` JSON vẫn dành cho frontend. Chạy một worker vì WS room và ticket nằm trong RAM tiến trình. `/health` kiểm tra ứng dụng còn phản hồi, không kiểm tra DB.

## Cấu trúc và trách nhiệm

| File/thư mục | Trách nhiệm |
| --- | --- |
| app/main.py | App, lifespan, middleware, exception handlers và OpenAPI |
| app/config.py, db.py | Biến môi trường, engine/session và yield dependency |
| app/models.py, schemas.py | Bảng ORM và hợp đồng Pydantic request/response |
| app/deps.py, access.py | Xác thực, role và quyền trên đăng ký/vé cụ thể |
| app/security.py | Argon2, JWT và hash refresh token |
| app/serializers.py, errors.py | Mapping ORM/API và lỗi nghiệp vụ thống nhất |
| app/routers/ | HTTP/WS endpoints theo tài nguyên |
| app/realtime.py | WS rooms, snapshot và ticket dùng một lần |
| app/services/lifecycle.py | Tự chuyển trạng thái theo giờ |
| app/services/notifier.py | Webhook async, SMTP trong thread, email/QR và xử lý lỗi transport |
| app/seed.py | Dữ liệu mẫu có registration/ticket thật, counter khớp dữ liệu |
| alembic/ | Migration 0001 schema cố định, 0002 composite index |
| tests/, scripts/ | Kiểm thử và benchmark PostgreSQL |

## Minh chứng FastAPI

| Kỹ thuật | Minh chứng trong project |
| --- | --- |
| Pydantic v2 | Field, EmailStr, Enum, field_validator thời gian/chuỗi, model_validator start/end; 422 trước endpoint |
| Dependency injection | get_db → current_user → require(role); dependency sync chuẩn bị dữ liệu cho notify/WS |
| Auth và quyền | OAuth2PasswordBearer, form password flow, JWT, refresh rotation với row lock; owner/assigned staff trong access.py |
| Sync/async đúng chỗ | Router DB dùng def; notifier/WS dùng async cho I/O; sweeper gọi DB bằng asyncio.to_thread |
| OpenAPI | response_model cho các tài nguyên, tags, security theo từng operation, schema lỗi dùng chung |
| Exception handlers | HTTP và validation trả body thống nhất; giữ WWW-Authenticate và details |
| Middleware | CORS và X-Process-Time-Ms; expose cursor/timing cho browser |
| Lifespan | Quét startup, chạy lifecycle task; cancel/await task và đóng HTTP client/engine khi shutdown |
| BackgroundTasks | Broadcast, gửi vé và thông báo sau commit; không truyền ORM vào task |
| WebSocket | Ticket 30 giây dùng một lần, snapshot rồi broadcast theo event room |
| TestClient/override | SQLite riêng cho API và lifecycle; PostgreSQL riêng cho FOR UPDATE |

## Quy tắc nghiệp vụ

- Đăng ký chỉ mở ở PUBLISHED, trước giờ bắt đầu, còn chỗ và không trùng attendee/event.
- Đăng ký + vé + counter cùng transaction. Khóa Event trước Registration/Ticket khi ghi dữ liệu liên quan để hạn chế deadlock.
- Hủy đăng ký chỉ ở PUBLISHED; lần hủy lại trả kết quả cũ. Vé đã dùng không được hủy.
- Check-in chỉ ở STARTED. STAFF phải được gán; ORGANIZER phải sở hữu event. Check-in gửi event_id để tránh nhận vé của event khác.
- Sửa/dời lịch chỉ DRAFT/PUBLISHED; không giảm capacity dưới registered_count. Xóa nháp dọn assignment trước để đúng FK.
- Lifecycle quét mỗi 60 giây, STARTED trước start 15 phút, COMPLETED khi quá end. Sau downtime, event quá hạn được COMPLETED trong một lượt quét.
- Notify thủ công chờ SMTP/webhook và trả 502 khi transport thất bại. Thông báo nền ghi log lỗi; dữ liệu đã commit không rollback theo lỗi gửi.

## Hướng dẫn phát triển

Thêm input/output schema ở schemas.py, route ở router phù hợp, dùng Depends để xác thực/DB và kiểm tra quyền tài nguyên. Giữ DB đồng bộ trong def hoặc dependency sync; không gọi Session sync trực tiếp trong vòng lặp async. Commit dữ liệu trước khi broadcast và chỉ đưa dữ liệu thuần vào BackgroundTasks.

Thêm migration mới khi thay schema; không dùng metadata runtime để tạo lại migration cũ. Thêm test cho quy tắc nghiệp vụ mới và ca lỗi ảnh hưởng dữ liệu. Comment giải thích quyết định transaction, locking, thời gian và async; tránh comment lặp lại câu lệnh.

## Tài liệu chuyên đề

- [Xác thực](docs/authentication.md)
- [Validation và mã lỗi](docs/validation-errors.md)
- [Realtime, async và task nền](docs/realtime.md)
- [Kiểm thử](docs/testing.md)
- [Hiệu năng](docs/performance.md)
- [Giới hạn và triển khai](../docs/gioi-han-ky-thuat.md)
