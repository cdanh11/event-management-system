# Kiến trúc frontend

Luồng dữ liệu: Page → hook/context → service → apiClient → FastAPI.

| Thành phần | Trách nhiệm |
| --- | --- |
| src/app/App.tsx | Routes lazy, AppShell và RoleGuard |
| src/hooks/useQuery.ts | Loading/error, giữ dữ liệu khi refetch, hủy request cũ và polling |
| src/features/auth/ | User/session, restore, login/register/logout |
| src/services/services.ts | Endpoint và mapping snake_case API → camelCase UI |
| src/api/apiClient.ts | Bearer, refresh cookie single-flight và ApiError |
| src/realtime/socket.ts, useOccupancy.ts | Room, WS ticket, reconnect và REST fallback |
| src/lib/ | Thời gian, trạng thái, điều hướng và lỗi dùng chung |
| src/features/ | Logic vé, cửa, organizer, event và phiên live |
| src/components/ui/ | Form, xác nhận, trạng thái tải/lỗi và các phần hiển thị dùng chung |
| src/copy/strings.ts | Nội dung giao diện tiếng Anh tập trung |
| src/styles/ | CSS theo chức năng; font local ở public/fonts |

UI không fetch trực tiếp. Quyền frontend giúp chọn thao tác phù hợp; backend luôn kiểm tra quyền trước khi đọc/ghi. Không có mock API trong runtime. Event start/end là giờ địa phương; timestamp audit là UTC, được chuẩn hóa riêng trong service.
