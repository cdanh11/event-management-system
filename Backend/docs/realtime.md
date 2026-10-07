# WebSocket, async và task nền

## Occupancy

GET /events/{id}/occupancy là REST snapshot dành cho ORGANIZER. POST /ws/ticket dành cho mọi user đã login; WS /ws/events/{id}?ticket=... stream occupancy công khai theo room event.

Ticket ngẫu nhiên sống 30 giây, dùng một lần. Mint/redeem có lock giữa các worker thread; ticket không dùng được dọn khi cấp ticket mới. JWT không đưa vào query string. Mã đóng 4401: ticket sai/hết hạn/đã dùng; 4404: event không tồn tại.

Payload gồm type (snapshot/occupancy), event_id, capacity, registered_count, remaining, status. Snapshot đầu để client vẽ ngay. Sau register/cancel/PATCH capacity/transition và lifecycle, server broadcast sau commit. registered_count đếm đăng ký, không đếm check-in; Check-in history lấy REST và polling.

Handshake DB nằm trong dependency sync, trả dict thuần và rollback transaction đọc để không giữ connection DB trong suốt WS. Vòng lặp async chỉ chờ receive/send, disconnect dọn room. Server nhận heartbeat nhưng không echo pong.

## Sync và async

Endpoint SQLAlchemy Session sync dùng def, được FastAPI chạy trong threadpool. Notify có dependency sync chuẩn bị quyền/dữ liệu, handler async await httpx.AsyncClient hoặc asyncio.to_thread cho SMTP. Không dùng DB sync trực tiếp trong vòng lặp event loop. Lifecycle dùng asyncio.to_thread để chạy sweep DB.

httpx client dùng chung để tái sử dụng kết nối, đóng trong lifespan. SMTP_HOST có giá trị thì gửi email qua SMTP trong thread, vé có PNG QR đính kèm. Nếu không có SMTP, NOTIFY_WEBHOOK_URL gửi JSON bằng HTTP async; không có cả hai thì mô phỏng I/O. Notify thủ công lỗi transport trả 502; gửi nền ghi log lỗi.

## BackgroundTasks và lifespan

Register commit registration/ticket/counter, sau đó lên lịch broadcast và gửi vé bằng dữ liệu thuần. Transition COMPLETED/CANCELLED lên lịch notify. BackgroundTasks không phải queue, không retry hay đảm bảo giao thông báo khi tiến trình dừng.

Lifespan quét lifecycle lúc startup rồi chạy task mỗi 60 giây. Shutdown cancel và await task, đóng notifier/engine. Sweep khóa Event, catch-up sau downtime và broadcast trạng thái cuối.

## Phạm vi chạy

Một process/worker. WS rooms/tickets trong RAM; nhiều worker cần shared store/pub-sub. Catalog hiện công khai occupancy và cả metadata nháp; không truyền tên/mã vé qua WS. Chi tiết [giới hạn triển khai](../../docs/gioi-han-ky-thuat.md).
