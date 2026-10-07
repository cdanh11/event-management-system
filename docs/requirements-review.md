# Đối chiếu Evently với yêu cầu môn học và góp ý của giảng viên

> Review trước đợt đóng backend cuối. Các mục OAuth2, email SMTP/QR, DTO, PATCH capacity broadcast và phân trang organizer đã được xử lý ngày 07/10/2026; kết quả hiện hành ở [final-review.md](final-review.md). Các nhận định còn thiếu của bản review này là lịch sử, không phải trạng thái source cuối. Báo cáo Word không thuộc đợt sửa source này.

Ngày rà soát: 07/10/2026. Đối tượng: code đang làm việc, README/tài liệu Markdown, `Bao_cao_Evently_DRAFT.docx`, hai PDF và hai ảnh do nhóm cung cấp. Đây là kết quả review, chưa phải báo cáo nộp cuối kỳ. Không sửa chức năng, không sửa Word, không commit/push trong đợt đối chiếu này.

## 1. Kết luận và giới hạn kiểm chứng

**Code đã vượt mức CRUD cơ bản và có đủ ba nhóm lõi FastAPI của danh mục. Tuy nhiên, chưa thể chốt toàn bộ hồ sơ đồ án theo yêu cầu môn học.** Điểm thiếu lớn nhất là chiều sâu và tính nhất quán của báo cáo, minh chứng thực nghiệm, hands-on lab và hồ sơ quá trình của nhóm. Có thêm một lỗi đồng bộ realtime được tái hiện trong lần review này.

Kết luận trước trong `final-review.md` chỉ xác nhận MVP local một worker trong phạm vi triển khai đã được yêu cầu lúc đó. Sau khi có đủ tài liệu môn học, phải bổ sung các điều kiện nghiệm thu học thuật dưới đây; không đồng nhất “code chạy được” với “hồ sơ đủ để nộp”.

- Đã đọc nội dung hai PDF, kiểm tra trực quan các trang quan trọng của danh mục/bố cục; đối chiếu nội dung Word, source, test và Git.
- Đã chạy thêm TestClient trên SQLite in-memory riêng: 422 cho capacity âm và end trước start; schema OpenAPI; cập nhật capacity và số lần broadcast. Không tác động database demo.
- Kết quả 70 passed/2 skipped, 2 test PostgreSQL, coverage 89%, frontend 21 tests và benchmark bên dưới là kiểm chứng của đợt rà soát triển khai cùng ngày, ghi trong `final-review.md`; không gọi chúng là một lần chạy lại toàn bộ trong đợt review yêu cầu này.
- Chưa kiểm tra dàn trang PDF xuất từ Word, chưa quan sát mọi thành viên thực hành, chưa có kết quả CI của commit chứa các thay đổi chưa commit, chưa thực hiện HTTP load test hoặc thử hàng nghìn WebSocket.
- “Chưa tìm thấy” hồ sơ trong repository không có nghĩa nhóm không có hồ sơ đó ở nơi khác. Nhóm cần cung cấp/đưa vào gói nộp đúng phiên bản thật.

## 2. Hiểu đúng nguồn yêu cầu

| Nguồn | Vai trò trong review |
| --- | --- |
| `01_Danh_muc_cong_nghe_Goi_y.pdf`, trang 12 | FastAPI: Pydantic model, dependency system, endpoint async đúng chỗ là ba mục lõi; sáu mục chọn thêm được liệt kê |
| PDF danh mục, trang 17–18, 20 | Các hướng Tầng 3 tự chọn và chuẩn kỹ nghệ Tầng 2; không bắt làm toàn bộ hướng nâng cao |
| `03_cau_truc_bao_cao.pdf`, trang 4–14 | Bố cục, chiều sâu thực nghiệm, bảng phủ, AI disclosure, lab và hồ sơ nộp |
| Hai ảnh giảng viên gửi | Nhấn mạnh lựa chọn kỹ thuật có lý do, minh chứng, bảng phủ khớp code và khả năng giải thích/sửa tại chỗ |
| Yêu cầu trực tiếp của nhóm | Evently, web MVP đơn giản; JWT/phân quyền, event CRUD, pagination/status, booking/capacity, 422, background notification và dashboard realtime |
| Góp ý đề tài quản lý học tập của nhóm khác | Ví dụ về việc phải làm nổi bật FastAPI; không phải chỉ thị đổi Evently thành ứng dụng quản lý học tập |

