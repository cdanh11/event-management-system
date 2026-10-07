# Chốt giao diện web MVP và đối chiếu Tầng 1–2

> Review trước đợt đóng backend cuối. Các mục OAuth2, email SMTP/QR, DTO, PATCH capacity broadcast và phân trang organizer đã được xử lý ngày 07/10/2026; kết quả hiện hành ở [final-review.md](final-review.md). Các nhận định còn thiếu của bản review này là lịch sử, không phải trạng thái source cuối. Báo cáo Word không thuộc đợt sửa source này.

Ngày kiểm chứng: 07/10/2026. Đây là kết quả rà soát source đang chỉnh sửa, chưa commit/push; không thay thế báo cáo môn học.

## Phạm vi

- Chỉ web desktop. Loại yêu cầu mobile khỏi phạm vi prompt, triển khai và nghiệm thu; không thêm menu mobile hoặc kiểm thử mobile.
- Giữ frontend đơn giản để minh họa FastAPI: không thêm ảnh, banner, preview hoặc nghiệp vụ mới.
- Đợt này sửa frontend và tài liệu ghi nhận kết quả; không sửa source backend, không viết lại báo cáo Word.
- CSS responsive có sẵn được giữ để tránh làm hỏng layout; điều này không phải cam kết hỗ trợ mobile.

## Frontend đã chỉnh

| Khu vực | Kết quả |
| --- | --- |
| Foundation | Dùng chung tên/màu trạng thái, định dạng thời gian cùng ngày và nhiều ngày; trạng thái Door dựa trên trạng thái server, không hiện countdown mâu thuẫn khi đã mở check-in |
| Navigation | Menu Overview / Events / Dashboard / Create event có cùng chiều cao và căn giữa; bỏ viền pill của Create event, bỏ avatar mọi vai trò; đánh dấu trang đang chọn; bỏ New event và Live trùng lặp; scrollbar ổn định để tránh trang bị đẩy ngang |
| Manage | Connector nằm giữa các bước, không xuyên qua dấu tick; Cancelled có banner riêng; số đăng ký một dòng, meter rộng toàn hàng; bổ sung When/Where/Category/Capacity/Door status |
| Overview | Phân biệt sự kiện đang check-in với sự kiện tiếp theo; căn thống kê, lấy số liệu backend; mỗi hàng attention có một lý do, tối đa năm hàng |
| Events | Bộ lọc gọn; ưu tiên đang check-in, sắp diễn ra, đã kết thúc, rồi draft; hiển thị từng nhóm 20 sự kiện |
| Dashboard (trước đây Live) | Một chỉ báo kết nối, baseline bộ đếm gọn, meter toàn hàng và nút Manage phụ |
| Actions / forms | Một hành động chính trong nhóm chuyển trạng thái; Cancel nhẹ hơn; lịch bị khóa hiển thị thông báo thay cho form bị disable; Create có Cancel cạnh nút tạo |
| Attendee | Registered màu xanh; organizer có CTA Manage đúng vai trò; icon nằm trong hàng thông tin; màu viền vé theo trạng thái; ngày giờ thống nhất và thông báo đóng hủy vé ngắn hơn |
| Check-in | Đổi nhãn Door thành Check-in cho organizer/staff; dùng chung thành phần giữa organizer/staff; một danh sách lịch sử; tách Checked-in khỏi Registered; nút scan bị khóa vẫn đọc được |
| Auth | Link đăng ký rõ hơn; giữ luồng đăng nhập và layout tập trung |

Các nhóm file chính nằm trong `Frontend/src/lib`, `components/ui`, `components/layout`, `pages`, `features` và `styles`. Copy dùng chung nằm ở `Frontend/src/copy/strings.ts`.

### Giới hạn còn lại

- Load more của danh sách organizer là chia trang phía trình duyệt. API dashboard hiện vẫn trả toàn bộ sự kiện; không được mô tả là phân trang server. Danh sách public có luồng phân trang riêng.
- Lịch sử Door lấy tối đa 100 bản ghi; từ 100 hiển thị `≥100`, không giả định đó là tổng chính xác. Lịch sử được cập nhật theo cơ chế polling hiện có.
- Kiểm tra focus, modal và trạng thái loading/error theo thành phần hiện có; chưa phải audit WCAG đầy đủ.
- Không xóa/reset dữ liệu demo đang dùng của người dùng. Dataset kiểm tra riêng không chứng minh database cũ hoàn toàn sạch.

