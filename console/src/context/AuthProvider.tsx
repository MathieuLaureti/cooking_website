import React, { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  API_PREFIX,
  apiClient,
  clearToken,
  getToken,
  setToken,
  setUnauthorizedHandler,
} from '../api/client';
import { AuthContext, type AuthUser } from './auth-context';

function decodeJwtPayload(token: string): AuthUser | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return { username: payload.username, role: payload.role };
  } catch {
    return null;
  }
}

function userFromStoredToken(): AuthUser | null {
  const token = getToken();
  if (!token) return null;
  const decoded = decodeJwtPayload(token);
  if (!decoded) {
    clearToken();
    return null;
  }
  return decoded;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(() => userFromStoredToken());
  const [isLoading] = useState(false);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
  }, [logout]);

  const login = useCallback(async (username: string, password: string) => {
    try {
      const res = await apiClient.post(`${API_PREFIX}/auth/login`, { username, password });
      setToken(res.data.access_token);
      setUser({ username: res.data.username, role: res.data.role });
    } catch (err) {
      if (axios.isAxiosError(err)) {
        if (err.response?.status === 401) {
          throw new Error('Invalid username or password.');
        }
        if (!err.response) {
          throw new Error('Could not reach the API. Try a hard refresh or check the network.');
        }
      }
      throw err;
    }
  }, []);

  const register = useCallback(async (username: string, password: string, code: string) => {
    await apiClient.post(`${API_PREFIX}/auth/register`, { username, password, code });
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
