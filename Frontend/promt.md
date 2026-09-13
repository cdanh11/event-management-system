Bạn là Senior Frontend Engineer + Product Designer.

Hãy xây dựng một frontend MVP hoàn chỉnh cho đồ án:

# Event Management, Registration & Check-in System

Mục tiêu hiện tại CHỈ LÀ XÂY DỰNG UI + MOCK DATA để demo nghiệp vụ trước.

CHƯA được xây dựng:

* Backend
* FastAPI
* Database
* PostgreSQL
* API server thật
* Authentication server thật

Frontend phải được thiết kế sao cho sau này có thể thay Mock API bằng FastAPI thật mà không phải viết lại UI.

---

# 1. Tech stack

Sử dụng:

* React
* TypeScript
* Vite
* React Router
* CSS hoặc Tailwind CSS nếu project đã có sẵn
* Context/useReducer/useState cho state management
* LocalStorage để duy trì mock session và dữ liệu demo

Không sử dụng Redux nếu chưa thực sự cần.

Không sử dụng:

* Next.js
* Firebase
* Supabase
* Backend-as-a-Service
* GraphQL
* WebSocket ở MVP
* microservices

Ưu tiên code đơn giản, rõ ràng, dễ giải thích trong báo cáo và dễ chuyển sang FastAPI.

---

# 2. Kiến trúc frontend

Bắt buộc tổ chức theo:

Page
↓
Feature / Hook
↓
Service Layer
↓
Mock API
↓
Mock Data

UI KHÔNG được import trực tiếp mock data.

Ví dụ:

EventListPage
→ useEvents()
→ eventService.getEvents()
→ mockApi.getEvents()
→ mock/data/events.ts

Sau này:

EventListPage
→ useEvents()
→ eventService.getEvents()
→ apiClient.get("/events")
→ FastAPI

Mục tiêu là thay implementation ở tầng Service/API mà không ảnh hưởng UI.

---

# 3. Domain

Hệ thống là nền tảng quản lý sự kiện.

Ví dụ:

* Tech Conference
* Workshop
* Seminar
* Career Fair
* University Event
* Hackathon

Người dùng có thể xem sự kiện, đăng ký tham gia và nhận vé điện tử.

Ban tổ chức có thể tạo và quản lý sự kiện.

Staff có thể sử dụng hệ thống để check-in người tham dự.

---

# 4. Roles

Có 3 role chính:

ATTENDEE

* xem event
* đăng ký event
* xem vé
* xem QR code
* hủy registration nếu nghiệp vụ cho phép
* xem lịch sử tham gia

STAFF

* xem event được phân công
* quét/nhập ticket code
* check-in attendee
* xem danh sách attendee
* xem thống kê check-in

ORGANIZER

* tạo event
* chỉnh sửa event
* quản lý event
* quản lý ticket/registration
* xem attendee
* xem check-in statistics

Mock authentication phải hỗ trợ chuyển đổi giữa 3 role.

Demo accounts:

[attendee@demo.com](mailto:attendee@demo.com) / 123456
[staff@demo.com](mailto:staff@demo.com) / 123456
[organizer@demo.com](mailto:organizer@demo.com) / 123456

Không cần bảo mật thật.

---

# 5. Folder structure

Tạo cấu trúc tương tự:

