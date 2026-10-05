# Dashboard realtime (`/organizer/live`)

Màn hình cho organizer xem số vé còn lại **tự nhảy số** khi có đăng ký/hủy,
không cần tải lại trang.

## Cách hoạt động

1. `useOccupancySocket(eventId)` gọi `POST /ws/ticket` (kèm Bearer token) để lấy
   ticket WebSocket một lần (hiệu lực 30 giây).
2. Mở `WS /ws/events/{eventId}?ticket=...`; message đầu là **snapshot** để vẽ ngay,
   các message sau cập nhật `registered_count`/`remaining` trực tiếp.
3. Mất kết nối thường (rớt mạng, ticket hết hạn → mã đóng `4401`) thì lấy ticket mới
   và nối lại với backoff, tối đa 5 lần. Mã `4403` (sai role) và `4404` (sai event)
   dừng hẳn và hiển thị lỗi.

## Demo hai trình duyệt (kịch bản bảo vệ)

1. Trình duyệt A đăng nhập `organizer@demo.com`, mở `/organizer/live` → thấy `LIVE`.
2. Trình duyệt B đăng nhập `attendee@demo.com`, đăng ký một vé của event đang xem.
3. Số **Remaining** ở trình duyệt A tự giảm; hủy vé thì số tự tăng lại.

Logic socket (`src/realtime/`) tách khỏi giao diện (`src/features/realtime/`) nên
đổi theme chỉ cần thay JSX, không chạm realtime.