Tỷ trọng 80% công nghệ–20% ứng dụng là định hướng nhóm cung cấp, không phải công thức chấm điểm tự suy ra từ PDF. Không cần thêm ảnh/mobile, thanh toán, microservices, Redis hay queue chỉ để tăng số thư viện. Các chỗ chừa thông tin nhóm phải được điền bằng dữ liệu thật; không tạo lịch sử tiến độ, đóng góp, trải nghiệm so sánh hoặc lỗi AI giả.

## 3. Các API bắt buộc và ba điểm thể hiện FastAPI

| Yêu cầu | Code hiện tại / minh chứng | Đánh giá |
| --- | --- | --- |
| JWT | `security.py`, `deps.py`, `routers/auth.py`: JWT, hash Argon2, refresh rotation, dependency xác thực | Có; cần mô tả chính xác HTTPBearer |
| Organizer tạo/sửa/xóa; user xem/đăng ký | `require`, ownership và `access.py`; ATTENDEE/ORGANIZER/STAFF | Có; ORGANIZER là vai trò quản trị sự kiện, không có role ADMIN riêng |
| Event CRUD | POST/GET/PATCH/DELETE; title, description, start/end, location, capacity; trạng thái tạo DRAFT rồi transition | Có; xóa cứng chỉ DRAFT, các trạng thái khác hủy theo máy trạng thái |
| Pagination/status | GET `/events`: limit/offset hoặc cursor; status enum; q tìm title | Có; nhãn ba trạng thái nghiệp vụ chưa khớp hoàn toàn diễn giải trong Word |
| Booking | POST `/events/{id}/register` tạo registration, ticket và counter cùng transaction | Có |
| Capacity | Khóa Event trên PostgreSQL, kiểm tra trước commit; 409 EVENT_FULL | Có; đã kiểm tra capacity=1, năm request, chỉ một 201 |
| Pydantic 422 | Field capacity `gt=0`, model_validator end > start | Đã tái hiện cả hai trường hợp trả 422 trong review này |
| BackgroundTasks | Đăng ký task broadcast và gửi thông báo vé sau commit | Có cơ chế; chưa có minh chứng email thực nhận trong cấu hình mặc định |
| WebSocket Live | Snapshot, room theo event, broadcast đăng ký/hủy/transition, ticket handshake, reconnect và REST fallback | Có; một worker; thiếu broadcast khi PATCH capacity |