src/
├── app/
│   ├── App.tsx
│   ├── router.tsx
│   └── providers/
│
├── components/
│   ├── common/
│   ├── layout/
│   ├── event/
│   ├── ticket/
│   ├── registration/
│   └── checkin/
│
├── pages/
│   ├── auth/
│   │   ├── LoginPage.tsx
│   │   └── RegisterPage.tsx
│   │
│   ├── attendee/
│   │   ├── HomePage.tsx
│   │   ├── EventsPage.tsx
│   │   ├── EventDetailPage.tsx
│   │   ├── MyRegistrationsPage.tsx
│   │   ├── TicketPage.tsx
│   │   └── ProfilePage.tsx
│   │
│   ├── staff/
│   │   ├── StaffDashboardPage.tsx
│   │   ├── CheckInPage.tsx
│   │   └── AttendeesPage.tsx
│   │
│   └── organizer/
│       ├── OrganizerDashboardPage.tsx
│       ├── EventManagementPage.tsx
│       ├── CreateEventPage.tsx
│       ├── EditEventPage.tsx
│       ├── EventAttendeesPage.tsx
│       └── EventCheckInStatsPage.tsx
│
├── features/
│   ├── auth/
│   ├── events/
│   ├── registrations/
│   ├── tickets/
│   └── checkin/
│
├── services/
│   ├── authService.ts
│   ├── eventService.ts
│   ├── registrationService.ts
│   ├── ticketService.ts
│   └── checkinService.ts
│
├── mock/
│   ├── data/
│   │   ├── users.ts
│   │   ├── events.ts
│   │   ├── registrations.ts
│   │   ├── tickets.ts
│   │   └── checkins.ts
│   │
│   └── mockApi.ts
│
├── types/
│   ├── user.ts
│   ├── event.ts
│   ├── registration.ts
│   ├── ticket.ts
│   └── checkin.ts
│
├── hooks/
│   ├── useAuth.ts
│   ├── useEvents.ts
│   ├── useRegistrations.ts
│   ├── useTickets.ts
│   └── useCheckin.ts
│
├── utils/
│   ├── date.ts
│   ├── format.ts
│   └── storage.ts
│
├── styles/
│   └── globals.css
│
└── main.tsx

Không nhất thiết phải tạo mọi file ngay lập tức nếu chưa sử dụng.

---

# 6. Mock entities

Thiết kế TypeScript types phản ánh domain backend tương lai.

Tối thiểu:

User

* id
* name
* email
* role
* avatar

Event

* id
* organizerId
* title
* description
* location
* startTime
* endTime
* capacity
* registeredCount
* status
* bannerImage
* createdAt

Registration

* id
* eventId
* attendeeId
* registeredAt
* status

Ticket

* id
* registrationId
* ticketCode
* qrValue
* status
* issuedAt

CheckIn

* id
* ticketId
* eventId
* attendeeId
* checkedInBy
* checkedInAt
* status

Event status:

DRAFT
PUBLISHED
ONGOING
COMPLETED
CANCELLED

Registration status:

REGISTERED
CANCELLED

Ticket status:

VALID
USED
CANCELLED

Check-in status:

SUCCESS
REJECTED

Không sử dụng `any`.

---

# 7. Mock data

Tạo dữ liệu đủ để demo.

Ít nhất:

Users:

* 3 attendee
* 2 staff
* 1 organizer

Events:

* 5–8 events
* event đã published
* event sắp diễn ra
* event đang diễn ra
* event completed
* event cancelled
* event gần full
* event đã full

Registrations:

* nhiều attendee đăng ký các event khác nhau

Tickets:

* ticket VALID
* ticket USED
* ticket CANCELLED

Check-ins:

* một số attendee đã check-in
* một số chưa check-in

Dữ liệu phải có quan hệ hợp lý.

Ví dụ:

Event A capacity = 100
registeredCount = 73

Event B capacity = 50
registeredCount = 50

---

# 8. Attendee UI

## Home

Hiển thị:

* featured events
* upcoming events
* categories
* search
* event cards

---

## Events

Cho phép:

* search
* filter theo status
* filter theo category
* sort theo date
* pagination giả lập nếu cần

---

## Event Detail

Hiển thị:

* banner
* title
* description
* location
* start/end time
* organizer
* remaining seats
* registration status

CTA:

"Register"

Nếu event đã full:

"Sold out"

Nếu đã đăng ký:

"View Ticket"

---

# 9. Registration flow

Flow phải trực quan:

Event Detail
↓
Register
↓
Registration Confirmation
↓
Registration Success
↓
Ticket Generated
↓
My Ticket

