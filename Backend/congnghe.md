# Cong nghe FastAPI trong Evently

Tai lieu nay mo ta nhung cong nghe dang duoc dung trong code backend va cach chung minh tung yeu cau khi demo. FastAPI la cong nghe trung tam; React chi la client goi API.

## Kien truc

```text
HTTP client / React / Swagger
          |
       FastAPI app
          |
 routers -> dependencies -> services -> SQLAlchemy -> PostgreSQL
          |
 Pydantic request validation / response serialization
```

| Thanh phan | File chinh | Trach nhiem |
| --- | --- | --- |
| App, middleware, OpenAPI | `app/main.py` | Khoi tao FastAPI va contract toan cuc |
| Settings | `app/config.py` | Doc `.env` mot lan |
| Database dependency | `app/db.py` | Engine, SessionLocal, `get_db()` |
| ORM | `app/models.py` | 7 bang SQLAlchemy |
| Pydantic | `app/schemas.py` | Request, response, enum va error schema |
| Auth/RBAC | `app/deps.py`, `app/security.py` | JWT, Bearer, role dependency |
| Business endpoints | `app/routers/` | Event, registration, ticket, check-in, staff |
| Notify service | `app/services/notifier.py` | Async HTTP webhook/simulated I/O |
| Migration | `alembic/` | Version schema PostgreSQL |
| Test | `tests/` | TestClient va dependency override |

## Tang 1A - FastAPI core

### 1. Pydantic va API contract

`app/schemas.py` tach model dau vao va dau ra:

- `EventIn`, `EventUpdateIn`, `EventOut`.
- `LoginIn`, `TokenOut`, `UserOut`.
- `RegistrationOut`, `TicketOut`, `CheckinIn`, `CheckinOut`.
- `NotifyOut`, `ApiErrorOut`, `ValidationErrorOut`.

Validation co `Field(min_length=...)`, `Field(gt=0)`, `EmailStr` va `model_validator(mode="after")`
cho quan he start/end (Phase 1). Payload sai bi FastAPI/Pydantic chan truoc khi endpoint chay,
sau do `validation_error_handler` tai `app/main.py` (sanitize `ctx.error` bang `jsonable_encoder`)
tra 422 theo dang:

```json
{
  "status": 422,
  "code": "VALIDATION_ERROR",
  "message": "Request payload is invalid",
  "details": []
}
```

`EventStatus` va `NotifyMode` la `str, Enum`; Swagger hien dung gia tri hop le thay vi string tu do.

### 2. Dependency system

`get_db()` trong `app/db.py` yield mot SQLAlchemy `Session` cho moi request va dong sau khi response xong.

```text
require("ORGANIZER")
  -> current_user
      -> HTTPBearer
      -> get_db
```

- `current_user`: decode JWT va nap User; loi 401 neu token thieu/sai.
- `require(*roles)`: factory dependency; loi 403 neu role khong duoc phep.
- Ownership duoc kiem tra trong router, vi du organizer chi sua/notify Event cua minh.

`settings` trong `app/config.py` la config singleton, khong phai FastAPI dependency. Phan biet nay can duoc noi dung khi bao cao.

### 3. Sync va async dung cho

Database dang dung SQLAlchemy sync, nen endpoint query/commit DB duoc viet bang `def`. FastAPI chay cac handler sync nay trong threadpool, tranh block event loop.

`POST /events/{event_id}/notify` la `async def` vi cong viec cua handler la network I/O awaitable:

1. `_notification_target` la sync dependency, xu ly auth, ownership va doc recipient tu DB.
2. Handler async chi `await notify_attendees(...)`.
3. `notify_attendees` dung `httpx.AsyncClient` khi co `NOTIFY_WEBHOOK_URL`; neu khong co thi `asyncio.sleep` mo phong I/O.

Khi Event chuyen `COMPLETED`, `BackgroundTasks` gui notify sau response. Khi register thanh cong,
`BackgroundTasks` gui ve/QR (`send_ticket_email`) sau response — chi truyen kieu nguyen thuy (str),
cam cham ORM vi Session da dong. Day la cong viec ngan; khong phai queue retry/phan tan.

Realtime WS dung ticket handshake mot lan (`POST /ws/ticket` -> `?ticket=` 30s); JWT khong bao
gio di tren query string. `httpx` dung shared `AsyncClient` (connection pooling), dong o lifespan
shutdown. Thoi gian DB thong nhat naive-UTC qua `models.utcnow()`. Toan bo gioi han va quyet dinh
400/422: `../docs/gioi-han-ky-thuat.md` (nguyen lieu Chuong 13).