## Kết quả kiểm chứng

| Kiểm tra | Kết quả |
| --- | --- |
| Frontend lint | Qua |
| Frontend tests | 23 passed, 0 failed |
| Copy audit | Không còn lỗi phát hiện bởi script |
| Production build | Qua, Vite build thành công |
| Backend regression | 70 passed, 2 skipped; coverage 89% |
| PostgreSQL trong lần chạy này | Hai test bị skip do chưa cấu hình database test PostgreSQL; không suy diễn kết quả SQLite thành kết quả PostgreSQL |
| Browser console | Không ghi nhận error trong các luồng đã kiểm tra |

Kiểm tra trực tiếp trình duyệt ở bề rộng 1024, 1280 và 1440: không phát hiện tràn ngang trong các trang kiểm tra. Đã đi qua Overview, Events, Manage, Live, trang public, Create, Explore, My tickets, QR ticket và Door theo các vai trò organizer/staff/attendee.

Đã tạo draft bằng form, đăng ký vé và scan vé thật qua API local. Lần kiểm tra ban đầu: 7 sự kiện, 5 đăng ký, 1 check-in. Lần nghiệm thu FE tiếp theo bổ sung một registration/ticket thật trong database test riêng để kiểm tra banner admission: 7 sự kiện, 6 đăng ký, 2 check-in. Đây là database SQLite riêng tại thư mục temp, backend port 8010/frontend port 5175, không phải số liệu benchmark và không sửa database demo của người dùng. Chưa thực hiện kiểm thử tải hoặc kiểm thử mobile.

## Checklist prompt FE sau lượt hoàn thiện tiếp theo

Đường dẫn trong bảng tính từ `Frontend/src`. “Đã sửa” gồm đối chiếu source; các kiểm tra trực tiếp trên trình duyệt được ghi riêng phía dưới. Các yêu cầu bổ sung của người dùng ưu tiên hơn prompt đính kèm.

