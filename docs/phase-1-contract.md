# Phase 1 — Contract & validation (đã xong, chờ review)

## Mục tiêu phase 1
- Pydantic chặn `end <= start` → **422**, không còn `400` cho case này.
- `GET /events` có **pagination** `limit/offset`.
- Quyết định **DELETE event**: chỉ DRAFT của chính chủ; đã publish thì dùng CANCELLED.
- Swagger mô tả **error responses** cho endpoint quan trọng.

## Đã làm
- Backend:
  - `app/schemas.py` — `model_validator(mode="after")` trên `EventIn` (full payload) và
    `EventUpdateIn` (khi gửi cả 2 mốc); shared `ERROR_401/403/404/409`, `AUTH_RESPONSES`.
  - `app/main.py` — handler 422 sanitize `ctx.error` bằng `jsonable_encoder(...,
    custom_encoder={ValueError: str})`; nếu không, chính handler 422 crash thành 500.
  - `app/routers/events.py` — `GET /events?limit&offset` (1–100/0+), `DELETE /events/{id}`
    (204, chỉ DRAFT + chính chủ, else `400 EVENT_NOT_DELETABLE`), `responses={401,403,404}`
    cho create/patch/delete/transition/notify.
  - `app/routers/registrations.py` — `POST register` có `responses={401,403,404,409}`.
  - `app/routers/realtime.py` — `GET occupancy` có `responses={401,403,404}`.
  - Rule "start phải ở tương lai" giữ nguyên `400 INVALID_EVENT_TIME` (nghiệp vụ, cần `now()`).
- Frontend:
  - `services.ts` — `getEvents(limit, offset)`, `remove(id)` DELETE.
  - `App.tsx` — ManageEvent có nút **Delete draft** (DRAFT only, confirm rồi về `/organizer`).
- Test (`tests/test_events.py`): `test_create_event_end_before_start_422`,
  `test_create_event_past_start_400`, `test_reschedule_end_before_start_422`,
  `test_list_events_pagination` (kèm `limit=0 → 422`), `test_delete_event_draft_only`,
  `test_openapi_error_contract_phase1` (409 register, 401/403/404 delete, params limit/offset).

## Cách review (5 phút)
1. Backend: `cd Backend; .\.venv\Scripts\python.exe -m pytest -q` → kỳ vọng **42 passed**.
2. Swagger `/docs`: `POST /events` body end<start → 422; `GET /events` có limit/offset;
   `DELETE /events/{id}` hiện 401/403/404; `POST register` hiện 409.
3. Frontend: `npm run lint; npm run build` → sạch + pass; ManageEvent DRAFT có nút Delete.

## Lỗi gặp trong phase (ghi vào Chương 13)
- Handler 422 crash `TypeError: ValueError is not JSON serializable` vì `exc.errors()` chứa
  `ctx.error` là exception object. Sửa bằng `jsonable_encoder` + custom encoder. Đây là ca
  minh chứng "Pydantic error shape thay đổi khi dùng model_validator".

## Giới hạn còn lại → Phase 2
- Pagination mới là offset/limit; cursor + index + benchmark ở Phase 2 (Tầng 3).
- `BackgroundTasks` khi register (gửi vé/QR) ở Phase 2.
- Concurrency test `FOR UPDATE` trên PostgreSQL thật ở Phase 2.
