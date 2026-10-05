# Roadmap Evently (đồ án đã hoàn thành code)

## Mục tiêu

Hoàn thiện đồ án **Tìm hiểu và xây dựng dịch vụ Backend với FastAPI — Evently**.
Ưu tiên minh chứng FastAPI (Tầng 1/2/3 theo danh mục môn học), không mở rộng sản phẩm
ngoài phạm vi quản lý sự kiện. Phần việc còn lại: ảnh/video demo, báo cáo, lab/slide
và niêm phong.

## Hiện trạng (cuối Phase 2 + đợt fix hội đồng)

| Hạng mục | Trạng thái |
| --- | --- |
| Pydantic request/response, validation 422 | Hoàn thành |
| `Depends`, JWT, RBAC, ownership | Hoàn thành |
| SQLAlchemy sync + async network I/O đúng chỗ | Hoàn thành |
| OpenAPI, Bearer scheme, enum contract, error responses 401/403/404/409/422 | Hoàn thành |
| Middleware, lifespan, exception handler, BackgroundTasks | Hoàn thành |
| PostgreSQL, Alembic (0001–0002), seed, Docker Compose | Hoàn thành |
| Pytest/TestClient/dependency override | Hoàn thành: **52 passed + 1 skipped** (PG), coverage **~88%** |
| CI GitHub Actions | Hoàn thành |
| WebSocket realtime occupancy + dashboard `/organizer/live` (ticket handshake) | Hoàn thành (Phase 0) |
| Pydantic 422 cho start/end, pagination, DELETE, Swagger errors | Hoàn thành (Phase 1) |
| BackgroundTask khi register, cursor/index/benchmark, concurrency test PG thật | Hoàn thành (Phase 2) |
| Báo cáo toàn văn (DRAFT), ERD, ảnh minh chứng | Hoàn thành bản nháp, chờ duyệt nội dung |
| Lab, slide, video demo, niêm phong commit | Còn lại (Phase 3) |

## Phạm vi kỹ thuật (đã thực hiện)

### Tầng 1A bắt buộc

1. Pydantic: schema input/output, validation và error 422 (`model_validator` cho quan hệ start/end).
2. Dependency: `get_db`, `current_user`, `require(*roles)` + ownership theo organizer.
3. Async đúng chỗ: endpoint SQLAlchemy sync giữ `def`; chỉ notify/WS/notifier dùng `async` cho network I/O.

### Tầng 1B đã dùng

1. `response_model`, OpenAPI tags, HTTP Bearer (chỉ gắn operation cần auth), `responses={401,403,404,409}`.
2. Exception handler tập trung (`{status, code, message}`; 422 kèm `details`).
3. CORS + `TimingLoggingMiddleware` tự viết.
4. Lifespan: dispose engine + đóng shared `httpx.AsyncClient` khi shutdown.
5. BackgroundTasks: gửi vé/QR sau `201` register, notify khi `COMPLETED` (task ngắn, không retry).
6. TestClient + dependency override (SQLite) + test concurrency trên PostgreSQL thật.

### Tầng 2

1. Git history theo nhánh `feature/*`, README và `.env.example`.
2. Docker Compose tái lập PostgreSQL (+ pgAdmin profile `tools`).
3. Alembic migration versioned (`0001`–`0002`) và seed demo.
4. pytest + coverage, frontend lint/build, CI GitHub Actions.

### Tầng 3 đã chọn

**Tối ưu truy vấn PostgreSQL (C2.1) + realtime phía máy chủ (C2.3):** cursor pagination,
composite index `ix_events_status_start_time`, `EXPLAIN ANALYZE` + benchmark
(index ~12.5x, cursor ~2.1x trên 3000 rows), concurrency test `FOR UPDATE`
(`[201, 409×4]`), WebSocket occupancy + ticket handshake một lần.

## Lộ trình phase (0 → niêm phong)

