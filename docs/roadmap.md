# Roadmap Evently

## Muc tieu

Hoan thien do an **Tim hieu va xay dung dich vu Backend voi FastAPI - Evently** trong 2 tuan. Uu tien la minh chung FastAPI, khong mo rong san pham qua pham vi quan ly su kien.

## Hien trang

| Hang muc | Trang thai |
| --- | --- |
| Pydantic request/response, validation 422 | Hoan thanh |
| `Depends`, JWT, RBAC, ownership | Hoan thanh |
| Sync SQLAlchemy va async network I/O | Hoan thanh baseline |
| OpenAPI, Bearer scheme, enum contract, 422 response schema | Hoan thanh baseline |
| Middleware, lifespan, exception handler, BackgroundTasks | Hoan thanh |
| PostgreSQL, Alembic, seed, Docker Compose | Hoan thanh |
| Pytest/TestClient/dependency override | Hoan thanh; 52 passed + 1 skipped PG (sau dot fix hoi dong) |
| CI GitHub Actions | Hoan thanh baseline |
| WebSocket realtime occupancy + dashboard `/organizer/live` | Hoan thanh (Phase 0) |
| Pydantic 422 cho start/end, pagination, DELETE, Swagger errors | Phase 1 (dang lam) |
| BackgroundTask khi register, cursor/index/benchmark, concurrency test PG that | Hoan thanh (Phase 2) |
| ERD, bao cao Ch.11-14, lab, slide, video, niêm phong | Phase 3 (chua bat dau) |

## Pham vi ky thuat

### Tang 1A bat buoc

1. Pydantic: schema input/output, validation va error 422.
2. Dependency: `get_db`, `current_user`, `require(*roles)`.
3. Async dung cho notify webhook; endpoint SQLAlchemy sync giu `def`.

### Tang 1B dang dung

1. `response_model`, OpenAPI tags va HTTP Bearer security.
2. Exception handler tap trung.
3. CORS va timing/logging middleware.
4. Lifespan dong SQLAlchemy engine khi shutdown.
5. BackgroundTasks khi Event `COMPLETED`.
6. TestClient va dependency override.

### Tang 2

1. Git history, README va `.env.example`.
2. Docker Compose de tai lap PostgreSQL.
3. Alembic migration va seed demo.
4. pytest, coverage, frontend lint/build.
5. GitHub Actions CI.

### Tang 3 se chon

**Toi uu truy van PostgreSQL: cursor pagination, composite index, EXPLAIN ANALYZE va benchmark.**

Ly do: lien ket truc tiep voi `GET /events`, PostgreSQL va SQLAlchemy; de do duoc truoc/sau; khong lam lech trong tam FastAPI sang microservice hay queue.

## Lo trinh phase (0 -> niem phong)

| Phase | Noi dung | Dieu kien review xong |
| --- | --- | --- |
| Phase 0 (xong) | WebSocket realtime occupancy + dashboard `/organizer/live`, broadcast khi register/cancel | `37 passed`, FE lint/build pass, demo 2 browser so tu nhay. Chi tiet: `docs/phase-0-websocket.md` |
| Phase 1 (xong) | Contract & validation: Pydantic `model_validator` start/end -> 422; pagination `GET /events?limit&offset`; `DELETE /events/{id}` chi cho DRAFT; Swagger `responses={401,403,404,409}` cho endpoint quan trong | `42 passed`, coverage 87%, FE lint/build pass, Swagger check xong. Chi tiet: `docs/phase-1-contract.md` |
| Phase 2 (xong) | Background & T3: BackgroundTask gui ve/QR khi register; cursor pagination + composite index + `EXPLAIN ANALYZE` + benchmark; concurrency test `FOR UPDATE` tren PostgreSQL that | `44 passed + 1 skipped`, coverage 87%; index ~12.5x, cursor ~2.1x; concurrency `[201,409x4]` pass 2 lan. Chi tiet: `docs/phase-2-perf.md` |
| Fix hoi dong (xong) | POST /auth/register + FE signup; dashboard `func.count()`; chan register event qua han; WS ticket handshake; shared httpx client; `utcnow()`; `docs/gioi-han-ky-thuat.md` (nguyen lieu Chuong 13) | `52 passed + 1 skipped`, coverage 88%, FE lint/build pass |
| Phase 3 | Bao cao & niem phong: Chuong 11 (use case/ERD/API spec), Chuong 12 + Bang phu ky thuat, Chuong 13-14 + AI Disclosure, lab/slide/video, commit hash truoc bao ve >= 24h | Checklist ho so nop bai day du |

Moi phase co file review rieng (`docs/phase-N-*.md`); chi sang phase sau khi review phase truoc xong.

## Ke hoach 14 ngay (tham khao)

| Ngay | Cong viec | Dau ra/minh chung |
| --- | --- | --- |
| 1 | Chot scope, Compose, env, migration, seed | README va anh DB/Swagger |
| 2 | Ra soat Pydantic, dependency, auth/RBAC | Bang phu Tang 1 va test 401/403/422 |
| 3 | Hoan thien OpenAPI enum, security, error contract | Swagger public/protected dung |
| 4 | Ra soat sync/async Notify va BackgroundTasks | Sequence Create-Complete-Notify |
| 5 | Hoan thien frontend E2E, mapping API | Demo dang ky, ve, check-in, reschedule |
| 6 | Chot baseline Tang 1-2, CI | CI xanh, test/build pass |
| 7 | Thiet ke T3: filter, cursor va index | Query baseline va dataset benchmark |
| 8 | Implement pagination/cursor endpoint | API contract va test pagination |
| 9 | Tao migration composite index | `EXPLAIN ANALYZE` truoc/sau |
| 10 | Chay benchmark PostgreSQL that | Bang latency, query plan, ket luan |
| 11 | Them integration/concurrency test PostgreSQL | Minh chung `FOR UPDATE` chong over-booking |
| 12 | Ve ERD, dependency graph, state machine | Anh cho Chuong 3, 4, 11 |
| 13 | Viet lab 30-45 phut va bao cao | Lab Pydantic + Depends + TestClient |
| 14 | Regression test, slide, video, dong bang commit | Checklist nop bai va commit hash |

## Tieu chi dong bang base Tang 1-2

- `python -m pytest --cov=app --cov-report=term` pass.
- `npm run lint` va `npm run build` pass.
- `docker compose config` pass.
- Swagger mo duoc; endpoint public khong co Bearer requirement, endpoint private co Bearer requirement.
- README huong dan mot may moi chay duoc PostgreSQL, migration, seed, backend va frontend.
- CI chay cung cac lenh kiem tra tren.

## Ranh gioi can giai thich trong bao cao

- SQLite test chi dung cho unit/API test nhanh; row lock `FOR UPDATE` can PostgreSQL integration test de chung minh.
- `BackgroundTasks` chi phu hop notify ngan; khong co retry, outbox hay queue phan tan.
- `NOTIFY_WEBHOOK_URL` chua la dich vu email production.
- Secret/password mac dinh trong Compose chi phuc vu local development.
