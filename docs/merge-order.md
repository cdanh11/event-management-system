# Thứ tự merge source Evently

## Thứ tự merge sau khi sửa CI PR #10

| Thứ tự | PR/branch | Phạm vi |
| --- | --- | --- |
| 1 | Backend, PR #9 | Đã merge vào main |
| 2 | feature/uiux-v2-foundation, PR #10 | Frontend hoàn chỉnh: 20 commit từ foundation, attendee và operations |
| 3 | feature/uiux-v2-documentation | Tài liệu, ảnh minh chứng và hướng dẫn merge đã sửa |

Chọn **Create a merge commit**. Không cần mở/merge PR riêng cho attendee và operations: các commit của hai branch này đã nằm trong PR #10. Các branch riêng được giữ để tham chiếu phạm vi và lịch sử.

CI cũ của foundation lỗi do npm test trỏ tới file chưa có, đồng thời router tham chiếu các trang ở branch tiếp theo. Foundation đã fast-forward tới đầy đủ frontend, giữ từng commit theo chức năng; không skip test, không thêm placeholder và không tạo commit gộp. Tất cả bước npm ci/lint/test/audit-copy/build phải chạy trên branch này trước merge.

Branch documentation chứa toàn bộ source cuối trước khi main được merge. Integration là bản tổng hợp local. Báo cáo Word không sửa. Các mục dưới đây liệt kê file theo nhóm commit ban đầu, không còn là năm PR cần merge riêng.

## 1. feature/backend-realtime-lifecycle

Base ban đầu: `main`. Merge vào `main` sau các branch trước.

### chore(backend): pin dependencies and configure SMTP transport

- `Backend/.env.example`
- `Backend/app/config.py`
- `Backend/requirements.lock`
- `Backend/requirements.txt`

### fix(db): freeze migrations and normalize event timestamps

- `Backend/alembic/env.py`
- `Backend/alembic/versions/0001_initial_schema.py`
- `Backend/app/models.py`

### feat(auth): add OAuth2 login and numbered demo aliases

- `Backend/app/deps.py`
- `Backend/app/errors.py`
- `Backend/app/routers/auth.py`
- `Backend/app/schemas.py`
- `Backend/app/security.py`

### fix(booking): enforce ownership and transactional ticket invariants

- `Backend/app/access.py`
- `Backend/app/routers/checkins.py`
- `Backend/app/routers/registrations.py`
- `Backend/app/routers/tickets.py`

### feat(events): synchronize lifecycle and paginated realtime contracts

- `Backend/app/main.py`
- `Backend/app/realtime.py`
- `Backend/app/routers/events.py`
- `Backend/app/routers/realtime.py`
- `Backend/app/routers/staff.py`
- `Backend/app/services/lifecycle.py`

### feat(notifications): send ticket emails with QR attachments

- `Backend/app/services/notifier.py`

### feat(seed): add repeatable numbered accounts and event history

- `Backend/app/seed.py`
- `Backend/tests/test_seed.py`

### test(backend): cover auth lifecycle SMTP and PostgreSQL concurrency

- `Backend/tests/conftest.py`
- `Backend/tests/test_auth.py`
- `Backend/tests/test_checkins.py`
- `Backend/tests/test_concurrency_pg.py`
- `Backend/tests/test_events.py`
- `Backend/tests/test_final_review.py`
- `Backend/tests/test_lifecycle_auto.py`
- `Backend/tests/test_realtime.py`
- `Backend/tests/test_release.py`

### perf(events): benchmark indexes with rollback-safe fixtures

- `Backend/scripts/bench_events.py`
- `Backend/scripts/check_indexes.py`

### chore(backend): exclude local artifacts and remove obsolete cleanup tools

- `Backend/.coverage`
- `Backend/.gitignore`
- `Backend/scripts/check_bench_clean.py`
- `Backend/scripts/clean_race_leftovers.py`

### docs(backend): document final API behavior and reproducible checks

- `Backend/README.md`
- `Backend/docs/authentication.md`
- `Backend/docs/performance.md`
- `Backend/docs/realtime.md`
- `Backend/docs/testing.md`
- `Backend/docs/validation-errors.md`

## 2. feature/uiux-v2-foundation

Base backend đã merge. PR #10 bao gồm cả các nhóm attendee/operations bên dưới.

### chore(repo): exclude local files and configure PostgreSQL CI and Mailpit

- `.github/workflows/ci.yml`
- `.gitignore`
- `Frontend/.gitignore`
- `compose.yaml`

### build(frontend): streamline dependencies and lint source explicitly

- `Frontend/package-lock.json`
- `Frontend/package.json`
- `Frontend/postcss.config.js`
- `Frontend/scripts/audit-copy.mjs`
- `Frontend/tailwind.config.js`