Khi đăng ký:

* kiểm tra event còn capacity
* kiểm tra attendee đã đăng ký chưa
* tạo registration
* tạo ticket
* cập nhật registeredCount
* hiển thị success message

Nếu event full:

hiển thị:

"Event is full"

Nếu đã đăng ký:

"Already registered"

Mock API phải trả error code tương ứng.

---

# 10. Ticket UI

Ticket page phải giống vé sự kiện thực tế.

Hiển thị:

* Event name
* attendee name
* date
* location
* ticket code
* QR Code mock
* ticket status

Có thể dùng QR library hoặc tạo placeholder QR.

Không cần QR thật ở MVP nhưng cấu trúc phải sẵn sàng để backend sau này cung cấp ticket code/QR value.

---

# 11. Check-in UI

Đây là nghiệp vụ quan trọng nhất của MVP.

Staff mở:

/staff/check-in

UI gồm:

* input ticket code
* camera scan placeholder
* Search attendee
* Check-in button

Flow:

Enter ticket code
↓
Find ticket
↓
Validate ticket
↓
Check ticket status
↓
Check event
↓
Check whether already checked in
↓
Success / Reject

Success:

"Check-in successful"

Hiển thị:

* attendee
* event
* ticket code
* check-in time

Nếu ticket đã được sử dụng:

"Ticket already checked in"

Nếu ticket không tồn tại:

"Invalid ticket"

Nếu ticket bị cancelled:

"Ticket cancelled"

---

# 12. Staff dashboard

Hiển thị:

* assigned events
* total attendees
* checked-in
* remaining
* check-in percentage

Ví dụ:

Total: 250
Checked-in: 184
Remaining: 66
Rate: 73.6%

Có bảng attendee:

Name
Ticket
Registration status
Check-in status
Check-in time

Có filter:

* All
* Checked in
* Not checked in

---

# 13. Organizer dashboard

Dashboard hiển thị:

* total events
* published events
* upcoming events
* total registrations
* total check-ins

Event table:

Event
Date
Capacity
Registered
Check-in
Status
Actions

Actions:

* View
* Edit
* Attendees
* Check-in statistics

---

# 14. Organizer create event

Form:

* title
* description
* location
* start date/time
* end date/time
* capacity
* category
* banner

Validation:

* title required
* description required
* start < end
* capacity > 0
* start time không được trước hiện tại đối với event mới

Sau submit:

DRAFT event được tạo.

Cho phép Publish.

---

# 15. Event lifecycle UI

Hỗ trợ:

DRAFT
↓
PUBLISHED
↓
ONGOING
↓
COMPLETED

Ngoài ra:

DRAFT → CANCELLED
PUBLISHED → CANCELLED

Không cho UI thực hiện transition không hợp lệ.

Ví dụ:

COMPLETED không thể quay lại PUBLISHED.

---

# 16. Mock API

Tạo mockApi.ts với interface gần giống REST API.

Ví dụ:

auth:
POST /auth/login
GET /auth/me

events:
GET /events
GET /events/:id
POST /events
PATCH /events/:id
POST /events/:id/publish
POST /events/:id/cancel

registrations:
POST /events/:eventId/register
GET /registrations/me
GET /registrations/:id
POST /registrations/:id/cancel

tickets:
GET /tickets/:id
GET /tickets/:id/validate

checkin:
POST /checkins
GET /events/:eventId/checkins
GET /events/:eventId/checkin-stats

organizer:
GET /organizer/events
GET /organizer/events/:eventId/attendees

staff:
GET /staff/events
GET /staff/events/:eventId/attendees

Mock API phải có artificial delay khoảng 300–700ms để UI có thể demo loading state.

---

# 17. HTTP-like error behavior

Mock API phải mô phỏng:

200
201
400
401
403
404
409

Đặc biệt:

409 Conflict

dùng cho:

* event full
* duplicate registration
* ticket already checked in

Ví dụ:

