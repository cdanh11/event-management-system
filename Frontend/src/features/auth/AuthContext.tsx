import { useEffect, useState, type ReactNode } from 'react';
import { clearSession, request, setAccessToken } from '../../api/apiClient';
import type { User } from '../../types';
import { AuthContext } from './authStore';

const STORAGE_KEY = 'evently-session';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  });
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (user) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [user]);

  useEffect(() => {
    let alive = true;
    const abort = new AbortController();
    const end = () => { if (alive) { setUser(null); setReady(true); } };
    window.addEventListener('evently:session-ended', end);
    void request<User>('/auth/me', { signal: abort.signal })
      .then((value) => { if (alive) setUser(value); })
      .catch(() => {
        if (alive) { setAccessToken(); setUser(null); }
      })
      .finally(() => { if (alive) setReady(true); });
    return () => { alive = false; abort.abort(); window.removeEventListener('evently:session-ended', end); };
  }, []);

  const login = async (email: string, password: string) => {
    const result = await request<{ access_token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    setAccessToken(result.access_token);
    sessionStorage.removeItem('evently-session-expired');
    setUser(result.user);
    return result.user;
  };

  const register = async (name: string, email: string, password: string) => {
    const result = await request<{ access_token: string; user: User }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password }),
    });

    setAccessToken(result.access_token);
    sessionStorage.removeItem('evently-session-expired');
    setUser(result.user);
    return result.user;
  };

  const logout = () => {
    void request<void>('/auth/logout', { method: 'POST' }, false).catch(() => undefined);
    clearSession();
    sessionStorage.removeItem('evently-session-expired');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, ready, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