**JWT và OAuth2 không đồng nghĩa.** OpenAPI thực tế hiện khai báo `type=http`, `scheme=bearer`, `bearerFormat=JWT`; login nhận JSON. Không dùng `OAuth2PasswordBearer`, token endpoint form hoặc OAuth2 scopes. JWT đáp ứng yêu cầu xác thực đã nêu; nếu giảng viên muốn cụ thể OAuth2 password flow, đây là khoảng cách cần làm rõ khi trao đổi. Không ghi “đã triển khai OAuth2” với code hiện tại. Tham chiếu: [FastAPI security](https://fastapi.tiangolo.com/tutorial/security/first-steps/).

**Thông báo chưa phải email production.** Nếu `NOTIFY_WEBHOOK_URL` trống, notifier chỉ `await asyncio.sleep(0.05)` và ghi log. Khi có URL, code POST payload chứa email/ticket_code/qr_value; việc nhận payload không tự chứng minh dịch vụ đã gửi email hoặc đính kèm ảnh QR. QR hiện được frontend dựng từ mã vé. Nên có webhook test receiver và bằng chứng response đến trước task hoàn tất; nếu tuyên bố gửi email thực, phải có bằng chứng dịch vụ gửi và người nhận nhận được. Không cần mở rộng sang hệ thống mail phức tạp chỉ để demo cơ chế nền.

**Không cam kết “vài mili-giây” khi chưa đo.** Response đã tách khỏi task thông báo nhưng vẫn phải chờ xác thực, khóa DB, tạo vé và commit. Thời gian TestClient trả về có thể bao gồm việc chạy task nền, không dùng trực tiếp để chứng minh thời gian trình duyệt nhận response. Cần đo qua HTTP thật, log mốc response/task và ghi môi trường.

## 4. Phát hiện code cần xử lý hoặc diễn giải

### 4.1. Cần sửa trước khi chốt: PATCH capacity không cập nhật Live

Vị trí: `Backend/app/routers/events.py:197–231`; `Frontend/src/realtime/useOccupancy.ts:63`; `Frontend/src/pages/organizer/Live.tsx:38`.

Tái hiện qua API trên DB test riêng: tạo event capacity=10, publish, PATCH capacity=15 → 200; REST occupancy trả capacity/remaining=15; số lần gọi `manager.broadcast_occupancy` cho PATCH = **0**. Đăng ký/hủy/transition có broadcast, PATCH không có. Hook chỉ polling khi socket không open, còn Live ưu tiên snapshot capacity cũ. Vì vậy client đã có snapshot và đang kết nối có thể giữ số còn lại cũ cho tới một frame khác/reconnect.

Hướng sửa nhỏ: sau commit PATCH, lên lịch broadcast snapshot mới; thêm test với client đã subscribe, thay capacity và xác nhận frame mới. Không cần đổi kiến trúc hay thêm polling liên tục khi WS đang tốt. Đây là phát hiện mới của review; chưa tự sửa trong đợt chỉ đối chiếu yêu cầu này.

### 4.2. Hợp đồng OpenAPI chưa mô tả đầy đủ mọi response

Schema thực tế: **25 đường dẫn HTTP, 29 thao tác HTTP**, gồm health; nếu loại `/health`, còn 28 thao tác nghiệp vụ. WebSocket không nằm trong số này. Không dùng con số “27 endpoint REST” của Word nữa.

Bốn success response đang có schema JSON rỗng: GET `/events/{id}/occupancy`, POST `/ws/ticket`, GET `/organizer/dashboard`, GET `/health`. Có response_model ở nhiều API chính, nhưng chưa đủ để tuyên bố mọi response đều được Pydantic kiểm tra và có contract chặt. Error responses cũng chưa khai báo nhất quán cho mọi route. Nên bổ sung DTO cho ba API nghiệp vụ trên và audit error contract; `/health` là ưu tiên thấp hơn.

### 4.3. Trạng thái cần một bảng nghĩa thống nhất

Code có DRAFT, PUBLISHED, ONGOING, STARTED, COMPLETED, CANCELLED. ONGOING hiện là chuẩn bị/đóng đăng ký; STARTED là mở check-in, tự động trước start 15 phút, nên cũng không đồng nghĩa tuyệt đối “đã tới giờ diễn ra”. Frontend tab happening gom ONGOING + STARTED; past chỉ COMPLETED. Word viết happening=ONGOING, ended=COMPLETED/CANCELLED, sơ đồ bỏ STARTED: không đúng hợp đồng hiện tại.

Chốt một định nghĩa rồi mô tả đúng ở API, giao diện và báo cáo. Có thể giữ sáu trạng thái kỹ thuật và giải thích nhóm nhãn hiển thị; nếu cần ba nhóm theo thời gian thực, phải đặc tả rõ cách kết hợp start/end và status. CANCELLED phải được phân biệt với đã tổ chức xong. Không cần tạo thêm miền nghiệp vụ.

### 4.4. Giới hạn vận hành cần nói rõ

- WS rooms và ticket đều trong RAM: chạy nhiều worker có thể redeem ticket ở process khác hoặc broadcast không đến client ở process khác. Demo giữ một worker; Redis pub/sub và kho ticket dùng chung là hướng mở rộng có lý do.
- BackgroundTasks trong process không có durability, retry/backoff, dead-letter hoặc outbox. Không coi đây là queue Tầng 3. [FastAPI BackgroundTasks](https://fastapi.tiangolo.com/tutorial/background-tasks/).
- Broadcast gửi lần lượt tới client, chưa có timeout riêng/version frame/load test; không tuyên bố đã giải C10k hoặc bảo đảm thứ tự dữ liệu khi nhiều mutation đồng thời.
- Tự động COMPLETED trong lifecycle chỉ đổi trạng thái và broadcast; không gửi notification như transition thủ công. Nếu Word nói mọi đường hoàn thành đều gửi email thì phải sửa diễn giải hoặc bổ sung hành vi.
- Thời gian lưu naive theo timezone máy chủ; chưa có chuẩn UTC xuyên môi trường. Demo phải đặt cùng timezone và giải thích đánh đổi.
- Catalog public còn trả metadata DRAFT; không phải rò rỉ vé/email, nhưng cần xác định nháp có thật sự được công khai hay phải lọc cho người chưa đăng nhập.
- Cursor neo ID rồi đọc start_time hiện tại; xóa/dời lịch anchor giữa hai lần tải có thể ảnh hưởng pagination. Chưa có snapshot consistency; ghi rõ giới hạn thay vì gọi pagination tuyệt đối ổn định.
- `/health` là liveness, chưa kiểm tra DB. “App sống” không có nghĩa “DB sẵn sàng”.
- Requirements backend dùng khoảng phiên bản rộng. Lần review chạy Python 3.14.3, FastAPI 0.141.1, Starlette 1.6.0, Pydantic 2.13.5, SQLAlchemy 2.0.52, httpx 0.28.1, pytest 9.1.1; CI khai báo Python 3.12. Ghi version được kiểm chứng hoặc có lock/constraints để dễ tái lập. TestClient hiện phát cảnh báo deprecated về httpx; kiểm tra tương thích theo dependency đang chọn, không đổi thư viện mù quáng.
- Comment `/health` nói async không có await là “vô ích” là quá tuyệt đối. Cả def và async def đều hợp lệ cho handler nhẹ; vấn đề là không gọi I/O blocking trực tiếp trên event loop. [FastAPI async](https://fastapi.tiangolo.com/async/).

Các mục giới hạn không tự động trở thành yêu cầu phải xây production. Mục nào không chọn cần nói đúng lý do và hệ quả.

## 5. Tầng 1, Tầng 2, Tầng 3

### Tầng 1: có kỹ thuật, báo cáo cần thêm cơ chế và thực nghiệm

| Mục danh mục FastAPI | Bằng chứng source | Nội dung nhóm cần giải thích |
| --- | --- | --- |
| Lõi: Pydantic | `schemas.py`, handler 422, tests validation | Type parsing/coercion, Field vs model_validator, request vs response validation, 422 vs lỗi nghiệp vụ cần DB |
| Lõi: dependency | `db.py`, `deps.py`, `access.py`, `_notification_target`, fixture override | Dependency graph, resource lifecycle, auth vs role vs ownership, override để cô lập test |
| Lõi: async đúng chỗ | async notifier/httpx, WS, sync DB dependency, lifespan to_thread | ASGI/event loop, await nhường khi chờ I/O, threadpool cho sync handler/dependency, helper sync gọi trực tiếp không tự được offload |
| Chọn thêm: OpenAPI | `/openapi.json`, security schema, Pydantic DTO | Sinh contract từ type/dependency; giới hạn schema WS và các DTO còn thiếu |
| Chọn thêm: exception | `main.py`, `errors.py` | Handler tập trung, serialization lỗi validator, không biến lỗi DB thành 401 |
| Chọn thêm: background | registration/transition, notifier | Sau response khác với await trong handler; thất bại sau commit không rollback booking |
| Chọn thêm: middleware | timing + CORS | Thứ tự xử lý, header expose, timing này chưa là latency end-to-end/trace |
| Chọn thêm: response model | EventOut/RegisterOut/TicketOut... | Validation/filter/serialize đầu ra; không giả định tất cả API đã có |
| Chọn thêm: TestClient | tests + dependency override | Cô lập DB, TestClient lifespan, mock network, giới hạn SQLite/PG |

Danh mục trang 12 liệt kê **sáu** mục chọn thêm. Lifespan là minh chứng bổ sung có ích, nhưng không nên ghi “7 mục chọn thêm theo Phần F” như Word hiện tại. POST `/ws/ticket` là handler sync, không đưa vào danh sách endpoint async. Word nhắc `RegisterIn` trong bảng lõi nhưng schema hiện không có model này.

### Tầng 2: phần lớn nền tảng có, minh chứng quá trình chưa đủ

| Mục | Trạng thái / việc còn thiếu |
| --- | --- |
| Git/nhánh/PR/review | Có lịch sử và các worktree; diff hiện chưa commit. Nhánh riêng không tự chứng minh cross-review/merge conflict; phải trỏ PR và nhận xét thật |
| Môi trường tái lập | README, compose DB, migration, seed có. Compose chỉ chạy PostgreSQL/pgAdmin, không phải cả hệ thống một lệnh |
| Secrets | Env example và ignore có; phân biệt credentials demo với secret production; không đưa `.env` thật vào gói nộp |
| Testing | 70 passed/2 PG skip trong suite SQLite; PG riêng 2 passed; coverage 89%; frontend 21 tests. Chưa có browser E2E toàn luồng |
| CI | Có workflow test/lint/build. Chưa thể gọi bản diff chưa commit là “CI xanh” của phiên bản nộp |
| Bảo mật | JWT, hash, ownership, cookie, CORS, ORM bind có; không coi đó là chứng nhận hoàn tất OWASP/production |
| Tài liệu | README hiện hữu ích, API tự sinh; Word còn cũ; lab riêng chưa tìm thấy |
| Dùng AI/nguồn chính hãng | Cần khai báo công cụ/file thật, prompt và cách phát hiện hai lỗi AI thật; cần trích tài liệu chính hãng rõ |

### Tầng 3: chọn hai hướng hiện có, làm sâu minh chứng

1. **Tối ưu truy vấn:** composite index, cursor và EXPLAIN ANALYZE có code/measurement. Phép đo local PostgreSQL 16, thêm 3000 events, 3003 PUBLISHED tổng, limit 20, 20 lần: execution 2.551 → 0.197 ms; offset trung bình 3.457 ms, cursor 1.666 ms. Script rollback dữ liệu/index cuối phép đo. Cần lưu raw plan, thông số máy/version, query, seed, ngày/commit và cách đo vào hồ sơ; dữ liệu này minh họa DB optimization, không phải bằng chứng FastAPI nhanh hơn framework khác.
2. **Realtime phía server:** room, snapshot/broadcast, ticket một lần 30s, disconnect cleanup, frontend reconnect lấy ticket mới, fallback/resync có. Cần minh chứng hai client, frame/log, disconnect/reconnect, ticket hết hạn/đã dùng và dữ liệu không bị cập nhật chéo room; test tải/giới hạn nếu tuyên bố khả năng tải. Không bắt phải triển khai Redis cho demo một worker.

Row lock + unique constraint và test capacity là minh chứng transaction/concurrency của PostgreSQL/SQLAlchemy được tích hợp qua FastAPI; tách khỏi dòng WS để không lẫn hai cơ chế.

Không tự ghi đã đạt: Redis cache, queue thật, advanced full-text search, tích hợp webhook có chữ ký/retry, streaming dữ liệu lớn, observability đầy đủ hoặc microservices. ILIKE, BackgroundTasks, timing log và POST webhook đơn giản chưa chứng minh các kỹ thuật nâng cao tương ứng. Tầng 3 không có số mục tối thiểu chung; tránh over-engineering.

## 6. Bố cục báo cáo: đúng vị trí, còn thiếu chiều sâu

| Phần/chương | Hiện trạng | Cần sửa/bổ sung |
| --- | --- | --- |
| Tên đề tài, mở đầu | Gọi đúng FastAPI là backend/API framework; domain Evently hợp | Phạm vi mở đầu nói một T3 nhưng phần sau có hai; đồng bộ. Thông tin cá nhân và kế hoạch lấy từ nhóm |
| C1: tổng quan/phản biện | Có ecosystem và so sánh ngắn Express/NestJS | Thử/đo 1–2 đối thủ trực tiếp trên cùng bài toán nhỏ; hiện chưa thấy minh chứng trải nghiệm. Hai tình huống không phù hợp phải có lý do; in-memory WS là giới hạn thiết kế hiện tại, không phải FastAPI không hỗ trợ hệ phân tán |
| C2: vị thế/ứng dụng | Vài câu và số backend ~37% | 2–3 bối cảnh ứng dụng, 1–2 nguồn đáng tin có ngày. Số backend chung không chứng minh riêng FastAPI; không cần bảng lương |
| C3: môi trường/kiến trúc | Đúng chương | Cài đặt tái lập, health/Swagger, version và sơ đồ modular monolith; không chuyển use case vào đây. FastAPI không bắt buộc tổ chức tầng/microservices như repo |
| C4: ba mục lõi | Có bảng nhưng nội dung ngắn | Mỗi mục thành tiểu mục: khái niệm → cơ chế → code/thực nghiệm → kết quả → giải thích ứng dụng. Không dùng benchmark SQL làm bằng chứng await hiệu quả |
| C5+: chọn thêm | Có các chủ đề tốt | Với từng kỹ thuật trả lời lý do chọn, cơ chế, đã thử gì, kết quả, vị trí dùng. Không cần bịa chương 6–10 để đủ số |
| C11: phân tích/thiết kế | Đúng vị trí, có user story/ERD/API | Bổ sung use case và nhánh lỗi; bảng quyền; trạng thái đầy đủ; API table sinh từ schema mới |
| C12: tích hợp/kết quả | Có bảng phủ | Phân biệt source thực hiện, thí nghiệm độc lập và hướng tương lai; số test/benchmark mới; minh chứng API/log; frozen commit đúng phiên bản |
| C13: đánh giá/AI | Có lỗi và disclosure | Prompt/AI response thật của ít nhất hai lỗi, cách phát hiện và sửa; công cụ Codex đang dùng chưa được phản ánh; cập nhật timezone và migration fixed snapshot |
| C14: hướng phát triển | Có Redis/SMTP... | Fresh WS ticket khi reconnect đã làm, không để là tính năng tương lai; tách giới hạn còn lại khỏi việc đã triển khai |
| Tài liệu tham khảo/phụ lục | Có danh sách tên tài liệu và placeholders | URL/mục/ngày truy cập; nhật ký chi tiết khớp Git và người thực hiện; Insights/commit/PR thật |
| Hands-on lab | Chỉ ghi là bước tiếp theo | Tài liệu riêng bắt buộc 30–45 phút, starter, bài tập/đáp án/lỗi thường gặp |

**Use case đặt ở C11, không phải C3.** PDF yêu cầu chức năng dạng user story, nhóm muốn use case thì triển khai tại C11 để thể hiện rõ. Tối thiểu sáu luồng: login/phân quyền; organizer tạo/publish; xem/lọc/phân trang; đăng ký/đầy/trùng; hủy/đã check-in; staff check-in đúng event/nhầm/trùng; thêm observer Live như minh chứng kỹ thuật. Mỗi luồng có actor, điều kiện trước, luồng chính, luồng lỗi và hậu điều kiện. Không cần kéo dài thành phân tích nghiệp vụ hàng chục trang.

Sơ đồ lifecycle cần phản ánh các cạnh thực tế: DRAFT → PUBLISHED/CANCELLED; PUBLISHED → ONGOING/STARTED/CANCELLED; ONGOING → STARTED/CANCELLED; STARTED → COMPLETED. Giải thích chuyển tự động trước giờ 15 phút và hoàn thành sau end, chu kỳ sweep 60 giây; không tuyên bố đổi trạng thái chính xác tức thời ở thời điểm lịch.

## 7. Những thông tin Word đang cũ hoặc chưa có bằng chứng

| Nội dung draft | Đối chiếu phiên bản hiện tại |
| --- | --- |
| 27 endpoint | 29 thao tác HTTP gồm health, 28 nếu loại health; WS tách riêng |
| 52 passed + 1 skipped, coverage 88% | 70 passed + 2 skipped ở SQLite, PG riêng 2 passed; coverage 89% |
| EXPLAIN 1.403 → 0.112, offset 3.43/cursor 1.60 | Số liệu lịch sử khác phép đo hiện tại; chỉ giữ nếu có raw evidence/ngày/commit cũ, không trộn hai lần đo |
| ADMIN xem occupancy | Không có role ADMIN riêng; quản trị sự kiện là ORGANIZER |
| ONGOING = đang diễn ra; CANCELLED = kết thúc | Không khớp state machine/nhóm tab hiện tại; STARTED bị bỏ sót |
| Close code 4401/4403/4404 | Server WS hiện dùng 4401/4404; 4403 chỉ có xử lý phòng thủ ở frontend |
| Notify khi COMPLETED | Transition thủ công có task, auto completion không gửi notify |
| Async notify/WS/ticket | Ticket REST là sync; chỉ rõ handler/dependency tương ứng |
| Dashboard O(1) | SQL aggregate giảm nạp chi tiết vào RAM, không làm cả dashboard O(1); vẫn trả danh sách events |
| `docs/phase-*.md` | Các file cũ đã xóa/gộp; thay bằng link tài liệu hiện hành |
| “naive-UTC”, migration bài học chỉ if_not_exists | Hiện naive theo giờ local; migration 0001 đã được cố định snapshot schema |
| “CI xanh”, các hash cũ | Commit lịch sử không chứng minh CI/code của diff chưa commit; sau chốt phải trỏ đúng version |
| OpenCode/Muse là công cụ duy nhất | Phiên làm việc hiện có Codex; công cụ lịch sử cần nhóm xác nhận, không xóa sự thật cũ hoặc bịa model |
| Nhóm tự viết lại toàn bộ không AI | Chỉ thành viên mới xác nhận được bằng luyện thực hành, AI không thể chứng nhận thay |
| 12 tuần đã làm, gộp bốn khoảng tuần | Chưa có đối chiếu đủ 12 tuần; nhiều commit gần đây cùng ngày 05/10; cần log thật, không chia commit giả để lấp tuần |
| Bước tương lai refresh WS ticket | Đã được frontend lấy ticket mới khi retry/reconnect |

README/Markdown đã cập nhật phần vận hành trong lần trước. **Điều đó không có nghĩa báo cáo Word đã cập nhật mới nhất.** DOCX vẫn là draft ở commit cũ; cần viết lại theo review này trước khi xuất PDF. Bố cục đúng số chương chưa bảo đảm đủ nội dung theo từng chương.

## 8. Làm rõ trọng tâm công nghệ trong báo cáo và demo

Không viết mỗi trang như danh sách chức năng Evently. Dùng tính năng làm thí nghiệm cho cơ chế:

| Câu hỏi nghiên cứu | Thí nghiệm vừa đủ | Minh chứng cần giữ |
| --- | --- | --- |
| Type hints/Pydantic làm gì khi body sai? | Ngày kết thúc trước bắt đầu, capacity âm, thiếu field, response model | Request/422 có loc/msg/type; schema; test và giải thích router chưa xử lý khi validation thất bại |
| Depends giảm lặp và quản lý quyền thế nào? | Không token, sai role, đúng role nhưng không sở hữu | Dependency graph, 401/403, ownership case, test override |
| def/async def khác nhau ở I/O? | Webhook test trì hoãn; concurrent requests so await với blocking call trong bài thực nghiệm riêng | Thời gian/p95 và health responsiveness; cùng môi trường, không đưa cố tình-blocking endpoint vào bản sản phẩm |
| BackgroundTasks khác await ở handler ra sao? | Receiver trì hoãn; so mốc response với task completion và task thất bại | HTTP thật + log timeline; booking vẫn tồn tại khi notifier lỗi |
| WS giải quyết đồng bộ gì? | Hai browser cùng event, user book/cancel, disconnect/reconnect | Frame + UI counter + room cleanup; chỉ rõ REST polling là fallback |
| Index/keyset cải thiện query nào? | Dataset/query cố định; trước–sau index, tăng độ sâu offset | Raw EXPLAIN ANALYZE, buffers nếu đo, median/p95/mean đúng định nghĩa, script và phiên bản |
| Tại sao khóa Event? | Capacity=1, năm request trên PG | 1×201, 4×409, counter/ticket/registration đối chiếu; SQLite không chứng minh FOR UPDATE |
| Vì sao chọn FastAPI thay framework khác? | Cùng schema/route/auth nhỏ trên 1–2 framework đối thủ | Source + command + kết quả tự chạy; đánh giá tích hợp type/validation/docs/dependency, không chỉ số dòng |

Phần cơ chế nên có Uvicorn → ASGI/Starlette → route/dependency/Pydantic → sync threadpool hoặc async handler → response/middleware. Đây là sơ đồ khái quát, không khẳng định mọi bước chạy tuần tự tuyệt đối; dependency/body validation được FastAPI giải quyết trong pipeline. Phân biệt concurrency với parallelism, Python với FastAPI, ORM với framework và I/O với CPU.

Kiến trúc hiện tại là modular monolith: hợp một đồ án nhỏ, transaction một DB, đơn giản triển khai. FastAPI không ép microservices. Điểm nghẽn dự kiến gồm DB locks trên cùng event, DB connection/thread pool, serial broadcast/slow clients và I/O dịch vụ ngoài; phải đo mới được khẳng định điểm nghẽn thực tế. Resource lifecycle cần giải thích đóng session/client, dọn room/ticket; không tuyên bố đã phân tích GC/memory leak nếu chưa có profiling.

FastAPI không có cơ chế độc quyền khiến các framework khác không làm được JWT/WS/background. Lý do phù hợp là tích hợp type-driven validation, dependency và OpenAPI trong cùng mô hình Python/ASGI, giúp nhóm triển khai và kiểm chứng API dễ hơn. Evently đã thể hiện tốt phần lõi cùng vài kỹ thuật chọn thêm, nhưng không thể/không cần thể hiện toàn bộ framework. Các phần chưa dùng như OAuth2 scopes, streaming, nhiều worker hoặc observability có thể nêu giới hạn/hướng phát triển đúng phạm vi.

## 9. Lab và hồ sơ nộp: những phần không thể bỏ qua

Chưa tìm thấy trong repo: báo cáo toàn văn PDF cuối, lab riêng có starter/đáp án, slide 5–7 trang, file/link weekly log chi tiết. Bảng tự kiểm trong Word đã thừa nhận các mục này đang chờ. PDF môn học trang 11 và 14 yêu cầu lab **bắt buộc**; video 2–3 phút chỉ **khuyến khích**.

Lab nên chọn Pydantic + Depends + test override để người khác thực hành trong 30–45 phút: mục tiêu, môi trường, starter; hoàn thiện validator thời gian/capacity; thêm dependency quyền cho một endpoint; viết/hoàn thiện test 422/401/403; 2–3 bài tập kèm đáp án và lỗi thường gặp. Đây là đề xuất thiết kế lab, không phải lab đã được thực hiện. Có thể bổ sung quan sát WS nếu còn thời gian, không biến lab thành việc chạy CRUD sẵn hoặc cài đặt chiếm gần hết buổi.

Hồ sơ nhóm cần hoàn tất bằng dữ liệu thật:

- Tên, MSSN, lớp, GVHD, năm học, phân công module; không nộp bảng phần trăm đóng góp.
- Weekly log chi tiết theo tuần: đã làm, dự kiến, khó khăn, người thực hiện, link minh chứng; phụ lục chỉ tóm tắt.
- Insights/Contributors, 10–20 commit gần nhất, PR/review thật. Các commit thấy được tập trung nhiều ngày 05/10; không kết luận toàn bộ lịch sử hoặc đóng góp cá nhân chỉ từ đoạn log này, nhưng cần kiểm tra yêu cầu phân bố từ tuần 2.
- AI disclosure: công cụ, phần code AI sinh nhiều; ít nhất hai lỗi thật với prompt, response, lỗi, cách phát hiện, cách sửa. Hai lỗi draft nêu chưa có prompt/response kèm theo.
- PDF đầy đủ, slide 5–7 trang, lab riêng, source sạch + mã commit niêm phong ít nhất 24 giờ trước bảo vệ. File branch inventory/hash SHA của working tree không thay thế frozen Git commit.
- Mọi thành viên luyện thay validator, dependency, response model, sửa một test và giải thích transaction/async/WS không dùng AI. Bài thực hành ngẫu nhiên là cổng đạt/không đạt; nhiều tính năng không bù việc không hiểu code.

## 10. File thừa và cách đóng gói

Đợt trước đã xóa 35 file cũ/không còn dùng, gồm tracked coverage, prompt/review UI, fixture mobile, mock API, component bỏ và kế hoạch phase cũ. Không thấy thêm file nào có thể kết luận chắc chắn phải xóa chỉ bằng tên trong đợt này. Không cam kết “không còn một dòng/file thừa”.

- `Bien_ban_bao_cao.docx` là tài liệu nguồn môn học, không phải báo cáo Evently và không vô nghĩa; có thể đặt vào thư mục tài liệu tham chiếu hoặc giữ riêng ngoài gói sản phẩm.
- `Bao_cao_Evently_DRAFT.docx` cần sửa/đổi thành bản cuối, không xóa để che khoảng trống hồ sơ.
- `final-review.md` là chứng cứ kiểm chứng triển khai; file này là đối chiếu yêu cầu học thuật, hai phạm vi khác nhau. Không dùng cả hai như hai báo cáo nộp chính.
- Script đồng bộ worktree và manifest chia nhánh từng phục vụ quản lý các bản review local; đã xóa sau khi hoàn tất commit vì không phục vụ chạy hay triển khai đồ án.
- Tests, migrations, benchmark script, ERD và giấy phép font có giá trị; không xóa để làm repo nhìn ít file hơn.
- `.venv`, `node_modules`, `dist`, caches, `.coverage` sinh lại và `.env` thật có thể tồn tại local để chạy, nhưng không đưa vào archive nộp. Giữ lockfile/env example/source/tests/docs; dùng allowlist hoặc bản checkout sạch từ frozen commit để đóng gói.
- Screenshot gắn vào Word cần kiểm tra lại với web MVP hiện tại; cập nhật ảnh ngoài `docs/assets` không tự cập nhật ảnh đã nhúng trong DOCX.

## 11. Thứ tự chốt hợp lý

1. Sửa broadcast PATCH capacity, chốt nghĩa trạng thái/role/auth/email và DTO quan trọng; test hồi quy vừa đủ. Không mở rộng mobile/ảnh/miền nghiệp vụ.
2. Tăng chiều sâu C4/C5 bằng các thí nghiệm nhỏ và minh chứng có thể chạy lại; so sánh framework ở C1 theo trải nghiệm thật; bổ sung nguồn ở C2.
3. Viết lại Word C11/C12/C13 và các bảng theo code mới; giữ thông tin nhóm chưa biết để nhóm xác nhận, không bịa.
4. Hoàn thiện lab, weekly log, AI disclosure và bằng chứng làm việc nhóm; luyện thực hành không AI.
5. Chốt commit thực, CI đúng commit, rerun các kiểm tra liên quan; khóa bảng phủ, báo cáo, source cùng phiên bản; xuất và kiểm tra PDF/slide/gói nộp.

**Điều kiện có thể nói “đã chốt”: code và demo đúng, báo cáo bám bố cục và phản ánh đúng code, thực nghiệm có bằng chứng, lab và hồ sơ nhóm đầy đủ, phiên bản được niêm phong đúng hạn, từng thành viên giải thích/sửa được phần đã khai báo.** Hiện đã có nền tảng code tốt để đạt các điều kiện này, nhưng chưa đủ căn cứ đánh dấu tất cả đã hoàn thành.
