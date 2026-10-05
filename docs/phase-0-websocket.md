# Phase 0 — WebSocket realtime dashboard (đã xong, chờ review)

## Mục tiêu phase 0
- Admin mở `/organizer/live`, Attendee đăng ký vé → số **Remaining tự nhảy**, không reload.
- Chứng minh FastAPI WebSocket + broadcast + auth query-token + test WS.

## Đã làm
- Backend:
  - `Backend/app/realtime.py` — `ConnectionManager` theo room `event_id`, `occupancy_payload` chuẩn.
  - `Backend/app/routers/realtime.py` — `GET /events/{id}/occupancy` (ORGANIZER) + `WS /ws/events/{id}?token=`.
  - `registrations.py` — `register`/`cancel` broadcast occupancy qua `BackgroundTasks` sau commit.
  - `tests/test_realtime.py` — snapshot REST + WS nhận broadcast khi đăng ký + từ chối thiếu token.
- Frontend:
  - `src/api/apiClient.ts` — thêm `getAccessToken()`, `wsBaseUrl()`.
  - `src/realtime/useOccupancySocket.ts` — hook socket: snapshot đầu, reconnect backoff, phân biệt mã lỗi 4401/4403/4404.
  - `src/features/realtime/LiveDashboard.tsx` — UI tách khỏi logic socket để sau này áp theme promax.
  - Route `/organizer/live` + nav `Live` trong `App.tsx`.

## Cách review (5 phút)
1. Backend: `cd Backend; .\.venv\Scripts\python.exe -m pytest -q` → kỳ vọng **37 passed**.
2. Frontend: `cd Frontend; npm run lint; npm run build` → kỳ vọng sạch + build pass.
3. Manual 2 trình duyệt:
   - Browser A (ORGANIZER): login → `/organizer/live` → thấy `LIVE` + snapshot.
   - Browser B (ATTENDEE): đăng ký 1 vé event đang xem → Browser A số Remaining tự giảm.
   - Cancel vé → số tự tăng lại.

## Giới hạn đã biết (ghi vào báo cáo Chương 13)
- Broadcast in-memory, single-process. Đa worker/instance cần Redis pub/sub (phase Tầng 3 C2.3).
- WS auth bằng query token; chưa có refresh tự động trong socket — token hết hạn thì reconnect với token mới.

## Về repo uiux promax (chưa thấy trong máy)
- Tôi đã quét `D:\`, `D:\S1Y4\CNLTHD`, `D:\Project`, `D:\App`, `D:\portfolio` — **chưa thấy thư mục promax**.
- Khi bạn đưa đường dẫn/link, tôi đánh giá theo 4 điểm: stack (React/Tailwind?), component sẵn (card/metric/select), router/theme, xung đột CSS/auth.
- Chiến lược tích hợp an toàn: **theme-first** — giữ nguyên `useOccupancySocket` + route, chỉ thay JSX trong `LiveDashboard.tsx` bằng component promax; `services.ts`/`apiClient.ts` giữ nguyên.

## Roadmap các phase tiếp theo (mỗi phase review 1 lần)
- **Phase 1 — Contract & validation:** Pydantic `model_validator` cho start/end → 422; pagination `GET /events`; quyết định DELETE event; bổ sung `responses={401,403,404,409}` Swagger. Review: pytest + Swagger check.
- **Phase 2 — Background & Tầng 3:** BackgroundTask gửi vé/QR khi register; cursor pagination + index + `EXPLAIN ANALYZE` + benchmark; concurrency test `FOR UPDATE`. Review: số liệu trước/sau.
- **Phase 3 — Báo cáo & niêm phong:** Chương 11 (use case/ERD/API spec), Chương 12 + Bảng phủ, Chương 13-14 + AI Disclosure, lab/slide/video, commit hash.
