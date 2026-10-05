# Realtime occupancy qua WebSocket

Dashboard organizer (`/organizer/live`) hiển thị số vé còn lại **tự nhảy số** khi có
đăng ký/hủy, không cần tải lại trang.

## Thiết kế

```text
Attendee POST /events/{id}/register (commit xong)
        |
        +-- BackgroundTasks --> manager.broadcast_occupancy(event_id, payload)
        |
Room event_id: { WS_admin_1, WS_admin_2, ... }  <-- dict[event_id, set[WebSocket]]
```

- Mỗi sự kiện là một room. Client kết nối nhận **snapshot đầu tiên** để vẽ ngay,
  các message sau là cập nhật occupancy `{capacity, registered_count, remaining, status}`.
- `register`/`cancel` đẩy broadcast qua `BackgroundTasks` sau commit: response `201`
  về ngay trong vài ms, việc đẩy tin không chặn request.

## Ticket handshake (xác thực WS)

JWT không bao giờ đi trên query string (dính log proxy, header `Referer`, history).
Luồng chuẩn:

1. Client gọi `POST /ws/ticket` kèm header `Authorization` (chỉ `ORGANIZER`).
2. Server cấp ticket 30 giây, **dùng một lần duy nhất**.
3. Client mở `WS /ws/events/{event_id}?ticket=...`.

| Mã đóng | Ý nghĩa |
| --- | --- |
| `4401` | Ticket sai/hết hạn/đã dùng lại (chống replay) |
| `4403` | Sai role |
| `4404` | Event không tồn tại |

Test bao phủ: snapshot + broadcast khi đăng ký (`test_occupancy_snapshot_and_ws_broadcast`),
dùng lại ticket (`test_ws_ticket_one_time_use`), cấp ticket sai quyền.

## Minh chứng async đúng chỗ

- Endpoint DB dùng SQLAlchemy **sync** nên khai báo `def` (FastAPI chạy trong threadpool).
- Chỉ `POST /events/{id}/notify`, notifier và WS dùng `async`: công việc duy nhất là
  network I/O awaitable (`httpx.AsyncClient` hoặc `asyncio.sleep` mô phỏng).
- `httpx` dùng **shared `AsyncClient`** (connection pooling), đóng ở lifespan shutdown.

## Giới hạn đã biết

`ConnectionManager` giữ kết nối trong RAM tiến trình (single-node): chạy
`uvicorn --workers 4` thì client ở worker khác không nhận broadcast. Hướng mở rộng:
Redis Pub/Sub (worker publish, mọi worker subscribe rồi đẩy tới room của mình).
Chi tiết đầy đủ xem `docs/gioi-han-ky-thuat.md` ở thư mục `docs/` gốc.