| Mục prompt | Kết quả và file |
| --- | --- |
| 1.1 / checklist: trạng thái, nhãn, màu, viền | Đã thống nhất qua `lib/status.ts`, `copy/strings.ts`, `components/ui/Agenda.tsx`; dùng biến CSS để điều chỉnh tương phản trên nền tối mà giữ cùng trạng thái |
| 1.2: ngày giờ | `lib/datetime.ts`: formatWhen; formatRange là alias dùng chung, không phải formatter riêng |
| 1.2: thang nút | `components/ui/Button.tsx`, styles; lifecycle là secondary khi chọn tab có hành động riêng, tránh hai primary trên cùng trang Manage |
| P0.1: countdown mâu thuẫn | `DoorStatus.tsx`, `lib/status.ts`, Manage/EventDetail/MyRegistrations/PosterBand; STARTED không hiện Starts in |
| P0.2: stepper/cancelled | `pages/organizer/Manage.tsx`, `styles/organizer.css`; connector riêng, cancelled chỉ banner |
| P0.3: Registered/meter/Live | `Manage.tsx`, `organizer.css`; meter toàn hàng, Live chỉ khi socket open |
| P0.4: Overview facts | `Manage.tsx`; đủ thông tin và mô tả thật từ API, không tự che mô tả thử trong database cũ |
| P0.5–7: menu/nút trùng/active | `components/layout/AppShell.tsx`, `globals.css`; một Create event; Overview/Events/Dashboard/Create event không đổi vị trí khi chọn |
| P0.8: organizer xem public | `pages/attendee/EventDetail.tsx`; Manage theo quyền sở hữu, ghi chú đúng vai trò, icon trong thẻ |
| P0.9–10: scrollbar/abbr | `styles/globals.css`; stable gutter và bỏ gạch chân QR |
| P0.11: sort/meter terminal | `lib/status.ts`, `components/ui/Agenda.tsx`, `pages/organizer/Events.tsx`; thứ tự đúng, terminal xám và nhãn registered |
| P0.12: số liệu | SQL dashboard giữ nguyên; seed hiện tại có registration thật. Không thay tổng SQL bằng counter frontend để che lỗi dữ liệu cũ |
| P1.1: Overview | `pages/organizer/Dashboard.tsx`, `OrganizerAgenda.tsx`; Now/Next/empty, thống kê, attention một lý do, tối đa năm hàng |
| P1.2: Events | Bộ lọc/đếm/hàng link đã sửa. Load more 20 hàng phía client; server pagination organizer chưa có trong contract hiện tại, không đổi backend trong lượt FE |
| P1.3: Manage | Back/public quiet, một câu Check-in, Cancel cuối hàng; modal nêu hậu quả/số người; `DoorWorkspace` dùng chung; lịch khóa và Staff empty rõ ràng |
| P1.4: Dashboard (Live cũ) | `pages/organizer/Live.tsx`, `DoorCounter.tsx`, `operations.css`; chọn đúng event, bộ đếm một baseline, meter rộng; reconnect/polling/paused, empty “Waiting for the next registration.” |
| P1.5: Create | `pages/organizer/Create.tsx`, `organizer.css`; chọn phương án form 640px căn giữa, Cancel cuối form; validation sau blur/submit, giờ tương lai; toast và điều hướng giữ nguyên |
| P1.6: Explore | `Agenda.tsx`, `Explore.tsx`, `attendee.css`; Registered xanh + View ticket mở vé trực tiếp; Cancelled ngắn; cột 150px; link tiêu đề phủ vùng hàng, action riêng không lồng anchor |
| P1.6: Sort | Select có viền “Sort: Soonest”; chỉ một lựa chọn đúng thứ tự API hiện có, không tạo lựa chọn giả hoặc sắp lại riêng một trang cursor gây sai kết quả |
| P1.6: tab active | Giữ “Preparing / check-in open” vì contract gom ONGOING và STARTED; gọi cả hai là “Check-in open” sẽ sai quyền check-in |
| P1.7: My tickets | `MyRegistrations.tsx`, `attendee.css`; hàng mở Event detail qua link phủ vùng hàng, action độc lập; cột action 180px, View ticket quiet, Cancel quiet đỏ, Cancellation closed không bẻ dòng, viền đúng trạng thái |
| P1.8: Auth/brand | `auth.css`, `copy/strings.ts`; form căn giữa dọc, link đăng ký rõ, thống nhất Evently chữ E hoa |
| P1.9: Check-in | `features/door/DoorDesk.tsx`, `CheckinDesk.tsx`, Manage; một history server, You chỉ cho lần quét thành công của phiên này; banner trên input tự ẩn sau 5s, Last scan giữ lại; tên lấy từ history API, fallback mã vé nếu history lỗi |
| P1.10: việc chung | Không footer/avatar; h1 trang dữ liệu khoảng 36px, focus/hover/disabled dùng chung; action và liên kết không lồng anchor |
| P2: mobile | Loại khỏi phạm vi theo yêu cầu trực tiếp của người dùng; không nghiệm thu 375px/768px |
| P2: tương phản | Kiểm tra các cặp token chính: muted/paper 5.35, green/paper 5.16, orange text/paper 5.25, disabled/haze khoảng 4.50, green sáng/ink 10.77, violet/white 7.21. Không suy diễn thành chứng nhận WCAG toàn ứng dụng |
| P2: accessibility | Toast aria-live, icon labels, field labels/error; modal Esc, focus trap và trả focus. Esc/return focus đã kiểm tra trực tiếp trên trình duyệt |
| P2: loading/error | `useQuery`, `states.tsx` giữ nội dung khi refetch; skeleton, thông báo lỗi và Retry. Manage có heading khi đang tải |
| Mục 5: dữ liệu demo | Không cleanup database người dùng. Test riêng có dữ liệu thật; danh sách thử, mô tả disposable hay counter lệch trong DB khác phải dọn ở bước dữ liệu, không giấu bằng CSS |
| Mục 6.1–2: ảnh/preview | Không làm theo yêu cầu tối giản, không ảnh của người dùng; chọn căn giữa form |
| Mục 6.3: toast/loading ghi | Giữ và rà các luồng create/publish/start/complete/cancel/notify/assign/reschedule; state busy và xử lý lỗi có trong các handler |
| Commit mỗi priority | Chưa commit/push; các thay đổi vẫn review được trong diff và các feature worktree hiện có |

### Kiểm tra trực tiếp bổ sung

- Form Create ở viewport 1280 có chiều rộng 640px, lề hai bên bằng nhau; không có alert trước khi chạm ô và có đúng một primary.
- View ticket trong hàng Design Systems Workshop mở đúng ticket bằng registration hiện có.
- Quét lại vé đã dùng: cảnh báo Already scanned, không thêm history; banner tự ẩn và Last scan vẫn còn.
- Quét fixture riêng AI-FE-REVIEW: Last scan “Admitted: Linh Tran”, Checked in tăng 1 → 2; history có Linh Tran và nhãn You. History lookup thất bại không đổi admission đã thành công thành scan lỗi.
- Tab Staff không có lifecycle primary trùng; Notify modal hiển thị số đăng ký, Esc đóng dialog và focus trở về Notify attendees.
- Lint, 23 tests, copy audit và build đều qua sau lượt sửa cuối. Backend không sửa trong lượt này; số regression backend ở bảng trên là từ lần chạy trước.

