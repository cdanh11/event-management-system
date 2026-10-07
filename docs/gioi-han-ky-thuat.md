# Giới hạn và điều kiện triển khai

## Phạm vi MVP

Đồ án minh chứng FastAPI, không triển khai thanh toán, upload ảnh, quét QR bằng camera, hộp thư push hoặc hệ thống email production. Web client hỗ trợ thao tác demo; máy quét vé có đầu ra bàn phím có thể dùng với ô mã.

## Một worker

ConnectionManager và WS ticket nằm trong RAM. Chạy một Uvicorn worker; nhiều worker có thể không tìm thấy ticket hoặc không nhận broadcast ở worker khác. Lifecycle cũng chạy trong từng tiến trình. Mở rộng cần shared ticket store/pub-sub và scheduler có cơ chế điều phối.

Occupancy là dữ liệu công khai trong catalog; mọi user đã login được subscribe. WS ticket không gắn event và không phải kênh dữ liệu cá nhân. GET events hiện công khai cả nháp; UI lọc nháp nhưng đó không phải ranh giới bảo mật. Nếu nháp phải bí mật, cần đổi contract catalog/detail và kiểm thử quyền trước khi triển khai sản phẩm.

## Thông báo

SMTP_HOST bật gửi email/QR qua SMTP; không có SMTP thì dùng webhook nếu được cấu hình; không có cả hai thì mô phỏng I/O. Mailpit profile mail phục vụ hộp thư demo local. BackgroundTasks chạy sau commit, không có retry bền vững/outbox. Lỗi gửi nền ghi log; Notify thủ công trả 502 khi transport lỗi. Không đảm bảo giao email tới người nhận.

## Thời gian

start/end dùng DateTime naive theo giờ địa phương máy chủ. Input có timezone được đổi sang giờ địa phương trước validation/lưu; timestamp nội bộ/audit là UTC naive. Demo cần server và browser cùng timezone, ví dụ Asia/Ho_Chi_Minh. Triển khai đa múi giờ cần contract UTC aware và timezone hiển thị rõ ràng.

Lifecycle mỗi 60 giây nên trạng thái tự động có thể trễ một chu kỳ; có thể chuyển thủ công khi demo. Startup catch-up hoàn thành sự kiện đã hết giờ.

## Giao dịch và kiểm thử

PostgreSQL FOR UPDATE giữ bất biến capacity/vé; SQLite không chứng minh được row lock. Các thao tác ghi dùng thứ tự Event trước Registration/Ticket. Check-in một vé chỉ một lần nhờ lock và UNIQUE.

API đăng ký/hủy không cho tái đăng ký sau hủy. Lịch sử check-in giới hạn tối đa 100 dòng, chưa có cursor. Danh sách Events của organizer phân trang/filter/sort trên server; danh sách tổng quan dashboard và users chưa phân trang. Counter trong dữ liệu seed mới khớp registration thật; database seed cũ không tự được sửa lại.

## Triển khai local và mở rộng

Để demo: PostgreSQL Compose, migration, seed, Uvicorn một worker và Vite. Để phục vụ HTTPS: đặt JWT_SECRET riêng ít nhất 32 byte, COOKIE_SECURE=true, ALLOW_LOCALHOST_ORIGINS=false và FRONTEND_ORIGIN chính xác; dùng reverse proxy hỗ trợ WebSocket và host fallback cho SPA. Refresh cookie SameSite=lax cần frontend/API cùng site.

Cần bổ sung theo quy mô thực tế: quản lý secrets/DB credentials, TLS, backup, rate limiting, quan sát lỗi, cleanup refresh tokens và triển khai build frontend tĩnh. /health chỉ là liveness; readiness cần kiểm tra DB riêng. Những hạng mục này ngoài phạm vi chốt MVP hiện tại.
