import type { ApiError } from '../types';

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

let accessToken: string | undefined;

export const setAccessToken = (value?: string) => {
  accessToken = value;
};

export const getAccessToken = () => accessToken;

export const wsBaseUrl = () =>
  baseUrl.replace(/^http/, 'ws');

// Single-flight refresh: concurrent 401s (e.g. page load calling /auth/me while
// fetching a WS ticket) share ONE token rotation. Without dedupe, two refreshes
// race and revoke each other's token, logging the user out.
let refreshPromise: Promise<boolean> | null = null;
let sessionVersion = 0;

export function clearSession() {
  if (accessToken || localStorage.getItem('evently-session')) sessionStorage.setItem('evently-session-expired', '1');
  sessionVersion += 1;
  setAccessToken();
  window.dispatchEvent(new Event('evently:session-ended'));
}

async function refresh() {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const version = sessionVersion;
      try {
        const r = await fetch(`${baseUrl}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
        });

        if (!r.ok) return false;

        const body = (await r.json()) as { access_token: string };
        if (version !== sessionVersion) return false;
        setAccessToken(body.access_token);
        return true;
      } catch {
        return false;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export async function request<T>(
  path: string,
  init: RequestInit = {},
  retry = true
): Promise<T> {
  const headers = new Headers(init.headers);
  const sentToken = accessToken;
  headers.set('Content-Type', 'application/json');

  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  let response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });

  const authForm = path === '/auth/login' || path === '/auth/register' || path === '/auth/logout';
  if (response.status === 401 && retry && !authForm) {
    // A slower 401 may arrive after another request has already rotated the token.
    const refreshed = (accessToken !== sentToken && !!accessToken) || await refresh();
    if (init.signal?.aborted) throw new DOMException('Aborted', 'AbortError');
    if (refreshed) {
      headers.set('Authorization', `Bearer ${accessToken}`);
      response = await fetch(`${baseUrl}${path}`, { ...init, headers, credentials: 'include' });
    }
    if (!refreshed || response.status === 401) clearSession();
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = Object.assign(new Error(body.message ?? 'Request failed'), {
      status: response.status,
      code: body.code ?? 'HTTP_ERROR',
      details: body.details,
    }) as ApiError;
    throw error;
  }

  return response.status === 204
    ? (undefined as T)
    : (response.json() as Promise<T>);
}
