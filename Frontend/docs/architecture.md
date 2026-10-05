# Architecture

The UI follows `Page -> hook/context -> service -> apiClient -> FastAPI`. Pages call service functions through `useAsync`; `apiClient.ts` owns Bearer access-token handling, refresh-token cookie retry and normalized API errors. `services.ts` maps backend `snake_case` responses to the frontend `camelCase` domain types. The legacy `mock/` directory is not part of the runtime request flow.
