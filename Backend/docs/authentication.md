# Xác thực & phân quyền

## Tổng quan

Evently dùng JWT access token (header `Authorization: Bearer`) kết hợp refresh token
xoay vòng trong cookie `HttpOnly`. Mọi quy tắc nằm ở `app/deps.py` và `app/routers/auth.py`.

## Luồng

```text
Đăng ký/đăng nhập → access token (15 phút) + refresh cookie (7 ngày)
       |
Mỗi request → Depends(require("<ROLE>")) → Depends(current_user)
       |── HTTPBearer đọc header (thiếu header → 401, không phải 403)
       |── decode JWT → db.get(User, sub) → kiểm tra role → 403 nếu sai quyền
       └── GET /auth/me: trả thông tin user hiện tại
```

| Endpoint | Quyền | Ghi chú |
| --- | --- | --- |
| `POST /auth/register` (201) | public | Tự mở tài khoản **ATTENDEE**; server ấn định role, client không thể tự nâng quyền |
| `POST /auth/login` | public | Sai mật khẩu → `401 INVALID_CREDENTIALS` |
| `POST /auth/refresh` | cookie | Xoay vòng: thu hồi token cũ, cấp cặp mới |
| `POST /auth/logout` (204) | cookie (nếu có) | Thu hồi refresh token, xóa cookie |
| `GET /auth/me` | Bearer | Kiểm tra token nhanh |

## Vai trò

| Role | Được phép |
| --- | --- |
| `ATTENDEE` | Đăng ký/hủy vé của chính mình, xem vé của mình |
| `STAFF` | Check-in vé thuộc sự kiện được phân công |
| `ORGANIZER` | Tạo/sửa/xóa nháp, chuyển trạng thái, gán staff, notify, xem dashboard và occupancy |

Ngoài kiểm tra role, router còn kiểm tra **ownership**: organizer chỉ thao tác
sự kiện của chính mình (`event.organizer_id != user.id` → `403 FORBIDDEN`).

## Bảo mật mật khẩu & token

- Mật khẩu băm Argon2 (`pwdlib`), không bao giờ lưu plaintext.
- Refresh token chỉ lưu **hash SHA-256** trong bảng `refresh_tokens`; lộ DB cũng không dùng được token.
- Cookie `HttpOnly` + `SameSite=lax` (bật `secure=True` khi chạy HTTPS production).
- Secret trong `.env.example`/Compose chỉ dùng cho local development.

## WebSocket

Kênh realtime không dùng Bearer header (trình duyệt không gắn được header cho WS).
Thay vào đó là **ticket handshake một lần**, xem chi tiết ở [`realtime.md`](realtime.md).
