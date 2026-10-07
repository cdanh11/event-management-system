# Evently Web MVP

Client React/TypeScript/Vite dùng dữ liệu FastAPI thật. Mục tiêu là demo công nghệ và thao tác nghiệp vụ trên web; giao diện giữ các màn hình cần thiết, không có ảnh banner, preview, biểu đồ hoặc hộp thông báo phụ.

## Chạy

Khởi động backend theo [README gốc](../readme.md), sau đó chạy từ Frontend:

```powershell
npm ci
Copy-Item .env.example .env
npm run dev -- --port 5173
```

Mở http://localhost:5173. VITE_API_BASE_URL mặc định http://localhost:8000. Dùng cùng hostname cho API và frontend; đổi env cần khởi động lại Vite.

## Sử dụng theo vai trò

| Vai trò | Màn hình | Cách dùng |
| --- | --- | --- |
| ATTENDEE | Explore, My tickets | Tìm event, Register, xem QR/mã vé; Cancel registration khi Published |
| STAFF | Check-in | Chọn event được gán, nhập/quét mã và Enter; xem kết quả/lịch sử |
| ORGANIZER | Overview, Events, Create event, Manage, Dashboard | Tạo và Publish, gán staff, dời lịch, mở check-in, kết thúc, Notify |

Trong Manage, Overview chứa thông tin và hành động lifecycle; Staff gán/tạo nhân viên; Schedule sửa lịch khi Draft/Published; Check-in nhận vé cho organizer sở hữu.

Form Create event kiểm tra thông tin bắt buộc, thời gian tương lai, end sau start và capacity nguyên dương. Create draft tạo nháp; Publish mới mở đăng ký. Begin preparation đóng đăng ký, Start event mở check-in, Complete event kết thúc.

Vé QR chứa mã thật từ API. Vé đã hủy hoặc đã check-in không dùng lại được. Sau khi hủy không thể đăng ký lại cùng sự kiện; dùng attendee khác để demo tiếp. Màn hình Check-in gửi cả mã vé và ID event đang chọn để backend kiểm tra trước khi nhận vé.

Dashboard hiển thị Registered/Left/Fill và thay đổi gần nhất trong phiên. WebSocket cập nhật đăng ký/hủy, capacity và trạng thái; REST dự phòng khi mất kết nối. Check-in không thay đổi số đăng ký. Notify dùng SMTP, webhook hoặc simulated theo cấu hình backend. SMTP có email xác nhận kèm PNG QR; xem hướng dẫn Mailpit tại README gốc.

## Kiểm tra

```powershell
npm run lint
npm test
npm run audit:copy
npm run build
```

Test gồm thời gian, refresh token, phân trang, reconnect và lỗi thao tác. Không thay thế kiểm thử toàn bộ giao diện hoặc PostgreSQL.

Banner scan tự ẩn sau 5 giây; Last scan vẫn giữ kết quả cuối. Recent check-ins chỉ lấy bản ghi thành công từ server; nhãn You đánh dấu lượt nhận vé thành công trong phiên hiện tại. Explore có View ticket trực tiếp bên cạnh Registered.

## Tài liệu

- [Kiến trúc](docs/architecture.md)
- [Đăng nhập và phiên](docs/authentication.md)
- [Realtime](docs/realtime-dashboard.md)
- [Demo 5–7 phút](docs/demo-scenarios.md)

- [Checklist nghiệm thu FE web](../docs/frontend-mvp-review.md)

Events của organizer dùng `/organizer/events`: phân trang 20 dòng, tìm tên/địa điểm/category, lọc trạng thái và sắp xếp trên server. Chuyển bộ lọc đưa về trang đầu; tổng kết quả lấy từ API.