## Tầng 1: đủ cơ chế FastAPI để trình bày

Đối chiếu chi tiết và nguồn rubric xem [requirements-review.md](requirements-review.md). Source hiện có ba kỹ thuật lõi: Pydantic validation, dependency injection bằng Depends, và async I/O ở các luồng phù hợp. Các kỹ thuật bổ sung gồm OpenAPI/Swagger, exception handling, BackgroundTasks, middleware, response models và TestClient. Lifespan quản lý tác vụ vòng đời cũng có trong source.

Luồng minh họa đã có JWT/phân quyền, Event CRUD, đăng ký vé với kiểm soát sức chứa, lỗi validation 422, tác vụ nền và dashboard WebSocket. Không cần thêm framework hoặc nghiệp vụ chỉ để tăng số công nghệ.

Các điểm phải mô tả đúng khi báo cáo:

- Hiện dùng HTTPBearer với JWT và login JSON; chưa phải OAuth2 password flow/scopes. ORGANIZER là vai trò quản lý, không có vai trò ADMIN độc lập.
- BackgroundTasks không phải hàng đợi bền vững. Nếu chưa cấu hình webhook thì gửi thông báo là mô phỏng; chưa có bằng chứng gửi email thực tế. Không khẳng định API hoàn tất trong vài mili giây khi chưa đo.
- ONGOING là preparing; STARTED là mở check-in. Không diễn giải cả hai thành cùng một trạng thái.
- FastAPI không tự làm mọi I/O thành bất đồng bộ và không ép ứng dụng phải dùng microservices.

## Tầng 2: nền tảng source có, bằng chứng chốt còn thiếu

Source có cấu hình môi trường, quản lý secret, migration/seed, kiểm thử, cấu hình CI, tài liệu cài đặt/demo và các biện pháp bảo mật đã đối chiếu ở review chi tiết. Có cấu hình CI không đồng nghĩa đã có một run CI thành công cho phiên bản cuối.

Trước khi tuyên bố hoàn tất cần có commit source được chốt, kết quả CI trên commit đó, bằng chứng hoạt động nhóm/Git và nhật ký thực tế. Không dựng dữ liệu lịch sử hoặc khẳng định đáp ứng bằng tài liệu chưa được kiểm chứng. Báo cáo, slide, lab và phần sử dụng AI phải khớp phiên bản source cuối.

### Các mục backend cần xử lý trước khi đóng source

1. PATCH đổi capacity đang cập nhật database nhưng chưa broadcast occupancy mới. Live có thể giữ capacity cũ đến khi có frame tiếp theo hoặc reconnect. Đây là lỗi nhất quán dữ liệu đã tái hiện, không nên bỏ qua vì Tầng 3 tự chọn.
2. Một số response chưa có DTO rõ ràng: occupancy, ws-ticket, organizer dashboard và health. Chuẩn hóa giúp OpenAPI và frontend contract dễ chứng minh hơn.
3. Xác nhận với yêu cầu cuối có bắt buộc OAuth2 password flow và email thật hay chỉ JWT/tác vụ nền minh họa; source hiện tại không được mô tả quá mức.

Đợt frontend này ghi nhận các mục trên, chưa sửa backend.

## Tầng 3 và công việc tiếp theo

Tầng 3 không phải chưa triển khai hoàn toàn: đã có WebSocket realtime và hướng tối ưu truy vấn/index/cursor kèm benchmark. Phần cần hoàn thiện là chọn mục phù hợp, chứng minh kết quả đo, đối chiếu giới hạn và tránh khai đủ mọi mục tự chọn.

Trình tự chốt: nghiệm thu frontend web → xử lý các mục backend còn lại và kiểm tra contract → hoàn thiện bằng chứng cho mục Tầng 3 đã chọn → chốt commit/CI → viết báo cáo, lab, slide và nhật ký theo rubric. Use case/yêu cầu chức năng ở Chương 11; Chương 3 dành cho môi trường. Không cập nhật báo cáo Word trước khi source được chốt.