### style(frontend): vendor fonts with licenses and theme tokens

- `Frontend/public/fonts/3y9H6as8bTXq_nANBjzKo3IeZx8z6up5BeSl5jBNz_19PpbpMXuECpwUxJBOm_OJWiawA1Xp.woff2`
- `Frontend/public/fonts/3y9H6as8bTXq_nANBjzKo3IeZx8z6up5BeSl5jBNz_19PpbpMXuECpwUxJBOm_OJWiawDFXplDs.woff2`
- `Frontend/public/fonts/3y9H6as8bTXq_nANBjzKo3IeZx8z6up5BeSl5jBNz_19PpbpMXuECpwUxJBOm_OJWiawDVXplDs.woff2`
- `Frontend/public/fonts/QdVMSTAyLFyeg_IDWvOJmVES_HTEJm81Rb0.woff2`
- `Frontend/public/fonts/QdVMSTAyLFyeg_IDWvOJmVES_HTEJm86Rb0bcw.woff2`
- `Frontend/public/fonts/QdVMSTAyLFyeg_IDWvOJmVES_HTEJm87Rb0bcw.woff2`
- `Frontend/public/fonts/QdVMSTAyLFyeg_IDWvOJmVES_HToIW81Rb0.woff2`
- `Frontend/public/fonts/QdVMSTAyLFyeg_IDWvOJmVES_HToIW86Rb0bcw.woff2`
- `Frontend/public/fonts/QdVMSTAyLFyeg_IDWvOJmVES_HToIW87Rb0bcw.woff2`
- `Frontend/public/fonts/QdVPSTAyLFyeg_IDWvOJmVES_Hw3BXo.woff2`
- `Frontend/public/fonts/QdVPSTAyLFyeg_IDWvOJmVES_Hw4BXoKZA.woff2`
- `Frontend/public/fonts/QdVPSTAyLFyeg_IDWvOJmVES_Hw5BXoKZA.woff2`
- `Frontend/public/fonts/bevietnampro-OFL.txt`
- `Frontend/public/fonts/bricolagegrotesque-OFL.txt`
- `Frontend/scripts/vendor-fonts.py`
- `Frontend/src/styles/fonts.css`
- `Frontend/src/styles/tokens.css`

### feat(frontend): centralize contracts copy dates and query state

- `Frontend/src/copy/strings.ts`
- `Frontend/src/hooks/useQuery.ts`
- `Frontend/src/lib/datetime.ts`
- `Frontend/src/lib/errors.ts`
- `Frontend/src/lib/navigation.ts`
- `Frontend/src/lib/status.ts`
- `Frontend/src/types/index.ts`

### fix(frontend): coordinate token refresh and API services

- `Frontend/src/api/apiClient.ts`
- `Frontend/src/features/auth/AuthContext.tsx`
- `Frontend/src/features/auth/authStore.ts`
- `Frontend/src/services/services.ts`

### feat(ui): add accessible forms dialogs and feedback primitives

- `Frontend/src/components/ui/Button.tsx`
- `Frontend/src/components/ui/Modal.tsx`
- `Frontend/src/components/ui/PageHeader.tsx`
- `Frontend/src/components/ui/Tabs.tsx`
- `Frontend/src/components/ui/Toast.tsx`
- `Frontend/src/components/ui/forms.tsx`
- `Frontend/src/components/ui/states.tsx`

### feat(ui): add event ticket and occupancy display components

- `Frontend/src/components/ui/Agenda.tsx`
- `Frontend/src/components/ui/ConnectionIndicator.tsx`
- `Frontend/src/components/ui/Countdown.tsx`
- `Frontend/src/components/ui/DoorCounter.tsx`
- `Frontend/src/components/ui/DoorStatus.tsx`
- `Frontend/src/components/ui/OrganizerAgenda.tsx`
- `Frontend/src/components/ui/QRCodeView.tsx`
- `Frontend/src/components/ui/RelativeTime.tsx`

### feat(auth-ui): support numbered demo sign-in and role navigation

- `Frontend/src/pages/Login.tsx`
- `Frontend/src/pages/Register.tsx`
- `Frontend/src/pages/errors.tsx`

### refactor(frontend): wire desktop shell and lazy role routes

- `Frontend/index.html`
- `Frontend/src/app/App.tsx`
- `Frontend/src/components/layout/AppShell.tsx`
- `Frontend/src/main.tsx`
- `Frontend/src/styles/globals.css`

### chore(frontend): remove unused mock data and async wrapper

- `Frontend/src/hooks/useAsync.ts`
- `Frontend/src/mock/data.ts`
- `Frontend/src/mock/mockApi.ts`

### chore(review): retain scoped worktree synchronization utility

- `tools/sync_review_worktrees.py`

### fix(deps): patch source-map-js denial-of-service advisory

