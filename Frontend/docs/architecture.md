# Architecture

The UI follows `Page → hook/context → service → mock API → mock data`. Pages only call service functions through `useAsync`; `mockApi.ts` owns delay, LocalStorage persistence, errors, and domain transitions. Replacing mockApi with an HTTP client preserves pages.
