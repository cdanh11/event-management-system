# Xác thực và phân quyền

Access token JWT HS256 dùng header Authorization: Bearer, mặc định 15 phút. Refresh token ngẫu nhiên nằm trong cookie HttpOnly/SameSite=lax, mặc định 7 ngày; DB chỉ lưu hash SHA-256. Mật khẩu dùng Argon2.

## Luồng và endpoint

| Endpoint | Hành vi |
| --- | --- |
| POST /auth/register | Tạo ATTENDEE, role do server ấn định; trả 201 và đăng nhập |
| POST /auth/token | OAuth2 password flow: form grant_type=password, username=email; cấp JWT/refresh cookie |
| POST /auth/login | Kiểm tra email/password, cấp access token và refresh cookie |
| POST /auth/refresh | Khóa dòng refresh token, thu hồi token cũ và cấp cặp mới |
| POST /auth/logout | Thu hồi refresh token hiện tại, xóa cookie, trả 204 |
| GET /auth/me | Xác thực JWT và trả thông tin user |

require(role) → current_user → OAuth2PasswordBearer + get_db. Thiếu/sai JWT trả 401 kèm WWW-Authenticate: Bearer; sai role trả 403. Role được đọc từ user trong DB. Lỗi DB không bị che thành lỗi token.

Role chỉ là lớp kiểm tra đầu. Organizer phải sở hữu event khi thay đổi; staff phải được gán để check-in. access.py bảo vệ đăng ký/vé: attendee sở hữu, organizer sở hữu event hoặc staff được gán. Người có role đúng nhưng thuộc event khác không được đọc dữ liệu cá nhân.

Unique email bảo vệ cả khi đăng ký tài khoản đồng thời. Refresh rotation dùng FOR UPDATE trên PostgreSQL để cùng một token chỉ đổi thành công một lần; client sử dụng single-flight để tránh tự gửi hai lần refresh.

## Cấu hình và giới hạn

JWT_SECRET riêng ít nhất 32 byte. COOKIE_SECURE=true khi dùng HTTPS; local HTTP để false. Logout thu hồi refresh hiện tại, không vô hiệu ngay access JWT đã cấp; token đó còn hiệu lực tới exp. Chưa có quản lý tất cả phiên hoặc tác vụ dọn token hết hạn.

WebSocket dùng ticket 30 giây một lần thay cho access JWT trên URL, xem [realtime](realtime.md). Ticket/occupancy không mang dữ liệu vé cá nhân.

Swagger Authorize sử dụng `/auth/token`; grant_type sai trả 422. Client gửi scopes không được nâng quyền: RBAC lấy role từ DB, không triển khai quyền bằng OAuth2 scopes. Không có ADMIN độc lập; ORGANIZER quản lý các sự kiện mình sở hữu.

Alias demo `user1`, `staff1`, `organizer1` ánh xạ tới email tương ứng @demo.com; JSON login vẫn dùng field email và OAuth2 dùng field username. Email thật đăng nhập như trước; signup vẫn chỉ chấp nhận email hợp lệ. Không lấy User.name làm khóa xác thực.
