# Event Management System - Frontend MVP

Hệ thống quản lý sự kiện, đăng ký và check-in - Frontend Mock MVP

## Kết nối FastAPI

Copy `.env.example` thành `.env` và đặt `VITE_API_BASE_URL=http://localhost:8000`. Khởi động backend trong thư mục `../Backend` trước khi chạy frontend. Tầng service gọi REST API, access token được làm mới tự động bằng refresh-token HttpOnly cookie.

## Tech Stack
- React 18 + TypeScript
- Vite
- React Router v6
- Tailwind CSS
- Lucide React (icons)
- Context + useReducer + useState cho state management
- LocalStorage cho mock session & data persistence

## Cấu trúc thư mục

```
src/
├── app/
│   ├── App.tsx
│   ├── router.tsx
│   └── providers/
│       └── AuthProvider.tsx
├── components/
│   ├── common/
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Card.tsx
│   │   ├── Modal.tsx
│   │   ├── Badge.tsx
│   │   ├── Alert.tsx
│   │   ├── Loading.tsx
│   │   └── EmptyState.tsx
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   ├── Layout.tsx
│   │   └── ProtectedRoute.tsx
│   ├── event/
│   │   └── EventCard.tsx
│   └── ticket/
│       └── TicketDisplay.tsx
├── pages/
│   ├── auth/
│   │   ├── LoginPage.tsx
│   │   └── RegisterPage.tsx
│   ├── attendee/
│   │   ├── HomePage.tsx
│   │   ├── EventsPage.tsx
│   │   ├── EventDetailPage.tsx
│   │   ├── MyRegistrationsPage.tsx
│   │   ├── TicketPage.tsx
│   │   └── ProfilePage.tsx
│   ├── staff/
│   │   ├── StaffDashboardPage.tsx
│   │   ├── CheckInPage.tsx
│   │   └── AttendeesPage.tsx
│   └── organizer/
│       ├── OrganizerDashboardPage.tsx
│       ├── EventManagementPage.tsx
│       ├── CreateEventPage.tsx
│       ├── EditEventPage.tsx
│       ├── EventAttendeesPage.tsx
│       └── EventCheckInStatsPage.tsx
├── features/
├── services/
│   ├── authService.ts
│   ├── eventService.ts
│   ├── registrationService.ts
│   ├── ticketService.ts
│   └── checkinService.ts
├── mock/
│   ├── data/
│   │   ├── users.ts
│   │   ├── events.ts
│   │   ├── registrations.ts
│   │   ├── tickets.ts
│   │   └── checkins.ts
│   └── mockApi.ts
├── hooks/
│   ├── useAuth.ts
│   ├── useEvents.ts
│   ├── useRegistrations.ts
│   ├── useTickets.ts
│   └── useCheckin.ts
├── types/
│   ├── user.ts
│   ├── event.ts
│   ├── registration.ts
│   ├── ticket.ts
│   └── checkin.ts
├── utils/
│   ├── date.ts
│   ├── format.ts
│   └── storage.ts
└── styles/
    └── globals.css
```

## Cài đặt & Chạy

```bash
# Cài đặt dependencies
npm install

# Chạy development server
npm run dev

# Build production
npm run build

# Preview production build
npm run preview
```

Ứng dụng sẽ chạy tại `http://localhost:5173`

## Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| Attendee | attendee@demo.com | 123456 |
| Staff | staff@demo.com | 123456 |
| Organizer | organizer@demo.com | 123456 |

## Tính năng đã implement

### Attendee
- ✅ Xem danh sách sự kiện (Home, Events page)
- ✅ Tìm kiếm, lọc, sắp xếp sự kiện
- ✅ Xem chi tiết sự kiện
- ✅ Đăng ký sự kiện (với validation capacity, duplicate)
- ✅ Xem vé đã đăng ký (My Registrations)
- ✅ Xem chi tiết ticket với QR code
- ✅ Hủy đăng ký
- ✅ Profile page

### Staff
- ✅ Dashboard với thống kê sự kiện được phân công
- ✅ Check-in bằng mã vé (manual input + QR placeholder)
- ✅ Xử lý các trường hợp: success, already used, invalid, cancelled
- ✅ Danh sách attendee với filter (all, checked-in, pending)
- ✅ Thống kê real-time

### Organizer
- ✅ Dashboard với tổng quan sự kiện
- ✅ Quản lý sự kiện (CRUD, publish, cancel)
- ✅ Tạo sự kiện mới với validation đầy đủ
- ✅ Chỉnh sửa sự kiện
- ✅ Xem danh sách attendee theo event
- ✅ Thống kê check-in chi tiết (theo giờ, tỷ lệ)

### Authentication & Authorization
- ✅ Mock login với 3 roles
- ✅ Role-based protected routes
- ✅ Session persistence (LocalStorage)
- ✅ Redirect based on role after login

### Architecture
- ✅ Layered architecture (Page → Hook → Service → Mock API → Mock Data)
- ✅ TypeScript types phản ánh backend domain
- ✅ Mock API với HTTP-like behavior (status codes, errors, delays)
- ✅ Loading/Error/Empty states cho mọi API call
- ✅ Responsive UI (mobile, tablet, desktop)

## Documentation

- [Architecture](docs/architecture.md)
- [Mock API](docs/mock-api.md)
- [Demo Scenarios](docs/demo-scenarios.md)

## Chuyển sang FastAPI (Production)

Để thay Mock API bằng FastAPI thực tế:

1. Tạo `src/api/apiClient.ts` với axios/fetch wrapper
2. Cập nhật `src/services/*.ts` để gọi `apiClient` thay vì `mockApi`
3. Cấu hình environment variables cho API base URL
4. Thêm JWT token interceptor
5. Xử lý refresh token logic
6. Các Page và Hook **không cần thay đổi**

## Demo Scenarios

Xem chi tiết tại [Demo Scenarios](docs/demo-scenarios.md) cho 6 scenario bắt buộc:

1. Attendee Full Flow
2. Event Full (409 Error)
3. Staff Check-in Success
4. Duplicate Check-in (409 Error)
5. Organizer Full Flow
6. Cancel Registration

## License

MIT