| Phase | Nội dung | Điều kiện review xong |
| --- | --- | --- |
| Phase 0 (xong) | WebSocket realtime occupancy + dashboard `/organizer/live`, broadcast khi register/cancel | Demo 2 trình duyệt số tự nhảy. Chi tiết: `phase-0-websocket.md` |
| Phase 1 (xong) | Contract & validation: Pydantic `model_validator` start/end → 422; pagination `GET /events?limit&offset`; `DELETE /events/{id}` chỉ cho DRAFT; Swagger `responses={401,403,404,409}` | Swagger check xong. Chi tiết: `phase-1-contract.md` |
| Phase 2 (xong) | Background & T3: BackgroundTask gửi vé/QR khi register; cursor pagination + composite index + `EXPLAIN ANALYZE` + benchmark; concurrency test `FOR UPDATE` trên PostgreSQL thật | Index ~12.5x, cursor ~2.1x; concurrency `[201,409×4]`. Chi tiết: `phase-2-perf.md` |
| Fix hội đồng (xong) | `POST /auth/register` + FE signup; dashboard `func.count()`; chặn register event quá hạn; WS ticket handshake; shared httpx client; `utcnow()`; `gioi-han-ky-thuat.md` | `52 passed + 1 skipped`, coverage 88% |
| Phase 3 (đang làm) | Báo cáo toàn văn (DRAFT), lab, slide, niêm phong commit trước bảo vệ ≥ 24h | Checklist hồ sơ nộp bài đầy đủ (xem báo cáo DRAFT) |

Mỗi phase có đúng một file review (`phase-N-*.md`); chỉ sang phase sau khi review xong.

## Kế hoạch 14 ngày (đã thực hiện — giữ lại để đối chiếu weekly log)

| Ngày | Công việc | Đầu ra/minh chứng |
| --- | --- | --- |
| 1 | Chốt scope, Compose, env, migration, seed | README và ảnh DB/Swagger |
| 2 | Rà soát Pydantic, dependency, auth/RBAC | Bảng phủ Tầng 1 và test 401/403/422 |
| 3 | Hoàn thiện OpenAPI enum, security, error contract | Swagger public/protected đúng |
| 4 | Rà soát sync/async Notify và BackgroundTasks | Sequence Create–Complete–Notify |
| 5 | Hoàn thiện frontend E2E, mapping API | Demo đăng ký, vé, check-in, reschedule |
| 6 | Chốt baseline Tầng 1–2, CI | CI xanh, test/build pass |
| 7 | Thiết kế Tầng 3: filter, cursor và index | Query baseline và dataset benchmark |
| 8 | Implement pagination/cursor endpoint | API contract và test pagination |
| 9 | Tạo migration composite index | `EXPLAIN ANALYZE` trước/sau |
| 10 | Chạy benchmark PostgreSQL thật | Bảng latency, query plan, kết luận |
| 11 | Thêm integration/concurrency test PostgreSQL | Minh chứng `FOR UPDATE` chống over-booking |
| 12 | Vẽ ERD, dependency graph, state machine | Ảnh cho Chương 3, 4, 11 (`assets/`) |
| 13 | Viết lab 30–45 phút và báo cáo | Lab Pydantic + Depends + TestClient |
| 14 | Regression test, slide, video, đóng băng commit | Checklist nộp bài và commit hash |

## Tiêu chí đóng băng (đã đạt ở mức code)

- `python -m pytest --cov=app --cov-report=term` pass (52 passed + 1 skipped, ~88%).
- `npm run lint` và `npm run build` pass.
- `docker compose config` pass.
- Swagger mở được; endpoint public không yêu cầu Bearer, endpoint private có Bearer.
- README hướng dẫn máy mới chạy được PostgreSQL, migration, seed, backend và frontend.
- CI chạy cùng các lệnh kiểm tra trên.

## Ranh giới cần giải thích trong báo cáo

Chi tiết đầy đủ đã chuyển vào [`gioi-han-ky-thuat.md`](gioi-han-ky-thuat.md)
(nguyên liệu Chương 13). Tóm tắt:

- SQLite test chỉ cho unit/API nhanh; row lock `FOR UPDATE` chứng minh bằng test PostgreSQL.
- `BackgroundTasks` chỉ cho task ngắn sau response; không retry/outbox/queue phân tán.
- `NOTIFY_WEBHOOK_URL` chưa phải email production; WebSocket in-memory single-node.
- Secret/password mặc định trong Compose chỉ cho local development.
