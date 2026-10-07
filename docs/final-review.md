# Kết quả chốt source Evently

Ngày kiểm chứng: 07/10/2026. Phạm vi: backend FastAPI, frontend web MVP, migration, tests, cấu hình chạy và tài liệu kỹ thuật. Báo cáo Word do nhóm viết riêng, không được sửa trong đợt này. Source được chia thành các commit chức năng. PR frontend bao gồm ba nhóm foundation/attendee/operations để đảm bảo test/build đầy đủ; main do người dùng merge trên web.

## Kết luận theo tầng công nghệ

| Tầng | Source và minh chứng | Kết luận |
| --- | --- | --- |
| 1 | Pydantic v2; Depends; sync/async I/O; OAuth2 password flow/JWT; RBAC và quyền tài nguyên; OpenAPI/DTO; middleware; exception handling; BackgroundTasks; lifespan; TestClient | Đủ kỹ thuật để chốt MVP FastAPI và trình bày bằng luồng thực tế |
| 2 | Env example; dependency lock; migration/seed; README chạy/demo; tests API, PostgreSQL concurrency và SMTP; CI có PostgreSQL service | Đã hoàn tất phần source/local checks. CI remote cần được xác nhận trên commit cuối; minh chứng Git dùng lịch sử commit thực tế |
| 3 (tự chọn) | Realtime WebSocket với auth ticket, room, reconnect/REST fallback; composite index, offset/cursor và benchmark PostgreSQL rollback | Hai lựa chọn có triển khai và bằng chứng; không khai thêm cache, job queue, streaming hay microservices |

Ứng dụng minh họa ba vai trò ORGANIZER, STAFF và ATTENDEE. ORGANIZER đóng vai trò quản lý và chỉ sửa sự kiện mình sở hữu; không có ADMIN độc lập. Không tuyên bố tận dụng mọi tính năng FastAPI hoặc triển khai production.

## Backend hoàn tất

- OAuth2PasswordBearer và POST /auth/token dùng form grant_type=password, username=email; Swagger Authorize hoạt động theo flow này. POST /auth/login JSON được giữ cho frontend. Quyền lấy từ DB, client gửi scopes không nâng role.
- Event CRUD, lọc trạng thái, offset/cursor; danh sách organizer có phân trang/filter/sort trên SQL, total/has_more cho client.
- Booking kiểm tra sức chứa bằng FOR UPDATE trên PostgreSQL; registration, vé và counter cùng transaction. Refresh rotation đồng thời chỉ có một request thành công.
- Pydantic chặn capacity âm, end trước start, null/chuỗi quá dài; lỗi 422 có details. Lỗi xác thực giữ WWW-Authenticate.
- BackgroundTasks gửi xác nhận email kèm PNG QR qua SMTP sau commit. Webhook là lựa chọn thay thế; thiếu transport thì simulated. Mailpit profile mail cho demo hộp thư local, không gửi ra ngoài.
- PATCH capacity broadcast occupancy sau commit; DTO rõ ràng cho occupancy, ws-ticket, organizer dashboard, assignment và health.
- Quyền đọc vé/registration, check-in đúng event và chỉ dùng một lần; hủy vé/trạng thái giữ invariant. Xóa nháp xử lý FK assignment.
- Lifespan quét lifecycle/catch-up và await shutdown. WS handshake chuẩn bị dữ liệu bằng dependency sync, không giữ DB connection suốt kết nối.
- Comment/docstring giải thích transaction, locking, async, thời gian và transport. Không đổi mọi router thành async khi đang dùng SQLAlchemy sync.

## Frontend hoàn tất

Web MVP giữ Explore, My tickets, Check-in, Overview, Events, Create event, Manage và Dashboard. Không có ảnh banner/avatar, camera QR hoặc phần triển khai mobile. Menu organizer ổn định, Create event dùng cùng kích thước với các mục còn lại; form được căn giữa, actions và summary gọn.

Status/date dùng chung; lifecycle stepper và nhãn Check-in/Dashboard rõ ràng. Modal giữ lỗi để retry, Esc đóng và trả focus. Hủy vé áp dụng response thành công ngay. Banner scan tự ẩn sau 5 giây, Last scan giữ kết quả cuối; Recent check-ins lấy server, You đánh dấu lượt thành công trong phiên. Events dùng phân trang server 20 dòng.

Đã thử đăng nhập theo vai trò, tạo nháp, đăng ký/xem đúng QR, scan hợp lệ và scan đã dùng; kiểm tra bố cục desktop 1024/1280/1440, không có tràn ngang. Không dùng kiểm thử desktop để khẳng định đã nghiệm thu mobile.

## Kiểm chứng cuối

