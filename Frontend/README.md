# Evently Frontend

React + TypeScript client demo toàn bộ API Evently end-to-end. Mọi request chạy qua
`src/api/apiClient.ts` tới backend FastAPI (`VITE_API_BASE_URL`, mặc định
`http://localhost:8000`); backend phải chạy trước khi đăng nhập hoặc tải dữ liệu.

## Chạy local

```powershell
npm ci
Copy-Item .env.example .env
npm run dev -- --port 5173
```

Kiểm tra chất lượng:

```powershell
npm run lint
npm run build
```

## Chức năng theo vai trò

- **Attendee**: khám phá event, đăng ký/hủy vé, xem vé; tự tạo tài khoản ở `/login`.
- **Staff**: check-in vé bằng ticket code (vé một lần duy nhất).
- **Organizer**: dashboard, tạo event, lifecycle Publish/Start/Complete/Cancel,
  reschedule, notify, xóa nháp, gán staff, xem occupancy realtime ở `/organizer/live`.

Kịch bản demo chi tiết từng bước: [`docs/demo-scenarios.md`](docs/demo-scenarios.md).

## Tài liệu

| File | Nội dung |
| --- | --- |
| [`docs/architecture.md`](docs/architecture.md) | Luồng Page → service → apiClient, quy ước `snake_case`/`camelCase` |
| [`docs/authentication.md`](docs/authentication.md) | Đăng nhập/đăng ký, phiên, phân luồng theo role |
| [`docs/realtime-dashboard.md`](docs/realtime-dashboard.md) | Dashboard realtime và kịch bản demo hai trình duyệt |
| [`docs/demo-scenarios.md`](docs/demo-scenarios.md) | Checklist demo E2E cho buổi bảo vệ |

Tài liệu tổng của đồ án: [`../readme.md`](../readme.md).