- `Frontend/package-lock.json`

## 3. feature/uiux-v2-attendee

Các commit này đã được bao gồm trong PR #10; không cần PR riêng.

### feat(events-ui): add filtered agendas and event cache helpers

- `Frontend/src/features/events/agenda.ts`
- `Frontend/src/features/events/eventCache.ts`
- `Frontend/src/features/events/organizer.ts`

### feat(attendee): complete discovery and event registration views

- `Frontend/src/pages/attendee/EventDetail.tsx`
- `Frontend/src/pages/attendee/Explore.tsx`
- `Frontend/src/styles/attendee.css`
- `Frontend/src/styles/auth.css`

### feat(tickets-ui): display real QR tickets and retryable cancellation

- `Frontend/src/features/tickets/TicketPass.tsx`
- `Frontend/src/pages/attendee/MyRegistrations.tsx`
- `Frontend/src/pages/attendee/Ticket.tsx`

## 4. feature/uiux-v2-operations

Các commit này đã được bao gồm trong PR #10; không cần PR riêng.

### feat(realtime-ui): manage occupancy subscriptions and reconnect state

- `Frontend/src/features/live/session.ts`
- `Frontend/src/features/realtime/LiveDashboard.tsx`
- `Frontend/src/realtime/socket.ts`
- `Frontend/src/realtime/useNow.ts`
- `Frontend/src/realtime/useOccupancy.ts`
- `Frontend/src/realtime/useOccupancySocket.ts`
- `Frontend/src/realtime/usePolling.ts`

### feat(check-in-ui): add shared scanning desk and admission feedback

- `Frontend/src/features/door/DoorDesk.tsx`
- `Frontend/src/features/door/scan.ts`
- `Frontend/src/pages/staff/CheckinDesk.tsx`
- `Frontend/src/styles/operations.css`

### feat(organizer-ui): add event forms staff assignment and lifecycle actions

- `Frontend/src/features/organizer/ManageActions.tsx`
- `Frontend/src/features/organizer/ScheduleForm.tsx`
- `Frontend/src/features/organizer/StaffPanel.tsx`
- `Frontend/src/features/organizer/eventForm.ts`
- `Frontend/src/pages/organizer/Create.tsx`
- `Frontend/src/pages/organizer/Manage.tsx`
- `Frontend/src/styles/organizer.css`

### feat(organizer-ui): add paginated events and realtime dashboard

- `Frontend/src/pages/organizer/Dashboard.tsx`
- `Frontend/src/pages/organizer/Events.tsx`
- `Frontend/src/pages/organizer/Live.tsx`

### test(frontend): verify sessions realtime forms and action retries

- `Frontend/tests/foundation.test.mjs`
- `Frontend/tests/ui-actions.test.mjs`

## 5. feature/uiux-v2-documentation

Merge vào main sau PR #10.

### docs(setup): explain fresh clone installation and demo accounts

- `Frontend/README.md`
- `readme.md`

### docs(frontend): document architecture sessions and demo flows

- `Frontend/docs/architecture.md`
- `Frontend/docs/authentication.md`
- `Frontend/docs/demo-scenarios.md`
- `Frontend/docs/realtime-dashboard.md`

### docs(review): record source verification and accepted MVP limits

- `docs/README.md`
- `docs/final-review.md`
- `docs/frontend-mvp-review.md`
- `docs/gioi-han-ky-thuat.md`
- `docs/requirements-review.md`

### docs(evidence): refresh screenshots for desktop demo flows

- `docs/assets/fe-detail.png`
- `docs/assets/fe-events.png`
- `docs/assets/fe-live.png`
- `docs/assets/fe-login.png`
- `docs/assets/fe-manage.png`
- `docs/assets/fe-organizer.png`
- `docs/assets/fe-staff.png`
- `docs/assets/swagger.png`

### docs(cleanup): remove superseded phase plans

- `docs/phase-0-websocket.md`
- `docs/phase-1-contract.md`
- `docs/phase-2-perf.md`
- `docs/roadmap.md`

### docs(git): record scoped branch inventory

- `docs/uiux-v2-branches.json`
- `docs/merge-order.md`

## Kiểm chứng

Bản source cuối: 80 backend tests, coverage 94%; 23 frontend tests; lint, copy audit và production build qua. PostgreSQL concurrency, migration/seed, SMTP và dữ liệu demo đã kiểm chứng local. GitHub Actions chạy khi push; chỉ coi CI remote thành công khi run tương ứng xanh.

Không đưa .env, virtualenv, node_modules, dist, cache, coverage hoặc DB local vào commit. .env.example và dependency lock được giữ.

### fix(docs): correct merge order after completing frontend PR

- `readme.md`
- `docs/merge-order.md`
- `docs/final-review.md`
- `docs/uiux-v2-branches.json`