| Kiểm tra | Kết quả |
| --- | --- |
| Backend, dependency cài mới từ requirements.lock | 80 tests passed, 0 skipped, coverage 94% |
| PostgreSQL concurrency trong toàn bộ suite | Capacity=1/5 attendee: một 201, bốn 409; refresh song song: một 200, một 401 |
| SMTP integration | Inbox localhost nhận email xác nhận với attachment PNG QR; transport lỗi không mất vé, notify thủ công trả 502 |
| Mailpit Compose thực tế | Hộp thư local nhận email vé từ notifier, có một attachment QR |
| Migration/seed PostgreSQL riêng | Head 0002_event_status_start_index; seed thành công; alembic check không drift |
| Frontend cài sạch bằng npm ci | 23 tests passed; lint, audit:copy và production build thành công |
| Dependency audit frontend | npm audit kiểm tra lại: 0 vulnerabilities |
| CI | Workflow đã cấu hình PG service/lock install; trigger khi push; trạng thái thực tế xem GitHub Actions, không suy ra từ kết quả local |

PostgreSQL kiểm chứng dùng database evently_final_test riêng trên dịch vụ local cổng 5433. Không reset database evently hoặc dừng server của người dùng. Tests API dùng SQLite riêng, test PostgreSQL dùng UUID và dọn theo FK; lifecycle session factory được override để tránh chạm dữ liệu demo.

Benchmark PostgreSQL 16 local: thêm 3000 events, tổng 3003 Published, limit 20, 20 lần đo. EXPLAIN execution 1.113 ms trước index và 0.154 ms sau index; deep offset trung bình 1.922 ms, cursor 0.961 ms. Dữ liệu/index tạm rollback. Đây là số liệu query local, chưa phải load test thông lượng hoặc số kết nối WS tối đa.

## Tài liệu và dọn source

README gốc có cài đặt, tài khoản, thao tác từng vai trò, Swagger OAuth2, Mailpit/SMTP, kiểm thử và xử lý lỗi. README backend/frontend và tài liệu auth/realtime/testing/performance/limits được cập nhật theo source cuối. Review yêu cầu và FE trước đó được đánh dấu lịch sử, kết quả hiện hành là tài liệu này.

Đã bỏ mock client, component/hook không dùng, tài liệu phase/roadmap cũ, cấu hình Tailwind không dùng, script cleanup DB hardcode và file .coverage bị theo dõi. Giữ source, migration, tests, tài liệu kỹ thuật, ERD, ảnh minh chứng, báo cáo Word và giấy phép font. .venv, node_modules, dist/cache là dữ liệu chạy/build được ignore, không phải nội dung source cần nộp.

Checkout integration là bản chạy/test đầy đủ. Các branch được xếp theo phụ thuộc, có commit chức năng thật. Xem [thứ tự merge và danh sách file](merge-order.md). tools/sync_review_worktrees.py chỉ dùng trước khi đóng commit và bị chặn khi manifest đã đánh dấu committed.

## Giới hạn được chấp nhận trong MVP

Một worker cho WS rooms/tickets trong RAM; BackgroundTasks không có queue/retry bền vững; simulated không gửi email thật. Giờ sự kiện theo timezone máy chủ, lifecycle quét mỗi 60 giây. Catalog còn công khai metadata nháp; check-in history tối đa 100 dòng; dashboard tổng quan/users chưa phân trang. Không có thanh toán hoặc camera scanner. Xem [giới hạn kỹ thuật](gioi-han-ky-thuat.md).

Source có thể chốt cho demo theo phạm vi trên. Việc nộp cần commit/version thực tế và CI tương ứng; báo cáo, slide, lab và nhật ký được nhóm hoàn thiện thủ công, không phải phần source còn thiếu.

## Dataset mở rộng ngày 07/10/2026

Seed idempotent bổ sung 2 organizer, 5 staff, 100 attendee, 10 event mở và 5 completed, 278 registration/ticket, 75 check-in và 30 assignment. Tài khoản đăng nhập bằng alias đánh số hoặc email; không reset DB cũ. Đã kiểm chứng chạy lại không thêm bản ghi hoặc phục hồi trạng thái người dùng đã đổi. Tổng database hiện tại lớn hơn dataset do giữ các bản ghi cũ.

Trước push: source-map-js trong lockfile được nâng từ 1.2.1 lên 1.2.2 bằng commit riêng; npm audit sau cập nhật không còn cảnh báo.

## Sửa cách đóng PR frontend sau lỗi CI

CI của foundation tại 925059d lỗi npm test vì chưa có file tests và thiếu các trang router import. Nguyên nhân là ranh giới branch chưa khép kín phụ thuộc, không phải bản vá source-map-js. PR #10 được cập nhật bằng fast-forward tới b15d77f, chứa đủ 20 commit frontend. Không tắt/skip kiểm thử. Backend PR #9 đã merge; tiếp theo chỉ cần PR #10 và documentation.
