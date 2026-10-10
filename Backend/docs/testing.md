# Kiểm thử backend

## API và unit tests

Chạy từ Backend:

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term
```

Fixture tạo SQLite in-memory riêng, override get_db và thay session factory của lifecycle. Không dùng DB phát triển cho sweeper trong tests. Mỗi test tạo/xóa bảng riêng. auth_headers tạo user và login bằng API thật.

Bao phủ auth/rotation, validation, ownership, trạng thái, đăng ký/hủy, check-in một lần, chọn đúng event, capacity, webhook và WS. test_final_review.py giữ các ca hồi quy của đợt rà soát. test_release.py kiểm chứng OAuth2 form/role, OpenAPI DTO, organizer pagination, PATCH capacity qua WebSocket thật và email PNG QR bằng SMTP inbox local. Test gửi email không gọi dịch vụ bên ngoài. SQLite không hỗ trợ FOR UPDATE như PostgreSQL.

Các ca hết hạn kiểm tra access JWT ký đúng nhưng exp đã qua, refresh cookie còn
trên client nhưng bản ghi DB hết hạn, và WS ticket hết TTL. Test WS thay đồng hồ
của riêng module realtime, không sleep hoặc thay đồng hồ của event loop. Kết nối
thiếu/đã dùng/hết hạn ticket phải ném WebSocketDisconnect với code 4401; không
bắt Exception chung vì có thể nuốt cả assertion của test.

## Kiểm thử PostgreSQL thật

Dùng database riêng, ví dụ tạo khi Compose DB đang chạy (lệnh từ thư mục gốc):

```powershell
docker compose exec -T db createdb -U evently evently_test
```

Sau đó tại Backend:

```powershell
$env:DATABASE_URL='postgresql+psycopg://evently:evently@localhost:5433/evently_test?connect_timeout=5'
$env:TEST_POSTGRES_URL=$env:DATABASE_URL
$env:NOTIFY_WEBHOOK_URL=''
$env:SMTP_HOST=''
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term
Remove-Item Env:TEST_POSTGRES_URL
Remove-Item Env:DATABASE_URL
```

Đặt DATABASE_URL cùng DB test để lifespan không quét dữ liệu demo. Test từ chối DB có tên evently. Nếu thiếu TEST_POSTGRES_URL, các test PG được skip.

Hai kịch bản: capacity=1 với 5 attendee đồng thời → một 201 và bốn 409; hai request dùng cùng refresh cookie → một 200 và một 401. Dữ liệu test có email UUID riêng và được dọn theo FK trong finally.

## CI và kết quả

.github/workflows/ci.yml chạy backend pytest/coverage và frontend lint/test/audit-copy/build. CI tạo PostgreSQL service riêng, migration rồi chạy cả SQLite API tests và PostgreSQL concurrency tests. Kết quả của bản rà soát hiện tại được ghi tại [final-review](../../docs/final-review.md), không dùng số test lịch sử từ các phase cũ.