register event khi full
→ 409 EVENT_FULL

register event lần 2
→ 409 ALREADY_REGISTERED

check-in ticket đã dùng
→ 409 TICKET_ALREADY_USED

---

# 18. Loading / Error / Empty states

Tất cả API-like operation phải có:

Loading
Success
Error
Empty

Không được chỉ render dữ liệu tĩnh.

Ví dụ:

Events loading...

No events found.

Registration failed.

Check-in successful.

---

# 19. Authentication mock

Login bằng demo account.

Sau login:

attendee
→ attendee pages

staff
→ staff dashboard

organizer
→ organizer dashboard

Lưu session bằng LocalStorage.

Có protected route theo role.

Ví dụ:

ATTENDEE không được truy cập:

/organizer/*
/staff/*

STAFF không được truy cập:

/organizer/*

ORGANIZER có organizer permissions.

---

# 20. Responsive UI

Thiết kế responsive:

Desktop
Tablet
Mobile

Ưu tiên:

* clean
* modern
* professional
* giống SaaS/event platform
* dễ demo

Không sử dụng quá nhiều:

* gradient
* animation
* 3D
* glassmorphism
* decorative effects

Ưu tiên UX và nghiệp vụ.

---

# 21. Demo scenario bắt buộc

Sau khi hoàn thành phải đảm bảo có thể demo các scenario sau.

SCENARIO 1:

Attendee login
→ xem events
→ mở event
→ register
→ ticket được tạo
→ mở ticket

SCENARIO 2:

Attendee đăng ký event đã full
→ API mock trả 409
→ UI hiển thị Event Full.

SCENARIO 3:

Staff login
→ mở check-in
→ nhập ticket code hợp lệ
→ check-in thành công.

SCENARIO 4:

Staff nhập lại ticket code vừa check-in
→ 409 TICKET_ALREADY_USED
→ UI hiển thị Ticket Already Checked In.

SCENARIO 5:

Organizer login
→ dashboard
→ tạo event
→ publish event
→ xem registrations
→ xem check-in statistics.

SCENARIO 6:

Attendee hủy registration
→ registration CANCELLED
→ ticket CANCELLED
→ UI cập nhật.

---

# 22. Important architecture rules

1. UI không import mock data trực tiếp.

2. UI không chứa business logic phức tạp.

3. Business logic nằm ở service/mock API layer.

4. TypeScript types phải phản ánh backend domain.

5. Không hard-code dữ liệu trong component.

6. Không tạo fake backend server.

7. Không tạo database.

8. Không thêm công nghệ không cần thiết.

9. Code phải dễ chuyển sang FastAPI.

10. API contract phải có tên endpoint, request, response và error structure rõ ràng.

---

# 23. Documentation

Tạo:

docs/
├── architecture.md
├── mock-api.md
└── demo-scenarios.md

architecture.md giải thích:

Page
→ Hook
→ Service
→ Mock API
→ Mock Data

mock-api.md liệt kê toàn bộ endpoint.

demo-scenarios.md hướng dẫn cách demo 6 scenario ở trên.

---

# 24. Final requirement

Sau khi implement:

1. Chạy được bằng npm install + npm run dev.
2. Không có TypeScript error.
3. Không có import lỗi.
4. Các route hoạt động.
5. Mock login hoạt động.
6. Registration hoạt động.
7. Ticket generation hoạt động.
8. Check-in hoạt động.
9. Organizer flow hoạt động.
10. LocalStorage hoạt động.
11. Loading/error/empty state hoạt động.
12. README có hướng dẫn chạy project.

Trước khi kết thúc, hãy kiểm tra toàn bộ flow từ:

Login
→ Browse Event
→ Register
→ Ticket
→ Staff Check-in
→ Organizer Dashboard

và sửa mọi lỗi phát hiện được.

KHÔNG triển khai backend ở bước này.
KHÔNG triển khai database ở bước này.

Chỉ hoàn thành FRONTEND MOCK MVP.
