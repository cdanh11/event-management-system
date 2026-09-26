import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { request, setAccessToken } from '../../api/apiClient';
import type { User } from '../../types';

type Auth = {
  user: User | null;
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
};

const AuthContext = createContext<Auth | null>(null);
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

  const logout = () => {
    void request<void>('/auth/logout', { method: 'POST' }).catch(() => undefined);
    setAccessToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('AuthProvider missing');
  }
  return context;
};