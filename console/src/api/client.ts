import axios from 'axios';

/** `/api` in dev; `/recipes/api` when the prod Vite base is `/recipes/`. */
export const API_PREFIX = `${import.meta.env.BASE_URL.replace(/\/?$/, '')}/api`.replace(
  /\/+/g,
  '/',
);

const TOKEN_KEY = 'auth_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export const apiClient = axios.create();

apiClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let onUnauthorized: (() => void) | null = null;

export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && getToken()) {
      clearToken();
      onUnauthorized?.();
    }
    return Promise.reject(error);
  },
);
