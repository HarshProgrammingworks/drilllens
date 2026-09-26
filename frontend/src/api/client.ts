import axios, { AxiosError } from "axios";

const TOKEN_KEY = "drilllens_token";
const REMEMBER_KEY = "drilllens_remember";

export function tokenStore() {
  return localStorage.getItem(REMEMBER_KEY) === "1" ? localStorage : sessionStorage;
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string, remember: boolean) {
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
  if (remember) {
    localStorage.setItem(REMEMBER_KEY, "1");
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(REMEMBER_KEY);
    sessionStorage.setItem(TOKEN_KEY, token);
  }
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
export const api = axios.create({ baseURL: API_BASE ? `${API_BASE}/api` : "/api", timeout: 30000 });

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ message?: string; error_code?: string }>) => {
    if (error.response?.status === 401 && !error.config?.url?.includes("/auth/login")) {
      clearToken();
      if (!window.location.pathname.startsWith("/login")) window.location.assign("/login");
    }
    const message = error.response?.data?.message || (error.code === "ECONNABORTED" ? "The request timed out." : error.message || "Network request failed.");
    return Promise.reject(new Error(message));
  },
);
