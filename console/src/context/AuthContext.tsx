import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { apiClient, clearToken, getToken, setToken, setUnauthorizedHandler } from '../api/client';

export interface AuthUser {
  username: string;
  role: 'admin' | 'user';
}

interface AuthContextValue {
  user: AuthUser | null;
  isAdmin: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, code: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function decodeJwtPayload(token: string): AuthUser | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return { username: payload.username, role: payload.role };
  } catch {
    return null;
  }
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    const token = getToken();
    if (token) {
      const decoded = decodeJwtPayload(token);
      if (decoded) {
        setUser(decoded);
      } else {
        clearToken();
      }
    }
    setIsLoading(false);
  }, [logout]);

  const login = useCallback(async (username: string, password: string) => {
    const res = await apiClient.post('/api/auth/login', { username, password });
    setToken(res.data.access_token);
    setUser({ username: res.data.username, role: res.data.role });
  }, []);

  const register = useCallback(async (username: string, password: string, code: string) => {
    await apiClient.post('/api/auth/register', { username, password, code });
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAdmin: user?.role === 'admin',
      isLoading,
      login,
      register,
      logout,
    }),
    [user, isLoading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
