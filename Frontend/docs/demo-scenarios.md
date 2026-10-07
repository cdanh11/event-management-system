# Demo FastAPI end-to-end — 5–7 phút

Chuẩn bị PostgreSQL, migration, seed, backend và frontend. Mật khẩu tài khoản demo: 123456. Dùng hai browser profile độc lập; tạo event mới để không phụ thuộc thời gian/vé của lần demo trước.

## 1. Swagger và validation — 1 phút

Mở http://localhost:8000/docs. Login organizer@demo.com, Authorize bằng access_token. Giải thích schema Pydantic, Depends và security của route. Thử capacity âm hoặc end trước start để thấy 422; route bảo vệ thiếu token trả 401, sai role trả 403.

## 2. Organizer chuẩn bị — 1 phút

Login organizer → Create event. Nhập lịch ngày mai, capacity 5, tên dễ tìm → Create draft → Publish. Tab Staff gán staff@demo.com. Có thể đổi lịch ở Schedule trước khi mở cửa.

## 3. Đăng ký và realtime — 1–2 phút

Organizer mở Live và chọn event mới. Profile B login attendee@demo.com → Explore → event → Register. Số Registered tăng 1, Left giảm 1 và Last changes thêm +1 không reload. Mở My tickets và View ticket, sao chép mã vé.

Để demo hủy: dùng một attendee khác như linh@demo.com đăng ký rồi Cancel registration khi Published. Live nhận +1 rồi -1. Giữ vé của attendee@demo.com cho bước check-in; vé của Linh đã hủy không dùng được và không đăng ký lại cùng event.

## 4. Check-in — 1–2 phút

Organizer về Manage → Start event (STARTED). Profile B sign out attendee rồi login staff@demo.com → Check-in → chọn event mới → nhập mã vé đã giữ → Enter. Kết quả Admitted, lịch sử có lượt thành công. Nhập lại cùng mã → Already scanned; nhập mã không tồn tại → Not found.

Giải thích ticket lock và UNIQUE checkins.ticket_id. Registered không tăng khi check-in vì đó là số đăng ký, không phải số người vào cửa.

## 5. Async và kết thúc — 1 phút

Organizer chọn Notify attendees: SMTP/Mailpit nhận email thật (vé có PNG QR); nếu cả SMTP và webhook trống thì simulated. Chỉ ra SMTP chạy trong thread hoặc async HTTP I/O của notifier, và BackgroundTasks sau commit. Complete event đóng cửa. Giải thích lifespan task tự mở cửa trước start 15 phút và hoàn thành sau end, tối đa một chu kỳ quét 60 giây.

Khi được hỏi về mở rộng: WS/ticket hiện trong RAM một worker; nhiều worker cần pub/sub dùng chung. BackgroundTasks không có hàng đợi/retry bền vững. Test SQLite kiểm tra API, test PostgreSQL kiểm chứng FOR UPDATE.
