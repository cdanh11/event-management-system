# Legacy Mock API contract

This document describes the historical mock layer only. The running frontend now calls FastAPI through `src/api/apiClient.ts` and `src/services/services.ts`.

`GET /events`, `GET /events/:id`, `POST /events`, `POST /events/:id/publish`, `GET /registrations/me`, `POST /events/:id/register`, `POST /registrations/:id/cancel`, `GET /tickets/:id`, and `POST /checkins` are represented in `mockApi.ts`.

Calls delay 350–700ms. Errors include `status`, `code`, and `message`, notably `409 EVENT_FULL`, `ALREADY_REGISTERED`, and `TICKET_ALREADY_USED`.
