# Kiến trúc frontend

## Luồng dữ liệu

```text
Page → hook/context → service → apiClient → FastAPI
```

| Lớp | File | Trách nhiệm |
| --- | --- | --- |
| Page/route | `src/app/App.tsx` | Màn hình theo vai trò, bảo vệ bằng `RoleGate` |
| Hook/context | `src/hooks/useAsync.ts`, `src/features/auth/` | Fetch có trạng thái loading/error/reload; session user + login/register/logout |
| Service | `src/services/services.ts` | Gọi REST endpoint, chuẩn hóa response `snake_case` → model UI `camelCase` ở một điểm duy nhất |
| HTTP | `src/api/apiClient.ts` | Bearer access token, tự refresh qua HttpOnly cookie khi gặp 401, ném `ApiError {status, code}` thống nhất |
| Realtime | `src/realtime/useOccupancySocket.ts` | WebSocket occupancy (chi tiết ở [`realtime-dashboard.md`](realtime-dashboard.md)) |

Quy ước: UI không gọi `fetch` trực tiếp; mọi chuyển đổi tên trường API nằm trong
`services.ts`, component chỉ dùng kiểu `camelCase` trong `src/types/`.

## Thư mục `src/mock/` (không thuộc runtime)

`mockApi.ts` là tàn dư giai đoạn demo UI trước khi có backend, hiện không được import
ở bất kỳ luồng chạy nào. Giữ lại chỉ để tham khảo lịch sử, nên xóa trước khi niêm phong
(xem danh sách dọn dẹp ở tài liệu gốc).
