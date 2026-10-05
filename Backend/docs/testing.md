# Kiểm thử backend

## Lệnh chạy

```powershell
cd Backend
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term
```

Hiện tại: **52 passed + 1 skipped**, coverage **~88%**.

## Chiến lược hai tầng

| Tầng | Công cụ | Mục đích |
| --- | --- | --- |
| API/Unit (mặc định, chạy trong CI) | `TestClient` + SQLite in-memory qua `dependency_overrides[get_db]` | Nhanh: auth, 401/403, 422, ownership, vòng đời event, booking/cancel, capacity, check-in một lần, notify async, WS ticket handshake |
| PostgreSQL thật (chạy tay, skip mặc định) | `tests/test_concurrency_pg.py` với `TEST_POSTGRES_URL` | Chứng minh row lock `FOR UPDATE` mà SQLite không thể hiện được |

## Quy ước viết test

- Fixture `auth_headers(role, email)` tạo user + login qua API thật, không "giả token".
- Monkeypatch task nền khi cần assert tác vụ sau response
  (ví dụ `test_register_sends_ticket_in_background`).
- Mỗi bug nghiêm trọng đều có test hồi quy đi kèm (422 crash handler, drift migration,
  thứ tự dọn FK trong test concurrency).

## CI

`.github/workflows/ci.yml` chạy mỗi push: backend `pytest --cov` và frontend `npm run lint` + `npm run build`.
