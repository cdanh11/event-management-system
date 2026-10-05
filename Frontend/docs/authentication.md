# Đăng nhập & phiên làm việc

## Luồng

1. `/login` có hai chế độ: **Sign in** và **Sign up** (tự mở tài khoản `ATTENDEE`
   qua `POST /auth/register`; mật khẩu tối thiểu 6 ký tự).
2. `AuthContext.login/register` lưu access token vào bộ nhớ (biến module trong
   `apiClient.ts`, không lưu localStorage) và lưu `user` vào localStorage để giữ
   phiên hiển thị.
3. Khi app khởi động, `AuthProvider` gọi `GET /auth/me` để khôi phục phiên; refresh
   token trong HttpOnly cookie tự làm mới access token khi gặp `401`.
4. `logout` gọi `POST /auth/logout`, xóa token và user.

## Phân luồng theo vai trò

| Role | Trang chủ | Chức năng |
| --- | --- | --- |
| `ATTENDEE` | `/events` | Khám phá, đăng ký/hủy vé, xem vé (`/registrations`, `/tickets/:id`) |
| `STAFF` | `/staff/check-in` | Check-in vé bằng ticket code |
| `ORGANIZER` | `/organizer` | Dashboard, tạo/quản lý event, live occupancy (`/organizer/live`) |

`RoleGate` chặn route sai vai trò và điều hướng về trang chủ đúng role.
Tài khoản demo (mật khẩu `123456`): `attendee@demo.com`, `staff@demo.com`,
`organizer@demo.com` — chỉ có sau khi chạy seed backend.
