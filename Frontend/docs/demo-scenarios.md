# Kịch bản demo end-to-end

Điều kiện: backend + PostgreSQL đã chạy, đã seed (`python -m app.seed`).

## 1. Tự đăng ký & tham dự (ATTENDEE)

1. Mở `/login` → **Create an attendee account**, tạo tài khoản mới.
2. Tại `/events`, tìm sự kiện `PUBLISHED` còn chỗ → **View event** → **Register now**.
3. Mở `/registrations` → **View ticket** xem mã vé → **Cancel** để hủy (vé vô hiệu, trả slot).

## 2. Trường hợp biên

- Event đầy chỗ (ví dụ **Career Fair: Future Makers** sau seed) hiển thị **Sold out**.
- Đăng ký trùng (kể cả sau khi đã hủy) → lỗi `ALREADY_REGISTERED`.
- Đăng ký event chưa `PUBLISHED` hoặc đã qua giờ bắt đầu → `REGISTRATION_CLOSED` / `EVENT_STARTED`.

## 3. Check-in (STAFF)

1. Đăng nhập `staff@demo.com`, mở **Check-in**.
2. Nhập `AI-MEET-2026` (vé của `attendee@demo.com` cho **AI Product Meetup** `ONGOING`)
   → **Validate & check in**.
3. Nhập lại cùng mã → lỗi `TICKET_ALREADY_USED` (vé một lần duy nhất).

## 4. Quản lý (ORGANIZER)

1. Đăng nhập `organizer@demo.com` → **Dashboard** xem tổng đăng ký/check-in.
2. **Create event** → tạo nháp `DRAFT` → trang **Manage**: **Publish** → **Start** →
   **Mark completed**; **Reschedule** đổi giờ; **Notify attendees** gửi thông báo;
   **Delete draft** xóa khi còn nháp; **Cancel event** khi `DRAFT`/`PUBLISHED`.
3. **Assign staff**: chọn tài khoản staff trong dropdown để phân công check-in.
4. Mở `/organizer/live` xem occupancy realtime (kịch bản ở [`realtime-dashboard.md`](realtime-dashboard.md)).