## Tang 1B - FastAPI mo rong

### OpenAPI

Swagger tai `GET /docs`, schema tai `GET /openapi.json`.

- `response_model` gan tren endpoint de loc response va sinh schema.
- Tags chia `auth`, `events`, `registrations`, `tickets`, `checkins`, `staff`, `assignments`, `system`.
- `HTTPBearer` duoc FastAPI suy ra tu dependency graph.
- `app/main.py` bo sung security scheme nhung khong gan `security` toan cuc. Vi vay `POST /auth/login`, `POST /auth/refresh`, `GET /events`, `GET /health` van la public trong Swagger; `GET /auth/me` va endpoint phan quyen co Bearer requirement.
- `ValidationErrorOut` duoc gan o router level cho response 422, phu hop body loi custom cua app.

Error nghiep vu chay runtime theo dang `ApiErrorOut`: `{status, code, message}`. Trong buoc hoan thien sau, co the khai bao them `responses={...}` rieng cho 401/403/404/409 o cac endpoint quan trong de Swagger chi tiet hon.

### Exception handler

`app/main.py` co hai handler:

- `HTTPException` chuan hoa loi nghiep vu 401, 403, 404, 409 va 400.
- `RequestValidationError` chuan hoa Pydantic 422 va giu `details` theo field.

### Middleware va lifespan

- `CORSMiddleware`: cho frontend local gui cookie refresh token.
- `TimingLoggingMiddleware`: log thoi gian request.
- `lifespan`: log startup/shutdown va `engine.dispose()` khi tat app.

## Du lieu va nghiep vu

- SQLAlchemy 2 ORM trong `app/models.py` co 7 bang.
- Alembic migration `0001_initial_schema` tao schema.
- `app/seed.py` nap user, Event, staff assignment va ve demo.
- Dang ky su dung `with_for_update()` tren Event va unique `(event_id, attendee_id)` de chong over-booking/duplicate registration o PostgreSQL.
- State machine Event: `DRAFT -> PUBLISHED -> ONGOING -> COMPLETED`; `DRAFT/PUBLISHED -> CANCELLED`.

## Tang 2 - Ky nghe phan mem

| Noi dung | Minh chung |
| --- | --- |
| Config/secrets local | `.env.example`, `app/config.py` |
| Tai lap DB | `../compose.yaml` |
| Schema versioned | `alembic/`, `alembic.ini` |
| Du lieu demo | `app/seed.py` |
| API test | `tests/`, TestClient |
| Dependency override | `tests/conftest.py` thay `get_db` bang SQLite memory |
| Coverage | `pytest-cov` trong `requirements.txt` |
| CI | `../.github/workflows/ci.yml` |
| Huong dan chay | `../readme.md`, `README.md` |

Bo test hien kiem tra login, refresh/logout, 401/403, 422, ownership, lifecycle Event, registration/cancel, full capacity, check-in va notify. SQLite cho test nhanh; `FOR UPDATE` can them integration test PostgreSQL o Tang 3 de chung minh concurrency that.

## Cach demo FastAPI

1. Mo `/docs`, goi `POST /auth/login` bang organizer va lay `access_token`.
2. Bam **Authorize**, dan token vao HTTP Bearer.
3. Goi `POST /events`, sau do `POST /events/{id}/transition` voi `PUBLISHED`.
4. Login attendee, dang ky qua `POST /events/{id}/register` va lay ticket.
5. Login staff duoc phan cong, goi `POST /checkins`.
6. Login organizer, goi `PATCH /events/{id}` va `POST /events/{id}/notify`.
7. Thu body sai de xem 422, token thieu de xem 401, sai role de xem 403 va dang ky lap de xem 409.

## Gioi han hien tai va huong Tang 3

- `GET /events` co offset pagination (Phase 1); cursor pagination + benchmark voi dataset lon o Phase 2.
- Search `ILIKE('%q%')` chua duoc toi uu bang index/full-text search.
- Notify chua co retry, outbox hay queue that.
- Chua co PostgreSQL concurrency test cho `FOR UPDATE`.

Tang 3 se tap trung cursor pagination, composite index va `EXPLAIN ANALYZE`, khong mo rong sang microservice hay queue.
