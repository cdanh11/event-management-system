import { useEffect, useState, type ReactNode } from 'react';
import { request, setAccessToken } from '../../api/apiClient';
import type { User } from '../../types';
import { AuthContext } from './authStore';

const STORAGE_KEY = 'evently-session';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  });

  useEffect(() => {
    if (user) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [user]);

  useEffect(() => {
    void request<User>('/auth/me')
      .then(setUser)
      .catch(() => {
        setAccessToken();
        setUser(null);
      });
  }, []);

  const login = async (email: string, password: string) => {
    const result = await request<{ access_token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    setAccessToken(result.access_token);
    setUser(result.user);
    return result.user;
  };

  const register = async (name: string, email: string, password: string) => {
    const result = await request<{ access_token: string; user: User }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password }),
    });

    setAccessToken(result.access_token);
    setUser(result.user);
    return result.user;
  };

  const logout = () => {
    void request<void>('/auth/logout', { method: 'POST' }).catch(() => undefined);
    setAccessToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
