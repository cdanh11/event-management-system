# Evently Frontend

React/TypeScript client de demo Evently FastAPI API end-to-end. Frontend khong dung mock API trong runtime; moi request di qua `src/api/apiClient.ts` toi backend FastAPI.

## Chay local

```powershell
npm ci
Copy-Item .env.example .env
npm run dev -- --port 5173
```

`VITE_API_BASE_URL` mac dinh la `http://localhost:8000`. Backend phai chay truoc khi login hoac tai du lieu.

## Kien truc hien tai

```text
App/page -> useAsync/AuthContext -> services -> apiClient -> FastAPI
```

- `src/api/apiClient.ts`: Bearer access token, refresh token cookie va xu ly API error.
- `src/services/services.ts`: goi REST endpoint va chuyen API `snake_case` sang model UI `camelCase`.
- `src/features/auth/AuthContext.tsx`: luu user hien tai va login/logout/refresh.
- `src/app/App.tsx`: routes attendee, staff va organizer.
- `src/mock/`: du lieu cu, khong duoc import vao flow runtime.

## Chuc nang tich hop

- Attendee: xem Event, dang ky, xem ve, huy dang ky.
- Staff: check-in ticket.
- Organizer: tao Event, transition lifecycle, doi lich va Notify attendee.

## Kiem tra

```powershell
npm run lint
npm run build
```

Tai lieu chung cua project nam tai [`../readme.md`](../readme.md).
